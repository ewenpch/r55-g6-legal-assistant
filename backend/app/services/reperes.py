"""Fonctions sans IA : repérage de montants, dates, durées, termes juridiques, et recherche.

Tout est déterministe (expressions régulières et listes de mots-clés) : rien n'est envoyé à un LLM.
"""

import re
from collections.abc import Iterable

import pymupdf

CONTEXT_CHARS = 50
MAX_RESULTS = 50

_MONTHS = (
    "janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|"
    "septembre|octobre|novembre|décembre|decembre"
)
_NUMBER_WORDS = "un|une|deux|trois|quatre|cinq|six|sept|huit|neuf|dix|onze|douze"

PATTERNS: dict[str, re.Pattern[str]] = {
    "montants": re.compile(r"\d[\d   .]*(?:,\d{1,2})?\s?(?:€|euros?\b|EUR\b)", re.IGNORECASE),
    "dates": re.compile(
        rf"\b\d{{1,2}}[/.-]\d{{1,2}}[/.-]\d{{2,4}}\b|\b\d{{1,2}}(?:er)?\s+(?:{_MONTHS})\s+\d{{4}}\b",
        re.IGNORECASE,
    ),
    "durees": re.compile(
        rf"\b(?:\d+|{_NUMBER_WORDS})\s+(?:jours?|semaines?|mois|ans?|années?|annees?)\b",
        re.IGNORECASE,
    ),
}

# Définitions courtes de termes juridiques courants (glossaire fixe, relu à la main).
GLOSSAIRE: dict[str, str] = {
    "préavis": "Délai à respecter avant de mettre fin au contrat.",
    "résiliation": "Fin du contrat décidée par l'une des parties avant son terme.",
    "dépôt de garantie": "Somme versée au début, rendue à la fin sauf dégâts ou impayés.",
    "caution": "Personne qui s'engage à payer à la place du locataire s'il ne paie pas.",
    "tacite reconduction": "Renouvellement automatique du contrat si personne ne s'y oppose.",
    "clause pénale": "Somme à payer automatiquement en cas de manquement au contrat.",
    "période d'essai": "Début du contrat pendant lequel chacun peut l'arrêter plus facilement.",
    "preneur": "Celui qui loue ou prend à bail (le locataire).",
    "bailleur": "Celui qui loue son bien (le propriétaire).",
    "indexation": "Révision du prix selon un indice, par exemple l'IRL pour un loyer.",
    "solidarité": "Chacun des cosignataires peut être tenu de payer la totalité.",
}


def extract_pages(content: bytes) -> list[str]:
    """Texte de chaque page du PDF, dans l'ordre (page 1 = index 0)."""
    with pymupdf.open(stream=content, filetype="pdf") as doc:
        return [page.get_text() for page in doc]


def _context(text: str, start: int, end: int) -> str:
    a = max(0, start - CONTEXT_CHARS)
    b = min(len(text), end + CONTEXT_CHARS)
    snippet = " ".join(text[a:b].split())
    return ("…" if a > 0 else "") + snippet + ("…" if b < len(text) else "")


def _clean(value: str) -> str:
    return " ".join(value.split()).strip(" .")


def find_reperes(pages: Iterable[str]) -> dict[str, list[dict]]:
    """Montants, dates, durées (avec page et contexte) et termes juridiques présents."""
    result: dict[str, list[dict]] = {key: [] for key in PATTERNS}
    seen: set[tuple[str, str, int]] = set()
    terms: dict[str, list[int]] = {}
    for number, text in enumerate(pages, start=1):
        for kind, pattern in PATTERNS.items():
            for match in pattern.finditer(text):
                value = _clean(match.group())
                key = (kind, value.casefold(), number)
                if key in seen:
                    continue
                seen.add(key)
                result[kind].append(
                    {
                        "texte": value,
                        "page": number,
                        "contexte": _context(text, match.start(), match.end()),
                    }
                )
        lowered = " ".join(text.split()).casefold()
        for term in GLOSSAIRE:
            if term in lowered:
                terms.setdefault(term, []).append(number)
    result["termes"] = [
        {"terme": term, "definition": GLOSSAIRE[term], "pages": pages_found}
        for term, pages_found in terms.items()
    ]
    return result


def search(pages: Iterable[str], query: str) -> tuple[int, list[dict]]:
    """Occurrences de `query` (sans tenir compte de la casse) : (total, premiers résultats)."""
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    total = 0
    hits: list[dict] = []
    for number, text in enumerate(pages, start=1):
        for match in pattern.finditer(text):
            total += 1
            if len(hits) < MAX_RESULTS:
                hits.append({"page": number, "extrait": _context(text, match.start(), match.end())})
    return total, hits
