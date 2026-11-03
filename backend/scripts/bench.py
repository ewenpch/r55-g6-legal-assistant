"""Benchmark des modeles Ollama sur le pipeline d'analyse par blocs.

Mesure, pour chaque couple (modele, num_ctx, nombre de pages) :
- le temps de chargement du modele ;
- le debit de prefill et de generation ;
- le temps total du pipeline chunké ;
- le RSS pic / la RAM disponible / le swap si Ollama tourne en local.

Les resultats sont ecrits en JSON brut, CSV et resume Markdown.
Aucun contenu de contrat n'est ecrit dans les logs.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import statistics
import sys
import threading
import time
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import psutil
import pymupdf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEFAULT_MODELS = "qwen2.5:7b-instruct,llama3.2:3b"
DEFAULT_NUM_CTX = "2048,4096"
DEFAULT_PAGES = "6,10"

PROMPT_TEMPLATE = """Tu es un assistant qui aide un particulier a comprendre un contrat de bail.
Analyse l'extrait ci-dessous et reponds UNIQUEMENT avec un objet JSON valide, sans texte autour.

Schema attendu :
{{
  "contract_type": "type de contrat",
  "summary": "resume en 5 phrases maximum",
  "parties": [{{"name": "nom", "role": "role"}}],
  "object": "objet du contrat",
  "duration": "duree",
  "key_dates": [{{"label": "libelle", "date": "date"}}],
  "amounts": [{{"label": "libelle", "value": "montant"}}],
  "obligations": [{{"party": "partie", "items": ["obligation"]}}],
  "clauses_to_check": [
    {{
      "title": "titre court",
      "quote": "extrait exact du texte fourni",
      "explanation": "explication simple",
      "level": "info|attention|important",
      "page": 1
    }}
  ]
}}

Regles :
- Chaque citation de "clauses_to_check" doit etre copiee mot pour mot depuis l'extrait.
- Ne fabrique aucune clause absente de l'extrait.
- Utilise uniquement les informations presentes dans l'extrait.
- Reponds en francais.

