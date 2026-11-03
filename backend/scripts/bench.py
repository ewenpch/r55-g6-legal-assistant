"""Benchmark des modèles Ollama pour l'assistant de lecture de contrats (tâche S1-07).

Mesure, pour chaque combinaison (modèle, num_ctx, nombre de pages) :

- le temps de chargement du modèle, à froid (tous les modèles sont déchargés avant) ;
- le débit de prefill : tokens de prompt évalués par seconde ;
- le débit de génération : tokens produits par seconde ;
- le RSS pic des processus Ollama (serveur + runner) ;
- la détection de swap : swap des processus Ollama, pages écrites en swap, swap système,
  RAM disponible minimale, rechargement inattendu du modèle.

Le document est traité comme le fera le pipeline (CDC §8.3) : découpé en blocs qui tiennent
dans `num_ctx` (en coupant sur les titres d'articles), puis un appel `/api/chat` en mode JSON
par bloc. La durée totale par document est comparée au budget de 5 minutes (CDC §7.1).

Les documents viennent de la fixture `corpus/bench/` (3 contrats de 6 pages). Un document de
N pages prend les pages du contrat choisi, puis complète avec les contrats suivants (ordre
alphabétique) : 10 pages = 6 pages du bail + 4 pages de l'abonnement.

Usage (depuis `backend/`) :

    pip install -e ".[bench]"
    python scripts/bench.py                    # 2 modèles × num_ctx 2048/4096 × 6/10 pages
    python scripts/bench.py --models llama3.2:3b --num-ctx 2048 --pages 6
    python scripts/bench.py --dry-run          # découpage seul, sans appeler Ollama

Résultats : `docs/benchmark/raw/bench_<date>[_<tag>].{json,csv,md}`, réécrits après chaque run
(un benchmark interrompu garde ses mesures). Aucun contenu de contrat n'est écrit, ni dans les
fichiers ni dans la console : seulement des compteurs, des durées et des tailles (CDC §7.2).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import platform
import re
import statistics
import sys
import threading
import time
import uuid
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
import psutil
import pymupdf

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS_DIR = REPO_ROOT / "corpus" / "bench"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "docs" / "benchmark" / "raw"

DEFAULT_MODELS = ["qwen2.5:7b-instruct", "llama3.2:3b"]
DEFAULT_NUM_CTX = [2048, 4096]
DEFAULT_PAGES = [6, 10]
DEFAULT_CONTRACT = "bail-habitation"

TIME_BUDGET_S = 300.0  # CDC §7.1 : < 5 min par document
MB = 1024 * 1024

# Estimation volontairement prudente (le README de la fixture donne ~3,5 car./token) :
# un bloc sous-estimé déborderait de num_ctx et Ollama tronquerait le prompt sans erreur.
CHARS_PER_TOKEN = 3.2
CHAT_TEMPLATE_TOKENS = 48  # balises de rôle du template de chat + nonce
SAFETY_MARGIN_TOKENS = 128
MIN_CHUNK_TOKENS = 256

# Seuils de détection du swap.
PROC_SWAP_THRESHOLD_MB = 32.0
SWAP_OUT_THRESHOLD_MB = 32.0
SWAP_USED_THRESHOLD_MB = 64.0
LOW_RAM_MB = 256.0
LOW_RAM_RATIO = 0.03
RELOAD_THRESHOLD_S = 1.0

ARTICLE_RE = re.compile(r"^\s*article\s+\d+", re.IGNORECASE)

SYSTEM_PROMPT = """Tu aides un particulier à comprendre un contrat. Tu reçois un extrait du \
contrat. Réponds UNIQUEMENT par un objet JSON de la forme :
{
  "contract_type": "type de contrat ou null",
  "parties": [{"name": "nom", "role": "rôle"}],
  "key_dates": [{"label": "libellé", "date": "date"}],
  "amounts": [{"label": "libellé", "value": "montant"}],
  "obligations": [{"party": "partie", "items": ["obligation"]}],
  "clauses_to_check": [
    {"title": "titre court", "quote": "extrait copié mot pour mot", \
"explanation": "explication simple", "level": "info|attention|important", "page": 1}
  ]
}
Règles : n'utilise que l'extrait fourni, copie les citations mot pour mot, n'invente aucune \
clause, réponds en français, en langage clair."""

USER_TEMPLATE = "Extrait du contrat (pages {page_start} à {page_end}) :\n\n{text}"


# --------------------------------------------------------------------------------------------
# Document et découpage
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Page:
    number: int  # numéro dans le document assemblé (1..N)
    source: str  # contrat d'origine
    text: str


@dataclass(frozen=True)
class Chunk:
    index: int
    page_start: int
    page_end: int
    text: str
    est_tokens: int


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / CHARS_PER_TOKEN)


def read_pdf_pages(path: Path) -> list[str]:
    with pymupdf.open(path) as document:
        return [page.get_text("text") for page in document]


def load_corpus(corpus_dir: Path) -> dict[str, list[str]]:
    """Charge chaque PDF de la fixture : nom (sans extension) -> texte des pages."""
    paths = sorted(corpus_dir.glob("*.pdf"))
    if not paths:
        raise SystemExit(f"Aucun PDF dans {corpus_dir}")
    corpus = {path.stem: read_pdf_pages(path) for path in paths}
    for name, pages in corpus.items():
        empty = [number for number, text in enumerate(pages, start=1) if not text.strip()]
        if empty:
            raise SystemExit(f"{name} : pages sans texte extractible {empty}")
    return corpus


