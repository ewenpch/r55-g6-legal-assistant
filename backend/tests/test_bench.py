import csv
import json
from pathlib import Path

import httpx
import pytest

from scripts import bench

CORPUS_DIR = Path(__file__).resolve().parents[2] / "corpus" / "bench"


@pytest.fixture(scope="module")
def corpus() -> dict[str, list[str]]:
    return bench.load_corpus(CORPUS_DIR)


# --- Document et découpage -----------------------------------------------------------------


def test_assemble_document_takes_pages_from_first_contract(corpus) -> None:
    document = bench.assemble_document(corpus, "bail-habitation", 6)

    assert [page.number for page in document] == [1, 2, 3, 4, 5, 6]
    assert {page.source for page in document} == {"bail-habitation"}


def test_assemble_document_completes_with_next_contracts(corpus) -> None:
    document = bench.assemble_document(corpus, "bail-habitation", 10)

    assert len(document) == 10
    assert [page.source for page in document[6:]] == ["abonnement-salle-sport"] * 4
    assert document[6].text == corpus["abonnement-salle-sport"][0]


def test_assemble_document_rejects_too_many_pages(corpus) -> None:
    with pytest.raises(ValueError, match="pages demandées"):
        bench.assemble_document(corpus, "bail-habitation", 100)
    with pytest.raises(ValueError, match="contrat inconnu"):
        bench.assemble_document(corpus, "inexistant", 6)


@pytest.mark.parametrize("num_ctx", [2048, 4096])
def test_chunks_fit_budget_and_keep_all_text(corpus, num_ctx: int) -> None:
    document = bench.assemble_document(corpus, "bail-habitation", 10)
    budget = bench.chunk_budget(num_ctx, 512)
    chunks = bench.build_chunks(document, budget)

    assert all(chunk.est_tokens <= budget for chunk in chunks)
    assert [chunk.index for chunk in chunks] == list(range(1, len(chunks) + 1))
    assert chunks[0].page_start == 1 and chunks[-1].page_end == 10
    for previous, current in zip(chunks, chunks[1:], strict=False):
        assert current.page_start >= previous.page_end
    # Aucune perte de texte : on retrouve toutes les lignes, dans l'ordre.
    original = [line for page in document for line in page.text.splitlines()]
    rebuilt = [line for chunk in chunks for line in chunk.text.splitlines()]
    assert rebuilt == original


def test_smaller_context_gives_more_chunks(corpus) -> None:
    document = bench.assemble_document(corpus, "bail-habitation", 6)
    small = bench.build_chunks(document, bench.chunk_budget(2048, 512))
    large = bench.build_chunks(document, bench.chunk_budget(4096, 512))

    assert len(small) > len(large) >= 2


def test_chunks_start_on_article_titles(corpus) -> None:
    document = bench.assemble_document(corpus, "bail-habitation", 6)
    chunks = bench.build_chunks(document, bench.chunk_budget(2048, 512))

    for chunk in chunks[1:]:
        first_line = chunk.text.splitlines()[0]
        # Un bloc commence sur un titre d'article, sauf s'il commence une nouvelle page.
        starts_page = any(page.text.startswith(first_line) for page in document)
        assert bench.ARTICLE_RE.match(first_line) or starts_page


def test_long_section_is_split_by_lines() -> None:
    text = "\n".join(f"ligne {i} " + "x" * 200 for i in range(40))
    pages = [bench.Page(number=1, source="test", text=text)]
    chunks = bench.build_chunks(pages, 300)

    assert len(chunks) > 1
    assert all(chunk.est_tokens <= 300 for chunk in chunks)


def test_chunk_budget_rejects_tiny_context() -> None:
    with pytest.raises(ValueError, match="trop petit"):
        bench.chunk_budget(1024, 900)


# --- Métriques Ollama ----------------------------------------------------------------------


def test_request_metrics_from_ollama_counters() -> None:
    data = {
        "message": {"role": "assistant", "content": '{"contract_type": "Bail"}'},
        "done_reason": "stop",
        "load_duration": 50_000_000,
        "prompt_eval_count": 1200,
        "prompt_eval_duration": 4_000_000_000,
        "eval_count": 100,
        "eval_duration": 20_000_000_000,
        "total_duration": 24_100_000_000,
    }
    metrics = bench.request_metrics(data, num_ctx=2048, num_predict=512)

    assert metrics["prefill_tok_s"] == 300.0
    assert metrics["gen_tok_s"] == 5.0
    assert metrics["load_s"] == 0.05
    assert metrics["json_valid"] is True
    assert metrics["context_overflow"] is False


