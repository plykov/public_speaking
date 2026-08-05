"""PDF slide deck handling (§4.2 — "Slide/PDF upload with timing and
slide-linked transcript").

Pure functions over PDF bytes: page count and per-page PNG thumbnail
rendering, via PyMuPDF (`fitz`). No LLM/vendor call, no network — this is
the deterministic, no-model-opinion pattern already used by `metrics/`.

**License note, stated rather than hidden**: PyMuPDF's open-source
distribution is AGPL-3.0. That's fine for demonstrating this scope item,
but a real deployment shipping closed-source code alongside it would need
either Artifex's commercial license or a swap to a permissively-licensed
renderer (e.g. shelling out to Poppler's `pdftoppm`, BSD-ish/GPL depending
on build) — a vendor-swap decision, not an architecture change, since
everything downstream only depends on this module's two function
signatures.
"""

from __future__ import annotations

import fitz  # PyMuPDF


class InvalidPdfError(ValueError):
    """The uploaded bytes aren't a PDF PyMuPDF can open."""


def slide_deck_key(session_id: str) -> str:
    return f"{session_id}/slides.pdf"


def slide_thumbnail_key(session_id: str, page_index: int) -> str:
    return f"{session_id}/slides/page-{page_index}.png"


def count_pages(pdf_bytes: bytes) -> int:
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            return doc.page_count
    except Exception as exc:  # PyMuPDF raises its own RuntimeError/ValueError variants
        raise InvalidPdfError(str(exc)) from exc


def render_thumbnails(pdf_bytes: bytes, max_dimension_px: int = 640) -> list[bytes]:
    """Render every page to a PNG, scaled so its longer side is
    `max_dimension_px` — these are thumbnails for a slide-linked
    transcript view, not print-quality export."""
    thumbnails: list[bytes] = []
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page in doc:
                rect = page.rect
                longer_side = max(rect.width, rect.height) or 1.0
                scale = max_dimension_px / longer_side
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale))
                thumbnails.append(pix.tobytes("png"))
    except Exception as exc:
        raise InvalidPdfError(str(exc)) from exc
    return thumbnails