def assemble_document(corpus: dict[str, list[str]], first: str, n_pages: int) -> list[Page]:
    """Document de n_pages : pages de `first`, complétées par les contrats suivants."""
    if first not in corpus:
        raise ValueError(f"contrat inconnu : {first} (disponibles : {', '.join(sorted(corpus))})")
    order = [first] + [name for name in sorted(corpus) if name != first]
    pool = [(name, text) for name in order for text in corpus[name]]
    if not 1 <= n_pages <= len(pool):
        raise ValueError(f"{n_pages} pages demandées, la fixture en contient {len(pool)}")
    return [
        Page(number=number, source=name, text=text)
        for number, (name, text) in enumerate(pool[:n_pages], start=1)
    ]


def prompt_overhead_tokens() -> int:
    template = USER_TEMPLATE.format(page_start=10, page_end=10, text="")
    return estimate_tokens(SYSTEM_PROMPT) + estimate_tokens(template) + CHAT_TEMPLATE_TOKENS


def chunk_budget(num_ctx: int, num_predict: int) -> int:
    """Tokens de contrat par bloc : num_ctx moins consignes, réponse et marge."""
    budget = num_ctx - num_predict - prompt_overhead_tokens() - SAFETY_MARGIN_TOKENS
    if budget < MIN_CHUNK_TOKENS:
        raise ValueError(
            f"num_ctx={num_ctx} trop petit pour num_predict={num_predict} : "
            f"il reste {budget} tokens par bloc (minimum {MIN_CHUNK_TOKENS})"
        )
    return budget


def _split_sections(pages: list[Page]) -> list[tuple[int, str]]:
    """Sections (page, texte) coupées sur les titres d'articles et sur les sauts de page."""
    sections: list[tuple[int, str]] = []
    for page in pages:
        current: list[str] = []
        for line in page.text.splitlines():
            if ARTICLE_RE.match(line) and current:
                sections.append((page.number, "\n".join(current)))
                current = []
            current.append(line)
        if current:
            sections.append((page.number, "\n".join(current)))
    return sections


def _split_long(text: str, budget: int) -> list[str]:
    """Coupe une section trop longue ligne par ligne (et une ligne géante par caractères)."""
    max_chars = int(budget * CHARS_PER_TOKEN)
    lines: list[str] = []
    for line in text.splitlines():
        lines.extend(line[i : i + max_chars] for i in range(0, max(len(line), 1), max_chars))
    pieces: list[str] = []
    current: list[str] = []
    for line in lines:
        if current and estimate_tokens("\n".join([*current, line])) > budget:
            pieces.append("\n".join(current))
            current = []
        current.append(line)
    if current:
        pieces.append("\n".join(current))
    return pieces


def build_chunks(pages: list[Page], budget: int) -> list[Chunk]:
    """Regroupe les sections en blocs d'au plus `budget` tokens estimés, pages conservées."""
    pieces: list[tuple[int, str]] = []
    for page_number, text in _split_sections(pages):
        if estimate_tokens(text) <= budget:
            pieces.append((page_number, text))
        else:
            pieces.extend((page_number, piece) for piece in _split_long(text, budget))

    chunks: list[Chunk] = []
    current: list[tuple[int, str]] = []

    def flush() -> None:
        if not current:
            return
        text = "\n".join(piece for _, piece in current)
        chunks.append(
            Chunk(
                index=len(chunks) + 1,
                page_start=current[0][0],
                page_end=current[-1][0],
                text=text,
                est_tokens=estimate_tokens(text),
            )
        )
        current.clear()

    for page_number, text in pieces:
        candidate = "\n".join([*(piece for _, piece in current), text])
        if current and estimate_tokens(candidate) > budget:
            flush()
        current.append((page_number, text))
    flush()
    return chunks


# --------------------------------------------------------------------------------------------
# Mémoire : RSS pic et détection de swap
# --------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Sample:
    rss: int  # somme des RSS des processus Ollama (octets)
    proc_swap: int | None  # swap des processus Ollama (Linux uniquement), octets
    available: int  # RAM disponible système
    swap_used: int  # swap système utilisé
    swap_out: int  # octets écrits en swap depuis le démarrage (0 si non fourni par l'OS)


@dataclass
class MemoryStats:
    samples: int
    rss_peak_mb: float | None
    proc_swap_peak_mb: float | None
    ram_total_mb: float
    ram_available_min_mb: float | None
    swap_used_delta_mb: float | None
    swap_out_delta_mb: float | None
    swap: str  # "oui" | "suspect" | "non" | "inconnu"
    swap_reasons: list[str] = field(default_factory=list)


def is_ollama_process(name: str) -> bool:
    name = name.lower()
    if "ollama app" in name:  # icône de la barre des tâches (Windows/macOS), pas le serveur
        return False
    return "ollama" in name or "llama-server" in name or "llama_server" in name