def test_request_metrics_flags_overflow_and_invalid_json() -> None:
    data = {"message": {"content": "pas du json"}, "prompt_eval_count": 2040, "eval_count": 0}
    metrics = bench.request_metrics(data, num_ctx=2048, num_predict=512)

    assert metrics["context_overflow"] is True
    assert metrics["json_valid"] is False
    assert metrics["gen_tok_s"] is None


# --- Mémoire et swap -----------------------------------------------------------------------


def _sample(rss_mb=0, proc_swap_mb=0, available_mb=4000, swap_used_mb=100, swap_out_mb=0):
    mb = bench.MB
    return bench.Sample(
        rss=rss_mb * mb,
        proc_swap=None if proc_swap_mb is None else proc_swap_mb * mb,
        available=available_mb * mb,
        swap_used=swap_used_mb * mb,
        swap_out=swap_out_mb * mb,
    )


RAM_TOTAL = 8 * 1024 * bench.MB


def test_no_swap_when_memory_is_stable() -> None:
    samples = [_sample(rss_mb=4500), _sample(rss_mb=5200), _sample(rss_mb=5100)]
    stats = bench.summarize_samples(samples, RAM_TOTAL)

    assert stats.rss_peak_mb == 5200.0
    assert stats.swap == "non"
    assert stats.swap_reasons == []


def test_swap_detected_from_process_swap() -> None:
    samples = [_sample(rss_mb=5000), _sample(rss_mb=5000, proc_swap_mb=600)]
    stats = bench.summarize_samples(samples, RAM_TOTAL)

    assert stats.swap == "oui"
    assert "processus Ollama en swap" in stats.swap_reasons[0]


def test_swap_detected_from_pages_written_to_swap() -> None:
    samples = [_sample(swap_out_mb=1000, proc_swap_mb=None), _sample(swap_out_mb=1400)]
    stats = bench.summarize_samples(samples, RAM_TOTAL)

    assert stats.swap == "oui"
    assert stats.swap_out_delta_mb == 400.0


def test_swap_detected_from_system_swap_growth() -> None:
    samples = [_sample(swap_used_mb=100), _sample(swap_used_mb=900), _sample(swap_used_mb=500)]
    stats = bench.summarize_samples(samples, RAM_TOTAL)

    assert stats.swap == "oui"
    assert stats.swap_used_delta_mb == 800.0


def test_swap_suspected_when_ram_runs_out_or_model_reloads() -> None:
    low_ram = bench.summarize_samples([_sample(), _sample(available_mb=120)], RAM_TOTAL)
    reloaded = bench.summarize_samples([_sample()], RAM_TOTAL, reloads=2)

    assert low_ram.swap == "suspect"
    assert reloaded.swap == "suspect"


def test_no_samples_means_unknown() -> None:
    assert bench.summarize_samples([], RAM_TOTAL).swap == "inconnu"


def test_resource_monitor_samples_before_and_after() -> None:
    calls = []

    def sampler() -> bench.Sample:
        calls.append(1)
        return _sample(rss_mb=len(calls) * 100)

    with bench.ResourceMonitor(interval_s=3600, sampler=sampler) as monitor:
        pass

    assert len(monitor.samples) == 2
    assert bench.summarize_samples(monitor.samples, RAM_TOTAL).rss_peak_mb == 200.0


def test_ollama_process_names() -> None:
    assert bench.is_ollama_process("ollama")
    assert bench.is_ollama_process("ollama.exe")
    assert bench.is_ollama_process("ollama_llama_server.exe")
    assert not bench.is_ollama_process("ollama app.exe")
    assert not bench.is_ollama_process("python3")


def test_normalize_host() -> None:
    assert bench.normalize_host("localhost") == "http://localhost:11434"
    assert bench.normalize_host("0.0.0.0:11500") == "http://127.0.0.1:11500"
    assert bench.normalize_host("http://192.168.1.4:11434/") == "http://192.168.1.4:11434"
    assert bench.is_local_host("http://127.0.0.1:11434")
    assert not bench.is_local_host("http://192.168.1.4:11434")


# --- Bout en bout avec un faux serveur Ollama ----------------------------------------------