Mesure : {nonce}
Extrait (pages {page_start} a {page_end}) :
{text}
"""

RUN_FIELDS = [
    "run_id",
    "model",
    "num_ctx",
    "pages",
    "repeat",
    "cold_start",
    "contract",
    "chunk_tokens_target",
    "chunk_count",
    "pages_processed",
    "total_prompt_tokens",
    "total_eval_tokens",
    "total_load_s",
    "total_prefill_s",
    "total_eval_s",
    "total_duration_s",
    "pipeline_wall_s",
    "pipeline_wall_excl_load_s",
    "prefill_tok_s",
    "gen_tok_s",
    "sec_per_page",
    "tokens_per_page",
    "json_valid_chunks",
    "json_valid_ratio",
    "context_truncated_chunks",
    "rss_peak_mb",
    "ram_available_min_mb",
    "swap_used_delta_mb",
    "swap_used_peak_mb",
    "monitor_note",
    "error",
]

REQUEST_FIELDS = [
    "run_id",
    "model",
    "num_ctx",
    "pages",
    "repeat",
    "chunk_index",
    "chunk_count",
    "page_start",
    "page_end",
    "approx_chunk_tokens",
    "prompt_chars",
    "load_duration_ms",
    "prompt_eval_count",
    "prompt_eval_duration_ms",
    "eval_count",
    "eval_duration_ms",
    "total_duration_ms",
    "client_wall_ms",
    "prefill_tok_s",
    "gen_tok_s",
    "json_valid",
    "response_chars",
    "done_reason",
    "error",
]


@dataclass
class Chunk:
    text: str
    page_start: int
    page_end: int
    approx_tokens: int


@dataclass
class MonitorSample:
    rss_bytes: int
    available_bytes: int
    swap_used_bytes: int


@dataclass
class ResourceMonitor:
    interval_s: float = 0.25
    samples: list[MonitorSample] = field(default_factory=list)
    _stop: threading.Event = field(default_factory=threading.Event)
    _thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                rss = 0
                for process in psutil.process_iter(["name", "memory_info"]):
                    name = (process.info.get("name") or "").lower()
                    is_ollama = (
                        "ollama" in name
                        or "llama-server" in name
                        or "llama_server" in name
                    )
                    if not is_ollama:
                        continue
                    memory = process.info.get("memory_info")
                    if memory is not None:
                        rss += memory.rss
                memory = psutil.virtual_memory()
                swap = psutil.swap_memory()
                self.samples.append(
                    MonitorSample(
                        rss_bytes=rss,
                        available_bytes=memory.available,
                        swap_used_bytes=swap.used,
                    )
                )
            except (psutil.Error, OSError):
                pass
            self._stop.wait(self.interval_s)

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)

    def summary(self) -> dict[str, Any]:
        if not self.samples:
            return {
                "rss_peak_mb": None,
                "ram_available_min_mb": None,
                "swap_used_delta_mb": None,
                "swap_used_peak_mb": None,
                "monitor_note": "aucun echantillon",
            }
        rss_peak = max(sample.rss_bytes for sample in self.samples)
        ram_min = min(sample.available_bytes for sample in self.samples)
        swap_first = self.samples[0].swap_used_bytes
        swap_last = self.samples[-1].swap_used_bytes
        swap_peak = max(sample.swap_used_bytes for sample in self.samples)
        note = "ok" if rss_peak > 0 else "processus Ollama non trouve"
        return {
            "rss_peak_mb": round(rss_peak / (1024 * 1024), 1) if rss_peak > 0 else None,
            "ram_available_min_mb": round(ram_min / (1024 * 1024), 1),
            "swap_used_delta_mb": round((swap_last - swap_first) / (1024 * 1024), 1),
            "swap_used_peak_mb": round(swap_peak / (1024 * 1024), 1),
            "monitor_note": note,
        }


def parse_csv_list(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_int_list(value: str) -> list[int]:
    return [int(item) for item in parse_csv_list(value)]


def approx_tokens(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def split_sentences(text: str) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []
    sentences = []
    for part in normalized.replace(";", ".").split("."):
        part = part.strip()
        if part:
            sentences.append(f"{part}.")
    return sentences


def iter_units(pages: list[str]) -> Iterable[tuple[int, str]]:
    for page_number, page_text in enumerate(pages, start=1):
        for sentence in split_sentences(page_text):
            if len(sentence) <= 1200:
                yield page_number, sentence
                continue
            for start in range(0, len(sentence), 1200):
                piece = sentence[start : start + 1200].strip()
                if piece:
                    yield page_number, piece


def build_chunks(pages: list[str], chunk_tokens: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    current: list[str] = []
    current_tokens = 0
    page_start = 0
    page_end = 0

    def flush() -> None:
        nonlocal current, current_tokens, page_start, page_end
        if not current:
            return
        chunks.append(
            Chunk(
                text=" ".join(current),
                page_start=page_start,
                page_end=page_end,
                approx_tokens=current_tokens,
            )
        )
        current = []
        current_tokens = 0
        page_start = 0
        page_end = 0

    for page_number, sentence in iter_units(pages):
        sentence_tokens = approx_tokens(sentence)
        if current and current_tokens + sentence_tokens > chunk_tokens:
            flush()
        if not current:
            page_start = page_number
        current.append(sentence)
        current_tokens += sentence_tokens
        page_end = page_number

    flush()
    return chunks


def chunk_tokens_for(num_ctx: int, args: argparse.Namespace) -> int:
    tokens = max(1, num_ctx - args.reserve_tokens)
    if args.max_chunk_tokens > 0:
        tokens = min(tokens, args.max_chunk_tokens)
    return tokens


def select_chunks(chunks: list[Chunk], args: argparse.Namespace) -> list[Chunk]:
    if args.max_chunks > 0:
        return chunks[: args.max_chunks]
    return chunks


def read_pages(path: Path) -> list[str]:
    with pymupdf.open(path) as document:
        return [page.get_text("text") for page in document]


def normalize_host(host: str) -> str:
    host = host.strip().rstrip("/")
    if not host.startswith(("http://", "https://")):
        host = f"http://{host}"
    return host


def is_local_host(host: str) -> bool:
    hostname = (urlparse(host).hostname or "").lower()
    return hostname in {"localhost", "127.0.0.1", "::1"}


def model_matches(candidate: str, model: str) -> bool:
    return candidate == model or candidate.startswith(f"{model}:")


def ollama_version(client: httpx.Client, host: str) -> str | None:
    try:
        response = client.get(f"{host}/api/version", timeout=15)
        response.raise_for_status()
        return response.json().get("version")
    except (httpx.HTTPError, ValueError):
        return None


def ollama_tags(client: httpx.Client, host: str) -> list[dict[str, Any]]:
    response = client.get(f"{host}/api/tags", timeout=30)
    response.raise_for_status()
    return response.json().get("models", [])


def ollama_ps(client: httpx.Client, host: str) -> list[dict[str, Any]]:
    try:
        response = client.get(f"{host}/api/ps", timeout=15)
        response.raise_for_status()
        return response.json().get("models", [])
    except (httpx.HTTPError, ValueError):
        return []


def unload_model(client: httpx.Client, host: str, model: str, wait_s: float = 30.0) -> None:
    try:
        response = client.post(
            f"{host}/api/generate",
            json={"model": model, "keep_alive": 0},
            timeout=30,
        )
        if response.is_error:
            client.post(
                f"{host}/api/chat",
                json={"model": model, "messages": [], "keep_alive": 0},
                timeout=30,
            )
    except httpx.HTTPError:
        pass

    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        loaded = [item.get("name", "") for item in ollama_ps(client, host)]
        if not any(model_matches(name, model) for name in loaded):
            return
        time.sleep(1)


def unload_all_models(client: httpx.Client, host: str, wait_s: float = 30.0) -> None:
    loaded = [
        item.get("name", "")
        for item in ollama_ps(client, host)
        if item.get("name")
    ]
    for name in loaded:
        unload_model(client, host, name, wait_s=wait_s)

    deadline = time.monotonic() + wait_s
    while time.monotonic() < deadline:
        if not ollama_ps(client, host):
            return
        time.sleep(1)


def parse_json_response(text: str) -> bool:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = candidate.removeprefix("```json").removeprefix("```")
        candidate = candidate.removesuffix("```").strip()
    try:
        json.loads(candidate)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def generate(
    client: httpx.Client,
    host: str,
    model: str,
    prompt: str,
    num_ctx: int,
    num_predict: int,
    temperature: float,
    seed: int,
) -> tuple[dict[str, Any] | None, float, str | None]:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json",
        "keep_alive": "5m",
        "options": {
            "num_ctx": num_ctx,
            "num_predict": num_predict,
            "temperature": temperature,
            "seed": seed,
            "top_p": 0.9,
            "repeat_penalty": 1.05,
        },
    }
    started = time.perf_counter()
    try:
        response = client.post(f"{host}/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        wall_s = time.perf_counter() - started
        return data, wall_s, None
    except (httpx.HTTPError, ValueError) as exc:
        wall_s = time.perf_counter() - started
        return None, wall_s, f"{type(exc).__name__}: {exc}"


def chunk_prompt(
    chunk: Chunk,
    nonce: str,
    num_ctx: int,
) -> str:
    # La marge de securite couvre l'instruction, le schema et les tokens speciaux.
    reserve = max(1, num_ctx - chunk.approx_tokens)
    if reserve < 200:
        print(
            f"  attention : bloc de ~{chunk.approx_tokens} tokens pour num_ctx={num_ctx}",
            file=sys.stderr,
        )
    return PROMPT_TEMPLATE.format(
        nonce=nonce,
        page_start=chunk.page_start,
        page_end=chunk.page_end,
        text=chunk.text,
    )


def run_pipeline(
    client: httpx.Client,
    host: str,
    model: str,
    num_ctx: int,
    pages_count: int,
    contract_path: Path,
    chunks: list[Chunk],
    repeat: int,
    cold_start: bool,
    monitor: ResourceMonitor | None,
    args: argparse.Namespace,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    run_id = (
        f"{model.replace(':', '_').replace('/', '_')}"
        f"_ctx{num_ctx}_p{pages_count}_r{repeat}"
    )
    started = time.perf_counter()
    requests: list[dict[str, Any]] = []
    error: str | None = None

    if cold_start:
        unload_all_models(client, host)

    if monitor is not None:
        monitor.start()

    for index, chunk in enumerate(chunks, start=1):
        nonce = f"{run_id}-{index}-{time.time_ns()}"
        prompt = chunk_prompt(chunk, nonce, num_ctx)
        data, wall_s, request_error = generate(
            client=client,
            host=host,
            model=model,
            prompt=prompt,
            num_ctx=num_ctx,
            num_predict=args.num_predict,
            temperature=args.temperature,
            seed=args.seed,
        )

        request: dict[str, Any] = {
            "run_id": run_id,
            "model": model,
            "num_ctx": num_ctx,
            "pages": pages_count,
            "repeat": repeat,
            "chunk_index": index,
            "chunk_count": len(chunks),
            "page_start": chunk.page_start,
            "page_end": chunk.page_end,
            "approx_chunk_tokens": chunk.approx_tokens,
            "prompt_chars": len(prompt),
            "load_duration_ms": None,
            "prompt_eval_count": None,
            "prompt_eval_duration_ms": None,
            "eval_count": None,
            "eval_duration_ms": None,
            "total_duration_ms": None,
            "client_wall_ms": round(wall_s * 1000, 1),
            "prefill_tok_s": None,
            "gen_tok_s": None,
            "json_valid": None,
            "response_chars": None,
            "done_reason": None,
            "error": request_error,
        }

        if data is not None:
            prompt_eval_count = data.get("prompt_eval_count") or 0
            prompt_eval_duration_s = (data.get("prompt_eval_duration") or 0) / 1e9
            eval_count = data.get("eval_count") or 0
            eval_duration_s = (data.get("eval_duration") or 0) / 1e9
            response_text = data.get("response") or ""

            request.update(
                {
                    "load_duration_ms": round((data.get("load_duration") or 0) / 1e6, 1),
                    "prompt_eval_count": prompt_eval_count,
                    "prompt_eval_duration_ms": round(prompt_eval_duration_s * 1000, 1),
                    "eval_count": eval_count,
                    "eval_duration_ms": round(eval_duration_s * 1000, 1),
                    "total_duration_ms": round((data.get("total_duration") or 0) / 1e6, 1),
                    "prefill_tok_s": round(prompt_eval_count / prompt_eval_duration_s, 2)
                    if prompt_eval_duration_s > 0
                    else None,
                    "gen_tok_s": round(eval_count / eval_duration_s, 2)
                    if eval_duration_s > 0
                    else None,
                    "json_valid": parse_json_response(response_text),
                    "response_chars": len(response_text),
                    "done_reason": data.get("done_reason"),
                }
            )
        else:
            error = request_error

        requests.append(request)
        if request_error:
            error = request_error
            break

    wall_s = time.perf_counter() - started
    if monitor is not None:
        monitor.stop()
        monitor_summary = monitor.summary()
    else:
        monitor_summary = {
            "rss_peak_mb": None,
            "ram_available_min_mb": None,
            "swap_used_delta_mb": None,
            "swap_used_peak_mb": None,
            "monitor_note": "desactive (hote distant)",
        }

    successful = [request for request in requests if request["error"] is None]
    total_prompt_tokens = sum(request["prompt_eval_count"] or 0 for request in successful)
    total_eval_tokens = sum(request["eval_count"] or 0 for request in successful)
    total_load_s = sum((request["load_duration_ms"] or 0) / 1000 for request in successful)
    total_prefill_s = sum(
        (request["prompt_eval_duration_ms"] or 0) / 1000 for request in successful
    )
    total_eval_s = sum((request["eval_duration_ms"] or 0) / 1000 for request in successful)
    total_duration_s = sum((request["total_duration_ms"] or 0) / 1000 for request in successful)
    json_valid = sum(1 for request in successful if request["json_valid"])
    truncated = sum(
        1
        for request in successful
        if (request["prompt_eval_count"] or 0) >= max(1, num_ctx - 8)
    )

    run = {
        "run_id": run_id,
        "model": model,
        "num_ctx": num_ctx,
        "pages": pages_count,
        "repeat": repeat,
        "cold_start": cold_start,
        "contract": contract_path.name,
        "chunk_tokens_target": chunk_tokens_for(num_ctx, args),
        "chunk_count": len(chunks),
        "pages_processed": pages_count,
        "total_prompt_tokens": total_prompt_tokens,
        "total_eval_tokens": total_eval_tokens,
        "total_load_s": round(total_load_s, 3),
        "total_prefill_s": round(total_prefill_s, 3),
        "total_eval_s": round(total_eval_s, 3),
        "total_duration_s": round(total_duration_s, 3),
        "pipeline_wall_s": round(wall_s, 3),
        "pipeline_wall_excl_load_s": round(max(0.0, wall_s - total_load_s), 3),
        "prefill_tok_s": round(total_prompt_tokens / total_prefill_s, 2)
        if total_prefill_s > 0
        else None,
        "gen_tok_s": round(total_eval_tokens / total_eval_s, 2)
        if total_eval_s > 0
        else None,
        "sec_per_page": round(wall_s / pages_count, 3) if pages_count else None,
        "tokens_per_page": round(total_prompt_tokens / pages_count, 1)
        if pages_count
        else None,
        "json_valid_chunks": json_valid,
        "json_valid_ratio": round(json_valid / len(successful), 3) if successful else None,
        "context_truncated_chunks": truncated,
        **monitor_summary,
        "error": error,
    }
    return run, requests


def write_outputs(
    output_dir: Path,
    tag: str,
    meta: dict[str, Any],
    runs: list[dict[str, Any]],
    requests: list[dict[str, Any]],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"bench_{tag}" if tag else f"bench_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    json_path = output_dir / f"{stem}.json"
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(
            {"meta": meta, "runs": runs, "requests": requests},
            handle,
            ensure_ascii=False,
            indent=2,
        )

    with (output_dir / f"{stem}_runs.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RUN_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(runs)

    with (output_dir / f"{stem}_requests.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=REQUEST_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(requests)

    summary_path = output_dir / f"{stem}_summary.md"
    summary_path.write_text(render_summary(runs, meta), encoding="utf-8")
    return json_path


def group_runs(runs: list[dict[str, Any]]) -> dict[tuple[str, int, int], list[dict[str, Any]]]:
    grouped: dict[tuple[str, int, int], list[dict[str, Any]]] = {}
    for run in runs:
        key = (run["model"], run["num_ctx"], run["pages"])
        grouped.setdefault(key, []).append(run)
    return grouped


def median_or_none(values: list[float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    return statistics.median(clean) if clean else None


def render_summary(runs: list[dict[str, Any]], meta: dict[str, Any]) -> str:
    lines = [
        "# Resultats bruts du benchmark",
        "",
        f"- Date : {meta.get('timestamp')}",
        f"- Hote Ollama : {meta.get('host')}",
        f"- Version Ollama : {meta.get('ollama_version')}",
        f"- Mode : {meta.get('mode')}",
        f"- Repetitions : {meta.get('repeats')}",
        f"- Contrat : {meta.get('contract')}",
        "",
        "| Modele | ctx | pages | runs | charge (s) | temps chaud median (s) | "
        "s/page | prefill tok/s | gen tok/s | RSS pic (Mo) | JSON valide |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for (model, num_ctx, pages), group in sorted(group_runs(runs).items()):
        warm_runs = [run for run in group if not run["cold_start"]] or group
        cold_runs = [run for run in group if run["cold_start"]]
        wall = median_or_none([run["pipeline_wall_s"] for run in warm_runs])
        load = median_or_none([run["total_load_s"] for run in cold_runs])
        sec_page = median_or_none([run["sec_per_page"] for run in warm_runs])
        prefill = median_or_none([run["prefill_tok_s"] for run in warm_runs])
        gen = median_or_none([run["gen_tok_s"] for run in warm_runs])
        rss = median_or_none([run["rss_peak_mb"] for run in group])
        json_ratio = median_or_none([run["json_valid_ratio"] for run in group])
        lines.append(
            f"| {model} | {num_ctx} | {pages} | {len(group)} | {fmt(load)} | "
            f"{fmt(wall)} | {fmt(sec_page)} | {fmt(prefill)} | {fmt(gen)} | "
            f"{fmt(rss)} | {fmt(json_ratio)} |"
        )
    lines.extend(
        [
            "",
            "Notes :",
            "- `charge` est la mediane du temps de chargement des runs a froid.",
            "- `temps chaud median` exclut le chargement du modele.",
            "- `RSS pic` est vide si Ollama tourne sur un hote distant.",
            "- `JSON valide` est la proportion de blocs dont la reponse est un JSON parsable.",
            "- Le mode chunké decoupe le document selon `num_ctx - reserve`.",
            "",
        ]
    )
    if meta.get("fast"):
        lines.append(
            "- Mode express : 1 bloc par config et sortie courte ; "
            "`JSON valide` n'est pas representatif."
        )
    return "\n".join(lines)


def fmt(value: float | None) -> str:
    if value is None:
        return "-"
    if isinstance(value, float) and value.is_integer():
        return f"{int(value)}"
    return f"{value:.2f}".rstrip("0").rstrip(".")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark Ollama pour l'assistant juridique.")
    parser.add_argument("--host", default="http://localhost:11434")
    parser.add_argument("--models", default=DEFAULT_MODELS)
    parser.add_argument("--num-ctx", default=DEFAULT_NUM_CTX)
    parser.add_argument("--pages", default=DEFAULT_PAGES)
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--contract", default="bail")
    parser.add_argument("--corpus-dir", type=Path, default=Path("corpus/bench"))
    parser.add_argument("--output-dir", type=Path, default=Path("docs/benchmark/raw"))
    parser.add_argument("--tag", default="")
    parser.add_argument("--reserve-tokens", type=int, default=1400)
    parser.add_argument("--num-predict", type=int, default=900)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--timeout", type=float, default=3600.0)
    parser.add_argument("--local", action="store_true", help="Force la mesure RSS/swap locale.")
    parser.add_argument("--no-monitor", action="store_true", help="Desactive RSS/swap.")
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Preset express : 1 bloc de 600 tokens, 64 tokens en sortie, 1 repetition.",
    )
    parser.add_argument(
        "--max-chunks",
        type=int,
        default=0,
        help="Limite le nombre de blocs traites par run (0 = tous).",
    )
    parser.add_argument(
        "--max-chunk-tokens",
        type=int,
        default=0,
        help="Plafonne la taille des blocs (0 = taille derivee de num_ctx).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche le decoupage sans appeler Ollama.",
    )
    parser.add_argument("--stop-on-error", action="store_true")
    args = parser.parse_args(argv)
    if args.fast:
        args.max_chunks = args.max_chunks or 1
        args.max_chunk_tokens = args.max_chunk_tokens or 600
        args.num_predict = min(args.num_predict, 64)
        args.repeats = 1
    return args


def preflight(client: httpx.Client, host: str, models: list[str]) -> dict[str, Any]:
    try:
        version = ollama_version(client, host)
        tags = ollama_tags(client, host)
    except httpx.HTTPError as exc:
        raise SystemExit(
            f"Ollama injoignable sur {host} : {type(exc).__name__}: {exc}\n"
            "Verifiez l'URL et que le serveur est demarre."
        ) from exc

    available = [item.get("name", "") for item in tags]
    missing = [
        model for model in models if not any(model_matches(name, model) for name in available)
    ]
    if missing:
        raise SystemExit(
            f"Modele(s) absent(s) sur {host} : {', '.join(missing)}\n"
            f"Modeles disponibles : {', '.join(available) or '(aucun)'}"
        )

    details = {
        item.get("name", ""): {
            "digest": item.get("digest"),
            "size": item.get("size"),
            "modified_at": item.get("modified_at"),
            "details": item.get("details"),
        }
        for item in tags
        if any(model_matches(item.get("name", ""), model) for model in models)
    }
    return {"version": version, "models": details}


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    host = normalize_host(args.host)
    models = parse_csv_list(args.models)
    num_ctxs = parse_int_list(args.num_ctx)
    pages_list = parse_int_list(args.pages)

    if args.repeats < 1:
        raise SystemExit("--repeats doit etre >= 1")
    if args.reserve_tokens < 200:
        raise SystemExit("--reserve-tokens doit etre >= 200")

    contracts: dict[int, Path] = {}
    for pages in pages_list:
        path = args.corpus_dir / f"{args.contract}_{pages}p.pdf"
        if not path.exists():
            raise SystemExit(f"Contrat introuvable : {path}")
        contracts[pages] = path

    pages_cache = {pages: read_pages(path) for pages, path in contracts.items()}

    if args.dry_run:
        print(f"Hote : {host}")
        print(f"Modeles : {', '.join(models)}")
        print(f"Contrat : {args.contract}")
        print(
            "| modele | ctx | pages | chunk cible | blocs | tokens approx | prompts |"
        )
        print("|---|---:|---:|---:|---:|---:|---:|")
        for model in models:
            for num_ctx in num_ctxs:
                chunk_tokens = chunk_tokens_for(num_ctx, args)
                for pages in pages_list:
                    chunks = select_chunks(build_chunks(pages_cache[pages], chunk_tokens), args)
                    total = sum(chunk.approx_tokens for chunk in chunks)
                    print(
                        f"| {model} | {num_ctx} | {pages} | {chunk_tokens} | "
                        f"{len(chunks)} | {total} | {len(chunks) * args.repeats} |"
                    )
        return 0

    timeout = httpx.Timeout(connect=15.0, read=args.timeout, write=120.0, pool=args.timeout)
    monitor_enabled = not args.no_monitor and (args.local or is_local_host(host))

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        preflight_info = preflight(client, host, models)
        print(f"Ollama {preflight_info['version']} sur {host}")
        for name, details in preflight_info["models"].items():
            print(f"  modele {name}: digest={details['digest']}")

        runs: list[dict[str, Any]] = []
        requests: list[dict[str, Any]] = []
        started_at = datetime.now(UTC).isoformat()
        meta = build_meta(
            args, host, models, num_ctxs, pages_list,
            preflight_info, started_at, monitor_enabled,
        )

        for model in models:
            for num_ctx in num_ctxs:
                chunk_tokens = chunk_tokens_for(num_ctx, args)
                for pages in pages_list:
                    contract_path = contracts[pages]
                    chunks = select_chunks(build_chunks(pages_cache[pages], chunk_tokens), args)
                    print(
                        f"\n=== {model} | ctx={num_ctx} | {pages} pages | "
                        f"{len(chunks)} blocs | cible={chunk_tokens} tokens ==="
                    )
                    for repeat in range(1, args.repeats + 1):
                        cold_start = repeat == 1
                        monitor = ResourceMonitor() if monitor_enabled else None
                        print(
                            f"  run {repeat}/{args.repeats}"
                            f"{' (a froid)' if cold_start else ''}..."
                        )
                        run, run_requests = run_pipeline(
                            client=client,
                            host=host,
                            model=model,
                            num_ctx=num_ctx,
                            pages_count=pages,
                            contract_path=contract_path,
                            chunks=chunks,
                            repeat=repeat,
                            cold_start=cold_start,
                            monitor=monitor,
                            args=args,
                        )
                        runs.append(run)
                        requests.extend(run_requests)
                        write_outputs(args.output_dir, args.tag, meta, runs, requests)
                        print(
                            f"    total={run['pipeline_wall_s']}s "
                            f"prefill={fmt(run['prefill_tok_s'])} tok/s "
                            f"gen={fmt(run['gen_tok_s'])} tok/s "
                            f"json={fmt(run['json_valid_ratio'])} "
                            f"erreur={run['error'] or '-'}"
                        )
                        if run["error"]:
                            print(f"    echec : {run['error']}", file=sys.stderr)
                            if args.stop_on_error:
                                write_outputs(
                                    args.output_dir,
                                    args.tag,
                                    meta,
                                    runs,
                                    requests,
                                )
                                return 1

        meta["finished_at"] = datetime.now(UTC).isoformat()
        meta["ps_after"] = ollama_ps(client, host)
        json_path = write_outputs(args.output_dir, args.tag, meta, runs, requests)
        print(f"\nResultats bruts : {json_path}")
        print(render_summary(runs, meta))

    return 0


def build_meta(
    args: argparse.Namespace,
    host: str,
    models: list[str],
    num_ctxs: list[int],
    pages_list: list[int],
    preflight_info: dict[str, Any],
    started_at: str,
    monitor_enabled: bool,
) -> dict[str, Any]:
    return {
        "timestamp": started_at,
        "host": host,
        "ollama_version": preflight_info["version"],
        "models_requested": models,
        "models": preflight_info["models"],
        "num_ctx": num_ctxs,
        "pages": pages_list,
        "repeats": args.repeats,
        "mode": "chunked",
        "fast": args.fast,
        "max_chunks": args.max_chunks,
        "max_chunk_tokens": args.max_chunk_tokens,
        "contract": args.contract,
        "corpus_dir": str(args.corpus_dir),
        "reserve_tokens": args.reserve_tokens,
        "num_predict": args.num_predict,
        "temperature": args.temperature,
        "seed": args.seed,
        "monitor_enabled": monitor_enabled,
        "client": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "processor": platform.processor(),
        },
    }


if __name__ == "__main__":
    raise SystemExit(main())