def _linux_vmswap(pid: int) -> int | None:
    """VmSwap du processus, lisible même si Ollama tourne sous un autre utilisateur."""
    try:
        with open(f"/proc/{pid}/status", encoding="ascii") as handle:
            for line in handle:
                if line.startswith("VmSwap:"):
                    return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def sample_system() -> Sample:
    rss = 0
    proc_swap: int | None = 0 if sys.platform.startswith("linux") else None
    for process in psutil.process_iter(["name", "memory_info"]):
        if not is_ollama_process(process.info.get("name") or ""):
            continue
        memory = process.info.get("memory_info")
        if memory is not None:
            rss += memory.rss
        if proc_swap is not None:
            proc_swap += _linux_vmswap(process.pid) or 0
    virtual = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return Sample(
        rss=rss,
        proc_swap=proc_swap,
        available=virtual.available,
        swap_used=swap.used,
        swap_out=getattr(swap, "sout", 0) or 0,
    )


def detect_swap(
    *,
    proc_swap_peak_mb: float | None,
    swap_out_delta_mb: float | None,
    swap_used_delta_mb: float | None,
    ram_available_min_mb: float | None,
    ram_total_mb: float,
    reloads: int = 0,
) -> tuple[str, list[str]]:
    """Verdict « oui / suspect / non » et raisons, à partir des indicateurs mémoire."""
    reasons: list[str] = []
    if proc_swap_peak_mb is not None and proc_swap_peak_mb >= PROC_SWAP_THRESHOLD_MB:
        reasons.append(f"processus Ollama en swap : {proc_swap_peak_mb:.0f} Mo")
    if swap_out_delta_mb is not None and swap_out_delta_mb >= SWAP_OUT_THRESHOLD_MB:
        reasons.append(f"{swap_out_delta_mb:.0f} Mo écrits en swap pendant la mesure")
    if swap_used_delta_mb is not None and swap_used_delta_mb >= SWAP_USED_THRESHOLD_MB:
        reasons.append(f"swap système +{swap_used_delta_mb:.0f} Mo")
    if reasons:
        return "oui", reasons

    low_ram = max(LOW_RAM_MB, LOW_RAM_RATIO * ram_total_mb)
    if ram_available_min_mb is not None and ram_available_min_mb < low_ram:
        reasons.append(f"RAM disponible tombée à {ram_available_min_mb:.0f} Mo")
    if reloads:
        reasons.append(f"modèle rechargé {reloads} fois pendant la mesure")
    if reasons:
        return "suspect", reasons
    if ram_available_min_mb is None:
        return "inconnu", ["aucun échantillon mémoire"]
    return "non", []


def summarize_samples(samples: list[Sample], ram_total: int, reloads: int = 0) -> MemoryStats:
    ram_total_mb = round(ram_total / MB, 1)
    if not samples:
        return MemoryStats(
            samples=0,
            rss_peak_mb=None,
            proc_swap_peak_mb=None,
            ram_total_mb=ram_total_mb,
            ram_available_min_mb=None,
            swap_used_delta_mb=None,
            swap_out_delta_mb=None,
            swap="inconnu",
            swap_reasons=["mesure mémoire désactivée"],
        )
    rss_peak = max(sample.rss for sample in samples)
    proc_swaps = [sample.proc_swap for sample in samples if sample.proc_swap is not None]
    stats = {
        "proc_swap_peak_mb": round(max(proc_swaps) / MB, 1) if proc_swaps else None,
        "swap_out_delta_mb": round((samples[-1].swap_out - samples[0].swap_out) / MB, 1),
        "swap_used_delta_mb": round(
            (max(sample.swap_used for sample in samples) - samples[0].swap_used) / MB, 1
        ),
        "ram_available_min_mb": round(min(sample.available for sample in samples) / MB, 1),
    }
    verdict, reasons = detect_swap(**stats, ram_total_mb=ram_total_mb, reloads=reloads)
    return MemoryStats(
        samples=len(samples),
        rss_peak_mb=round(rss_peak / MB, 1) if rss_peak else None,
        ram_total_mb=ram_total_mb,
        swap=verdict,
        swap_reasons=reasons,
        **stats,
    )


class ResourceMonitor:
    """Échantillonne la mémoire dans un thread pendant une mesure."""

    def __init__(self, interval_s: float = 0.25, sampler: Callable[[], Sample] = sample_system):
        self.interval_s = interval_s
        self.sampler = sampler
        self.samples: list[Sample] = []
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _take(self) -> None:
        try:
            self.samples.append(self.sampler())
        except (psutil.Error, OSError):
            pass

    def _run(self) -> None:
        while not self._stop.wait(self.interval_s):
            self._take()

    def __enter__(self) -> ResourceMonitor:
        self._take()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._take()


class NullMonitor:
    samples: list[Sample] = []

    def __enter__(self) -> NullMonitor:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


# --------------------------------------------------------------------------------------------
# Client Ollama
# --------------------------------------------------------------------------------------------


class OllamaError(RuntimeError):
    pass


def normalize_host(host: str) -> str:
    host = host.strip().rstrip("/")
    if "://" not in host:
        host = f"http://{host}"
    parsed = urlparse(host)
    hostname = parsed.hostname or "localhost"
    if hostname == "0.0.0.0":  # valeur de OLLAMA_HOST côté serveur, pas une adresse cliente
        hostname = "127.0.0.1"
    if ":" in hostname:
        hostname = f"[{hostname}]"
    return f"{parsed.scheme}://{hostname}:{parsed.port or 11434}"


