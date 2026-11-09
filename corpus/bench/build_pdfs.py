"""Génère les PDF de la fixture de benchmark à partir des sources Markdown.

Usage (depuis la racine du dépôt) :

    pip install reportlab pypdf
    python corpus/bench/build_pdfs.py          # génère les PDF
    python corpus/bench/build_pdfs.py --check  # vérifie sans réécrire

Le script vérifie que chaque PDF fait exactement 6 pages et que le texte de
chaque page est extractible. Le rendu est déterministe (mode `invariant`) :
relancer le script sur les mêmes sources produit des fichiers identiques.

Syntaxe Markdown reconnue (volontairement minimale) :
    # Titre            → titre du contrat
    ### Sous-titre     → sous-titre centré
    ## Article ...     → intitulé d'article
    - élément          → puce
    ligne vide         → séparation de paragraphes
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (
    KeepTogether,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

BENCH_DIR = Path(__file__).resolve().parent
SOURCES_DIR = BENCH_DIR / "sources"
EXPECTED_PAGES = 6
FOOTER = "Document fictif – fixture de benchmark r55-g6"

# Polices standard PDF (Helvetica) : aucune dépendance à un fichier de police,
# encodage WinAnsi qui couvre les caractères français (é, à, ç, œ, «, », €).
BASE = ParagraphStyle(
    "base",
    fontName="Helvetica",
    fontSize=10.5,
    leading=14,
    alignment=TA_JUSTIFY,
    spaceAfter=5,
)
STYLES = {
    "title": ParagraphStyle(
        "title",
        parent=BASE,
        fontName="Helvetica-Bold",
        fontSize=16,
        leading=20,
        alignment=TA_CENTER,
        spaceBefore=12,  # ignoré en haut de page
        spaceAfter=6,
    ),
    "subtitle": ParagraphStyle(
        "subtitle",
        parent=BASE,
        fontName="Helvetica-Oblique",
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        spaceAfter=2,
    ),
    "heading": ParagraphStyle(
        "heading",
        parent=BASE,
        fontName="Helvetica-Bold",
        fontSize=11.5,
        leading=15,
        spaceBefore=8,
        spaceAfter=4,
    ),
    "body": BASE,
    "bullet": ParagraphStyle("bullet", parent=BASE, spaceAfter=2),
}


NBSP = "\u00a0"


def typo(text: str) -> str:
    """Échappe le texte et pose les espaces insécables de la typographie
    française (guillemets, symbole euro, séparateur de milliers), pour éviter
    un « ou un € isolé en début ou fin de ligne."""
    text = text.replace("« ", "«" + NBSP).replace(" »", NBSP + "»")
    text = text.replace(" €", NBSP + "€")
    text = re.sub(r"(?<=\d) (?=\d{3}\b)", NBSP, text)
    return escape(text)


class NumberedCanvas(rl_canvas.Canvas):
    """Canvas qui écrit « Page X / N » en pied de page (deux passes)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_pages: list[dict] = []

    def showPage(self):
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_pages)
        for state in self._saved_pages:
            self.__dict__.update(state)
            self._draw_footer(total)
            super().showPage()
        super().save()

    def _draw_footer(self, total: int) -> None:
        self.setFont("Helvetica", 8)
        self.drawString(2.2 * cm, 1.2 * cm, FOOTER)
        self.drawRightString(
            A4[0] - 2.2 * cm, 1.2 * cm, f"Page {self._pageNumber} / {total}"
        )


def parse(markdown: str) -> tuple[str, list]:
    """Transforme la source en (titre, flowables reportlab)."""
    title = ""
    story: list = []
    bullets: list[str] = []
    paragraph: list[str] = []
    pending_heading: Paragraph | None = None

    def add(flowable) -> None:
        nonlocal pending_heading
        # Un intitulé d'article n'est jamais laissé seul en bas de page.
        if pending_heading is not None:
            story.append(KeepTogether([pending_heading, flowable]))
            pending_heading = None
        else:
            story.append(flowable)

    def flush_paragraph() -> None:
        if paragraph:
            add(Paragraph(typo(" ".join(paragraph)), STYLES["body"]))
            paragraph.clear()

    def flush_bullets() -> None:
        if bullets:
            items = [
                ListItem(Paragraph(typo(b), STYLES["bullet"]), leftIndent=14)
                for b in bullets
            ]
            add(ListFlowable(items, bulletType="bullet", start="–", leftIndent=14))
            bullets.clear()

    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            flush_paragraph()
            flush_bullets()
            continue
        if line.startswith("### "):
            flush_paragraph()
            flush_bullets()
            add(Paragraph(typo(line[4:]), STYLES["subtitle"]))
        elif line.startswith("## "):
            flush_paragraph()
            flush_bullets()
            pending_heading = Paragraph(typo(line[3:]), STYLES["heading"])
        elif line.startswith("# "):
            flush_paragraph()
            flush_bullets()
            title = title or line[2:]  # le premier titre sert de métadonnée
            add(Paragraph(typo(line[2:]), STYLES["title"]))
        elif line.startswith("- "):
            flush_paragraph()
            bullets.append(line[2:])
        else:
            flush_bullets()
            paragraph.append(line)
    flush_paragraph()
    flush_bullets()

    # Espace entre le bloc de titre et la première section.
    first_heading = next(
        (i for i, f in enumerate(story) if isinstance(f, KeepTogether)), None
    )
    if first_heading is not None:
        story.insert(first_heading, Spacer(1, 10))
    return title, story


def render(source: Path) -> bytes:
    title, story = parse(source.read_text(encoding="utf-8"))
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.2 * cm,
        title=title,
        author="r55-g6 – corpus de benchmark",
        subject="Contrat fictif (fixture de benchmark)",
        creator="corpus/bench/build_pdfs.py",
        invariant=1,
    )
    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()


def check(pdf_bytes: bytes, name: str) -> list[str]:
    """Retourne la liste des problèmes détectés (vide si tout va bien)."""
    from pypdf import PdfReader

    problems = []
    reader = PdfReader(io.BytesIO(pdf_bytes))
    if len(reader.pages) != EXPECTED_PAGES:
        problems.append(
            f"{name} : {len(reader.pages)} pages au lieu de {EXPECTED_PAGES}"
        )
    for number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if len(text.split()) < 150:
            problems.append(f"{name} : page {number} quasi vide ({len(text)} car.)")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="vérifie les PDF sans les réécrire (échoue s'ils sont périmés)",
    )
    args = parser.parse_args()

    problems: list[str] = []
    for source in sorted(SOURCES_DIR.glob("*.md")):
        target = BENCH_DIR / f"{source.stem}.pdf"
        pdf_bytes = render(source)
        problems += check(pdf_bytes, target.name)
        if args.check:
            if not target.exists() or target.read_bytes() != pdf_bytes:
                problems.append(f"{target.name} : périmé, relancer le script")
        else:
            target.write_bytes(pdf_bytes)
            print(f"écrit {target.relative_to(BENCH_DIR.parent.parent)}")

    for problem in problems:
        print(f"ERREUR {problem}", file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