class FakeOllama:
    """Simule les routes Ollama utilisées par le script."""

    def __init__(self, models: list[str]):
        self.models = models
        self.loaded: dict[str, int] = {}
        self.chats: list[dict] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        body = json.loads(request.content) if request.content else {}
        if path == "/api/version":
            return httpx.Response(200, json={"version": "0.0-test"})
        if path == "/api/tags":
            models = [
                {
                    "name": name,
                    "digest": "abc123",
                    "size": 2 * 1024**3,
                    "details": {"parameter_size": "3B", "quantization_level": "Q4_K_M"},
                }
                for name in self.models
            ]
            return httpx.Response(200, json={"models": models})
        if path == "/api/ps":
            models = [
                {"name": name, "size": 3 * 1024**3, "size_vram": 0, "context_length": ctx}
                for name, ctx in self.loaded.items()
            ]
            return httpx.Response(200, json={"models": models})
        if path == "/api/generate":
            if body.get("keep_alive") == 0:
                self.loaded.pop(body["model"], None)
                return httpx.Response(200, json={"done": True, "done_reason": "unload"})
            self.loaded[body["model"]] = body["options"]["num_ctx"]
            return httpx.Response(200, json={"done": True, "done_reason": "load"})
        if path == "/api/chat":
            self.chats.append(body)
            if body["model"] not in self.loaded:
                return httpx.Response(500, json={"error": "modèle non chargé"})
            prompt_chars = sum(len(m["content"]) for m in body["messages"])
            return httpx.Response(
                200,
                json={
                    "message": {"role": "assistant", "content": '{"clauses_to_check": []}'},
                    "done": True,
                    "done_reason": "stop",
                    "load_duration": 10_000_000,
                    "prompt_eval_count": prompt_chars // 4,
                    "prompt_eval_duration": prompt_chars * 1_000_000,
                    "eval_count": 50,
                    "eval_duration": 5_000_000_000,
                    "total_duration": 6_000_000_000,
                },
            )
        return httpx.Response(404, json={"error": "route inconnue"})


def test_main_runs_full_matrix_and_writes_results(tmp_path: Path, capsys) -> None:
    fake = FakeOllama(["llama3.2:3b", "qwen2.5:7b-instruct"])
    argv = [
        "--models", "llama3.2:3b,qwen2.5:7b-instruct",
        "--num-ctx", "2048,4096",
        "--pages", "6,10",
        "--no-monitor",
        "--output-dir", str(tmp_path),
        "--tag", "test",
    ]  # fmt: skip

    assert bench.main(argv, transport=httpx.MockTransport(fake)) == 0

    json_files = list(tmp_path.glob("bench_*_test.json"))
    assert len(json_files) == 1
    results = json.loads(json_files[0].read_text(encoding="utf-8"))
    assert len(results["loads"]) == 4
    assert len(results["runs"]) == 8
    assert results["meta"]["models"]["llama3.2:3b"]["quantization_level"] == "Q4_K_M"

    run = results["runs"][0]
    assert run["error"] is None
    assert run["chunks_done"] == run["chunks"] > 1
    assert run["gen_tok_s"] == 10.0
    assert run["prefill_tok_s"] == pytest.approx(250, rel=1e-3)
    assert run["json_valid"] == run["chunks"]
    assert run["swap"] == "inconnu"

    # Le prompt commence par un nonce unique : pas de réutilisation du cache KV.
    systems = [chat["messages"][0]["content"].splitlines()[0] for chat in fake.chats]
    assert len(set(systems)) == len(systems)
    assert all(chat["options"]["num_ctx"] in (2048, 4096) for chat in fake.chats)

    with json_files[0].with_suffix(".csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 8
    markdown = json_files[0].with_suffix(".md").read_text(encoding="utf-8")
    assert "| llama3.2:3b | 2048 | 10 | bail-habitation |" in markdown

    # Aucun texte de contrat dans les résultats ni dans la console.
    secret = "Hélène Marchadier"
    assert secret not in json_files[0].read_text(encoding="utf-8")
    assert secret not in markdown
    assert secret not in capsys.readouterr().out


def test_main_reports_chat_errors_without_crashing(tmp_path: Path) -> None:
    fake = FakeOllama(["llama3.2:3b"])

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/chat":
            return httpx.Response(500, json={"error": "model requires more system memory"})
        return fake(request)

    argv = ["--models", "llama3.2:3b", "--num-ctx", "2048", "--pages", "6",
            "--no-monitor", "--output-dir", str(tmp_path)]  # fmt: skip

    assert bench.main(argv, transport=httpx.MockTransport(handler)) == 0

    results = json.loads(next(tmp_path.glob("*.json")).read_text(encoding="utf-8"))
    run = results["runs"][0]
    assert "more system memory" in run["error"]
    assert run["within_budget"] is False


def test_main_stops_when_model_is_missing(tmp_path: Path) -> None:
    fake = FakeOllama(["llama3.2:3b"])
    argv = ["--models", "qwen2.5:7b-instruct", "--no-monitor", "--output-dir", str(tmp_path)]

    with pytest.raises(SystemExit, match="ollama pull qwen2.5:7b-instruct"):
        bench.main(argv, transport=httpx.MockTransport(fake))


def test_dry_run_does_not_call_ollama(capsys) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("Ollama ne doit pas être appelé")

    assert bench.main(["--dry-run"], transport=httpx.MockTransport(handler)) == 0
    out = capsys.readouterr().out
    assert "| 2048 | 6 | bail-habitation |" in out
    assert "| 4096 | 10 | bail-habitation |" in out