def is_local_host(host: str) -> bool:
    return (urlparse(host).hostname or "").lower() in {"localhost", "127.0.0.1", "::1"}


def model_matches(name: str, model: str) -> bool:
    """`llama3.2` désigne `llama3.2:latest` côté Ollama."""
    return name == model or (":" not in model and name == f"{model}:latest")


def _ns_to_s(value: Any) -> float:
    return (value or 0) / 1e9


class OllamaClient:
    def __init__(
        self,
        host: str,
        timeout_s: float,
        transport: httpx.BaseTransport | None = None,
    ):
        self.host = host
        self.http = httpx.Client(
            base_url=host,
            timeout=httpx.Timeout(timeout_s, connect=10.0),
            transport=transport,
        )

    def close(self) -> None:
        self.http.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self.http.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise OllamaError(f"{type(exc).__name__}: {exc}") from exc
        if response.is_error:
            try:
                detail = response.json().get("error", response.text)
            except ValueError:
                detail = response.text
            raise OllamaError(f"HTTP {response.status_code} sur {path} : {detail}")
        return response.json()

    def version(self) -> str | None:
        return self._request("GET", "/api/version").get("version")

    def tags(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/tags").get("models", [])

    def ps(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/ps").get("models", [])

    def unload_all(self, wait_s: float = 60.0) -> None:
        for loaded in self.ps():
            name = loaded.get("name") or loaded.get("model")
            if name:
                self._request("POST", "/api/generate", json={"model": name, "keep_alive": 0})
        deadline = time.monotonic() + wait_s
        while self.ps():
            if time.monotonic() > deadline:
                raise OllamaError("des modèles sont toujours chargés après le déchargement")
            time.sleep(0.5)

    def load(self, model: str, num_ctx: int, keep_alive: str) -> tuple[float, dict[str, Any]]:
        """Charge le modèle sans générer (prompt vide). Renvoie (durée mesurée, réponse)."""
        started = time.perf_counter()
        data = self._request(
            "POST",
            "/api/generate",
            json={"model": model, "keep_alive": keep_alive, "options": {"num_ctx": num_ctx}},
        )
        return time.perf_counter() - started, data

    def chat(
        self, model: str, messages: list[dict[str, str]], options: dict[str, Any], keep_alive: str
    ) -> tuple[float, dict[str, Any]]:
        started = time.perf_counter()
        data = self._request(
            "POST",
            "/api/chat",
            json={
                "model": model,
                "messages": messages,
                "stream": False,
                "format": "json",
                "keep_alive": keep_alive,
                "options": options,
            },
        )
        return time.perf_counter() - started, data


# --------------------------------------------------------------------------------------------
# Mesures
# --------------------------------------------------------------------------------------------


def is_json_object(text: str) -> bool:
    try:
        return isinstance(json.loads(text), dict)
    except (TypeError, ValueError):
        return False


def request_metrics(data: dict[str, Any], num_ctx: int, num_predict: int) -> dict[str, Any]:
    """Métriques d'un appel /api/chat (durées Ollama en nanosecondes)."""
    prompt_tokens = data.get("prompt_eval_count") or 0
    gen_tokens = data.get("eval_count") or 0
    prefill_s = _ns_to_s(data.get("prompt_eval_duration"))
    gen_s = _ns_to_s(data.get("eval_duration"))
    content = (data.get("message") or {}).get("content", "")
    return {
        "prompt_tokens": prompt_tokens,
        "gen_tokens": gen_tokens,
        "prefill_s": round(prefill_s, 3),
        "gen_s": round(gen_s, 3),
        "load_s": round(_ns_to_s(data.get("load_duration")), 3),
        "total_s": round(_ns_to_s(data.get("total_duration")), 3),
        "prefill_tok_s": round(prompt_tokens / prefill_s, 2) if prefill_s > 0 else None,
        "gen_tok_s": round(gen_tokens / gen_s, 2) if gen_s > 0 else None,
        "done_reason": data.get("done_reason"),
        # Ollama tronque le prompt sans erreur s'il dépasse num_ctx : on le repère ici.
        "context_overflow": prompt_tokens > num_ctx - num_predict,
        "json_valid": is_json_object(content),
        "response_chars": len(content),
    }


def build_messages(chunk: Chunk, bust_cache: bool) -> list[dict[str, str]]:
    system = SYSTEM_PROMPT
    if bust_cache:
        # Un préfixe unique empêche Ollama de réutiliser le cache KV d'une requête précédente :
        # le prefill mesuré porte alors sur tout le prompt.
        system = f"[mesure {uuid.uuid4().hex[:12]}]\n{SYSTEM_PROMPT}"
    user = USER_TEMPLATE.format(
        page_start=chunk.page_start, page_end=chunk.page_end, text=chunk.text
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _sum(values: Iterable[float | int | None]) -> float:
    return sum(value or 0 for value in values)


def aggregate_requests(requests: list[dict[str, Any]], pages: int) -> dict[str, Any]:
    prompt_tokens = int(_sum(r["prompt_tokens"] for r in requests))
    gen_tokens = int(_sum(r["gen_tokens"] for r in requests))
    prefill_s = _sum(r["prefill_s"] for r in requests)
    gen_s = _sum(r["gen_s"] for r in requests)
    chars = _sum(r["prompt_chars"] for r in requests)
    return {
        "prompt_tokens": prompt_tokens,
        "gen_tokens": gen_tokens,
        "prefill_s": round(prefill_s, 3),
        "gen_s": round(gen_s, 3),
        "prefill_tok_s": round(prompt_tokens / prefill_s, 2) if prefill_s > 0 else None,
        "gen_tok_s": round(gen_tokens / gen_s, 2) if gen_s > 0 else None,
        "prompt_tokens_per_page": round(prompt_tokens / pages, 1) if pages else None,
        "chars_per_token": round(chars / prompt_tokens, 2) if prompt_tokens else None,
        "json_valid": sum(1 for r in requests if r["json_valid"]),
        "length_stops": sum(1 for r in requests if r["done_reason"] == "length"),
        "context_overflows": sum(1 for r in requests if r["context_overflow"]),
        "reloads": sum(1 for r in requests if r["load_s"] > RELOAD_THRESHOLD_S),
    }


@dataclass
class BenchConfig:
    models: list[str]
    num_ctx: list[int]
    pages: list[int]
    contracts: list[str]
    repeats: int
    num_predict: int
    temperature: float
    seed: int
    keep_alive: str
    bust_cache: bool
    sample_interval_s: float


class Bench:
    def __init__(
        self,
        client: OllamaClient,
        corpus: dict[str, list[str]],
        config: BenchConfig,
        monitor_factory: Callable[[], ResourceMonitor | NullMonitor],
        on_progress: Callable[[], None] = lambda: None,
        log: Callable[[str], None] = print,
    ):
        self.client = client
        self.corpus = corpus
        self.config = config
        self.monitor_factory = monitor_factory
        self.on_progress = on_progress
        self.log = log
        self.ram_total = psutil.virtual_memory().total
        self.loads: list[dict[str, Any]] = []
        self.runs: list[dict[str, Any]] = []

    def run(self) -> None:
        for model in self.config.models:
            for num_ctx in self.config.num_ctx:
                self.log(f"\n=== {model} · num_ctx={num_ctx} ===")
                load = self.measure_load(model, num_ctx)
                self.loads.append(load)
                self.on_progress()
                if load["error"]:
                    self.log(f"  chargement impossible : {load['error']}")
                    continue
                self.log(
                    f"  chargement {load['load_s']:.1f} s · RSS pic {_fmt(load['rss_peak_mb'])} Mo"
                    f" · swap {load['swap']}"
                )
                for pages in self.config.pages:
                    for contract in self.config.contracts:
                        for repeat in range(1, self.config.repeats + 1):
                            run = self.measure_document(model, num_ctx, pages, contract, repeat)
                            self.runs.append(run)
                            self.on_progress()
                            self.log(_run_line(run))

    def measure_load(self, model: str, num_ctx: int) -> dict[str, Any]:
        record: dict[str, Any] = {"model": model, "num_ctx": num_ctx, "error": None}
        try:
            self.client.unload_all()
            with self.monitor_factory() as monitor:
                wall_s, data = self.client.load(model, num_ctx, self.config.keep_alive)
            loaded = next(
                (m for m in self.client.ps() if model_matches(m.get("name", ""), model)), {}
            )
        except OllamaError as exc:
            record.update({"load_s": None, "error": str(exc)})
            return record
        memory = summarize_samples(monitor.samples, self.ram_total)
        record.update(
            {
                "load_s": round(wall_s, 3),
                "ollama_load_s": round(_ns_to_s(data.get("load_duration")), 3) or None,
                "model_size_mb": _mb(loaded.get("size")),
                "model_size_vram_mb": _mb(loaded.get("size_vram")),
                "context_length": loaded.get("context_length"),
                **asdict(memory),
            }
        )
        return record

    def measure_document(
        self, model: str, num_ctx: int, pages: int, contract: str, repeat: int
    ) -> dict[str, Any]:
        cfg = self.config
        budget = chunk_budget(num_ctx, cfg.num_predict)
        document = assemble_document(self.corpus, contract, pages)
        chunks = build_chunks(document, budget)
        options = {
            "num_ctx": num_ctx,
            "num_predict": cfg.num_predict,
            "temperature": cfg.temperature,
            "seed": cfg.seed,
        }
        requests: list[dict[str, Any]] = []
        error: str | None = None
        started = time.perf_counter()
        with self.monitor_factory() as monitor:
            for chunk in chunks:
                messages = build_messages(chunk, cfg.bust_cache)
                try:
                    wall_s, data = self.client.chat(model, messages, options, cfg.keep_alive)
                except OllamaError as exc:
                    error = f"bloc {chunk.index}/{len(chunks)} : {exc}"
                    break
                requests.append(
                    {
                        "chunk": chunk.index,
                        "page_start": chunk.page_start,
                        "page_end": chunk.page_end,
                        "est_tokens": chunk.est_tokens,
                        "prompt_chars": sum(len(m["content"]) for m in messages),
                        "wall_s": round(wall_s, 3),
                        **request_metrics(data, num_ctx, cfg.num_predict),
                    }
                )
        wall_s = time.perf_counter() - started
        totals = aggregate_requests(requests, pages)
        memory = summarize_samples(monitor.samples, self.ram_total, reloads=totals["reloads"])
        return {
            "model": model,
            "num_ctx": num_ctx,
            "pages": pages,
            "contract": contract,
            "sources": sorted({page.source for page in document}),
            "repeat": repeat,
            "chunk_budget_tokens": budget,
            "chunks": len(chunks),
            "chunks_done": len(requests),
            "wall_s": round(wall_s, 3),
            "within_budget": error is None and wall_s < TIME_BUDGET_S,
            **totals,
            **asdict(memory),
            "error": error,
            "requests": requests,
        }


# --------------------------------------------------------------------------------------------
# Restitution
# --------------------------------------------------------------------------------------------

CSV_FIELDS = [
    "model",
    "num_ctx",
    "pages",
    "contract",
    "repeat",
    "load_s",
    "chunks",
    "chunks_done",
    "chunk_budget_tokens",
    "prompt_tokens",
    "gen_tokens",
    "prefill_s",
    "gen_s",
    "prefill_tok_s",
    "gen_tok_s",
    "wall_s",
    "within_budget",
    "prompt_tokens_per_page",
    "chars_per_token",
    "json_valid",
    "length_stops",
    "context_overflows",
    "reloads",
    "rss_peak_mb",
    "load_rss_peak_mb",
    "proc_swap_peak_mb",
    "swap_out_delta_mb",
    "swap_used_delta_mb",
    "ram_available_min_mb",
    "swap",
    "swap_reasons",
    "error",
]

SWAP_SEVERITY = {"inconnu": 0, "non": 1, "suspect": 2, "oui": 3}


def _mb(value: Any) -> float | None:
    return round(value / MB, 1) if value else None


def _fmt(value: Any, digits: int = 1) -> str:
    if value is None:
        return "–"
    if isinstance(value, bool):
        return "oui" if value else "non"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _median(values: Iterable[float | None]) -> float | None:
    clean = [value for value in values if value is not None]
    return statistics.median(clean) if clean else None


def _run_line(run: dict[str, Any]) -> str:
    status = (
        f"ERREUR {run['error']}"
        if run["error"]
        else ("< 5 min" if run["within_budget"] else "> 5 min")
    )
    return (
        f"  {run['pages']:>2} p · {run['contract']} · essai {run['repeat']} : "
        f"{run['wall_s']:.1f} s ({status}) · {run['chunks_done']}/{run['chunks']} blocs · "
        f"prefill {_fmt(run['prefill_tok_s'])} tok/s · gen {_fmt(run['gen_tok_s'])} tok/s · "
        f"RSS {_fmt(run['rss_peak_mb'])} Mo · swap {run['swap']}"
    )


def csv_rows(loads: list[dict[str, Any]], runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    load_by_key = {(load["model"], load["num_ctx"]): load for load in loads}
    rows = []
    for run in runs:
        load = load_by_key.get((run["model"], run["num_ctx"]), {})
        row = {key: run.get(key) for key in CSV_FIELDS}
        row["load_s"] = load.get("load_s")
        row["load_rss_peak_mb"] = load.get("rss_peak_mb")
        row["swap_reasons"] = " ; ".join(run["swap_reasons"])
        rows.append(row)
    return rows


def render_markdown(meta: dict[str, Any], loads: list[dict], runs: list[dict]) -> str:
    machine = meta["machine"]
    lines = [
        f"# Benchmark Ollama — {meta['started_at']}",
        "",
        f"- Machine : {machine['os']} · {machine['cpu']} · "
        f"{machine['cpu_cores_physical']} cœurs / {machine['cpu_threads']} threads · "
        f"RAM {machine['ram_total_gb']} Go · swap {machine['swap_total_gb']} Go",
        f"- Ollama {meta['ollama_version']} sur {meta['host']}"
        f" · mesure mémoire : {'oui' if meta['monitor'] else 'non (hôte distant)'}",
        f"- num_predict={meta['config']['num_predict']} · "
        f"température={meta['config']['temperature']} · essais={meta['config']['repeats']}",
        "",
        "## Chargement (à froid)",
        "",
        "| Modèle | num_ctx | Chargement (s) | Taille en mémoire (Mo) | RSS pic (Mo) | Swap |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for load in loads:
        if load["error"]:
            lines.append(
                f"| {load['model']} | {load['num_ctx']} | erreur : {load['error']} | | | |"
            )
            continue
        lines.append(
            f"| {load['model']} | {load['num_ctx']} | {_fmt(load['load_s'])} | "
            f"{_fmt(load['model_size_mb'], 0)} | {_fmt(load['rss_peak_mb'], 0)} | "
            f"{load['swap']} |"
        )

    lines += [
        "",
        "## Document complet (médiane des essais)",
        "",
        "| Modèle | num_ctx | Pages | Contrat | Blocs | Prefill tok/s | Génération tok/s "
        "| Durée (s) | < 5 min | RSS pic (Mo) | Swap | JSON valide | Alertes |",
        "|---|---:|---:|---|---:|---:|---:|---:|---|---:|---|---:|---|",
    ]
    groups: dict[tuple, list[dict]] = {}
    for run in runs:
        groups.setdefault((run["model"], run["num_ctx"], run["pages"], run["contract"]), [])
        groups[(run["model"], run["num_ctx"], run["pages"], run["contract"])].append(run)
    for (model, num_ctx, pages, contract), group in groups.items():
        ok = [run for run in group if not run["error"]]
        errors = [run["error"] for run in group if run["error"]]
        alerts = []
        overflows = sum(run["context_overflows"] for run in group)
        if overflows:
            alerts.append(f"{overflows} bloc(s) hors contexte")
        length_stops = sum(run["length_stops"] for run in group)
        if length_stops:
            alerts.append(f"{length_stops} réponse(s) coupée(s) par num_predict")
        reasons = sorted({reason for run in group for reason in run["swap_reasons"]})
        alerts += [reason for reason in reasons if reason != "mesure mémoire désactivée"]
        alerts += errors
        swap = max((run["swap"] for run in group), key=SWAP_SEVERITY.__getitem__)
        wall = _median(run["wall_s"] for run in ok)
        json_valid = sum(run["json_valid"] for run in group)
        json_total = sum(run["chunks_done"] for run in group)
        lines.append(
            f"| {model} | {num_ctx} | {pages} | {contract} | {group[0]['chunks']} | "
            f"{_fmt(_median(run['prefill_tok_s'] for run in ok))} | "
            f"{_fmt(_median(run['gen_tok_s'] for run in ok))} | {_fmt(wall)} | "
            f"{_fmt(wall < TIME_BUDGET_S) if wall is not None else '–'} | "
            f"{_fmt(max((r['rss_peak_mb'] or 0 for r in group), default=0) or None, 0)} | "
            f"{swap} | {json_valid}/{json_total} | {' ; '.join(alerts) or '–'} |"
        )
    lines += [
        "",
        "Prefill et génération : tokens / durée cumulée de la phase sur tous les blocs "
        "(compteurs Ollama). Durée : temps mesuré côté client pour tout le document, modèle "
        "déjà chargé. Swap : « oui » si un processus Ollama ou le système écrit en swap, "
        "« suspect » si la RAM disponible s'effondre ou si le modèle est rechargé en cours de "
        "route.",
        "",
    ]
    return "\n".join(lines)


def machine_info() -> dict[str, Any]:
    cpu = platform.processor() or platform.machine()
    if sys.platform.startswith("linux"):
        try:
            for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
                if line.startswith("model name"):
                    cpu = line.split(":", 1)[1].strip()
                    break
        except OSError:
            pass
    return {
        "os": platform.platform(),
        "cpu": cpu,
        "cpu_cores_physical": psutil.cpu_count(logical=False),
        "cpu_threads": psutil.cpu_count(logical=True),
        "ram_total_gb": round(psutil.virtual_memory().total / 1024**3, 1),
        "swap_total_gb": round(psutil.swap_memory().total / 1024**3, 1),
        "python": platform.python_version(),
    }


def write_results(
    output_dir: Path, stem: str, meta: dict[str, Any], loads: list[dict], runs: list[dict]
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{stem}.json"
    payload = {"meta": meta, "loads": loads, "runs": runs}
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with (output_dir / f"{stem}.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(csv_rows(loads, runs))
    (output_dir / f"{stem}.md").write_text(render_markdown(meta, loads, runs), encoding="utf-8")
    return json_path


# --------------------------------------------------------------------------------------------
# Ligne de commande
# --------------------------------------------------------------------------------------------


def _list(cast: Callable[[str], Any]) -> Callable[[str], list[Any]]:
    def parse(value: str) -> list[Any]:
        items = [cast(item.strip()) for item in value.split(",") if item.strip()]
        if not items:
            raise argparse.ArgumentTypeError("liste vide")
        return items

    return parse


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark Ollama : chargement, prefill, génération, RSS pic, swap.",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
        help="serveur Ollama (défaut : $OLLAMA_HOST ou http://localhost:11434)",
    )
    parser.add_argument(
        "--models", type=_list(str), default=DEFAULT_MODELS, help="modèles séparés par des virgules"
    )
    parser.add_argument(
        "--num-ctx",
        type=_list(int),
        default=DEFAULT_NUM_CTX,
        help="tailles de contexte, ex. 2048,4096",
    )
    parser.add_argument(
        "--pages",
        type=_list(int),
        default=DEFAULT_PAGES,
        help="nombres de pages par document, ex. 6,10",
    )
    parser.add_argument(
        "--contracts",
        type=_list(str),
        default=[DEFAULT_CONTRACT],
        help="contrat(s) de départ de la fixture, ou « all »",
    )
    parser.add_argument("--repeats", type=int, default=1, help="essais par configuration")
    parser.add_argument(
        "--num-predict", type=int, default=512, help="tokens générés au maximum par bloc"
    )
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--keep-alive",
        default="30m",
        help="durée de maintien du modèle en mémoire entre deux blocs",
    )
    parser.add_argument(
        "--allow-cache",
        action="store_true",
        help="laisse Ollama réutiliser le cache KV (prefill sous-estimé)",
    )
    parser.add_argument(
        "--timeout", type=float, default=900.0, help="délai max d'une requête Ollama, en secondes"
    )
    parser.add_argument(
        "--sample-interval",
        type=float,
        default=0.25,
        help="période d'échantillonnage mémoire, en secondes",
    )
    parser.add_argument("--no-monitor", action="store_true", help="désactive RSS et swap")
    parser.add_argument("--corpus-dir", type=Path, default=DEFAULT_CORPUS_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--tag", default="", help="suffixe des fichiers de résultats")
    parser.add_argument(
        "--dry-run", action="store_true", help="affiche le découpage sans appeler Ollama"
    )
    args = parser.parse_args(argv)
    if args.repeats < 1:
        parser.error("--repeats doit être >= 1")
    if args.num_predict < 1:
        parser.error("--num-predict doit être >= 1")
    for num_ctx in args.num_ctx:
        try:
            chunk_budget(num_ctx, args.num_predict)
        except ValueError as exc:
            parser.error(str(exc))
    return args


def dry_run(corpus: dict[str, list[str]], args: argparse.Namespace) -> None:
    print("| num_ctx | pages | contrat | tokens/bloc | blocs | tokens estimés | pages par bloc |")
    print("|---:|---:|---|---:|---:|---:|---|")
    for num_ctx in args.num_ctx:
        budget = chunk_budget(num_ctx, args.num_predict)
        for pages in args.pages:
            for contract in args.contracts:
                chunks = build_chunks(assemble_document(corpus, contract, pages), budget)
                spans = ", ".join(f"{c.page_start}-{c.page_end}" for c in chunks)
                total = sum(chunk.est_tokens for chunk in chunks)
                print(
                    f"| {num_ctx} | {pages} | {contract} | {budget} | {len(chunks)} | "
                    f"{total} | {spans} |"
                )


def preflight(client: OllamaClient, models: list[str]) -> tuple[str | None, dict[str, Any]]:
    try:
        version = client.version()
        tags = client.tags()
    except OllamaError as exc:
        raise SystemExit(
            f"Ollama injoignable sur {client.host} ({exc}).\n"
            "Démarrez-le (`ollama serve` ou l'application) ou précisez --host."
        ) from exc
    available = [tag.get("name", "") for tag in tags]
    missing = [m for m in models if not any(model_matches(name, m) for name in available)]
    if missing:
        pulls = "\n".join(f"  ollama pull {model}" for model in missing)
        raise SystemExit(f"Modèle(s) absent(s) : {', '.join(missing)}. Installez-les :\n{pulls}")
    details = {}
    for model in models:
        tag = next(t for t in tags if model_matches(t.get("name", ""), model))
        info = tag.get("details") or {}
        details[model] = {
            "digest": tag.get("digest"),
            "size_mb": _mb(tag.get("size")),
            "parameter_size": info.get("parameter_size"),
            "quantization_level": info.get("quantization_level"),
            "family": info.get("family"),
        }
    return version, details


def main(argv: list[str] | None = None, transport: httpx.BaseTransport | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = parse_args(argv)
    corpus = load_corpus(args.corpus_dir)
    if args.contracts == ["all"]:
        args.contracts = sorted(corpus)
    for contract in args.contracts:
        for pages in args.pages:
            try:
                assemble_document(corpus, contract, pages)
            except ValueError as exc:
                raise SystemExit(str(exc)) from exc

    if args.dry_run:
        dry_run(corpus, args)
        return 0

    host = normalize_host(args.host)
    monitor_enabled = not args.no_monitor and is_local_host(host)
    client = OllamaClient(host, args.timeout, transport=transport)
    try:
        version, models = preflight(client, args.models)
        config = BenchConfig(
            models=args.models,
            num_ctx=args.num_ctx,
            pages=args.pages,
            contracts=args.contracts,
            repeats=args.repeats,
            num_predict=args.num_predict,
            temperature=args.temperature,
            seed=args.seed,
            keep_alive=args.keep_alive,
            bust_cache=not args.allow_cache,
            sample_interval_s=args.sample_interval,
        )
        started_at = datetime.now().astimezone()
        meta = {
            "started_at": started_at.isoformat(timespec="seconds"),
            "finished_at": None,
            "host": host,
            "ollama_version": version,
            "models": models,
            "monitor": monitor_enabled,
            "machine": machine_info(),
            "config": asdict(config),
            "chars_per_token_estimate": CHARS_PER_TOKEN,
            "time_budget_s": TIME_BUDGET_S,
        }
        stem = f"bench_{started_at:%Y%m%d-%H%M%S}" + (f"_{args.tag}" if args.tag else "")

        def monitor_factory() -> ResourceMonitor | NullMonitor:
            if monitor_enabled:
                return ResourceMonitor(interval_s=args.sample_interval)
            return NullMonitor()

        bench = Bench(client, corpus, config, monitor_factory)
        bench.on_progress = lambda: write_results(
            args.output_dir, stem, meta, bench.loads, bench.runs
        )
        print(
            f"Ollama {version} sur {host} · mesure mémoire : {'oui' if monitor_enabled else 'non'}"
        )
        if not monitor_enabled and not args.no_monitor:
            print("  hôte distant : RSS et swap ne peuvent pas être mesurés depuis cette machine")
        interrupted = False
        try:
            bench.run()
        except KeyboardInterrupt:
            interrupted = True
            print("\nInterrompu : résultats partiels conservés.")
        meta["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        meta["interrupted"] = interrupted
        json_path = write_results(args.output_dir, stem, meta, bench.loads, bench.runs)
    finally:
        client.close()

    print()
    print(render_markdown(meta, bench.loads, bench.runs))
    print(f"Résultats : {json_path.with_suffix('')}.{{json,csv,md}}")
    return 130 if interrupted else 0


if __name__ == "__main__":
    raise SystemExit(main())
