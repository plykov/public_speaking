from __future__ import annotations

import fitz
import pytest

from api.slides import InvalidPdfError, count_pages, render_thumbnails, slide_deck_key, slide_thumbnail_key


def _make_pdf(n_pages: int) -> bytes:
    doc = fitz.open()
    for i in range(n_pages):
        page = doc.new_page(width=300, height=200)
        page.insert_text((20, 100), f"Slide {i + 1}")
    return doc.tobytes()


def test_count_pages() -> None:
    assert count_pages(_make_pdf(3)) == 3


def test_count_pages_single_page() -> None:
    assert count_pages(_make_pdf(1)) == 1


def test_render_thumbnails_returns_one_png_per_page() -> None:
    thumbnails = render_thumbnails(_make_pdf(3))
    assert len(thumbnails) == 3
    for png_bytes in thumbnails:
        assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic number


def test_render_thumbnails_scales_to_max_dimension() -> None:
    thumbnails = render_thumbnails(_make_pdf(1), max_dimension_px=100)
    with fitz.open(stream=thumbnails[0], filetype="png") as doc:
        page = doc[0]
        assert max(page.rect.width, page.rect.height) <= 101  # rounding tolerance


def test_count_pages_rejects_garbage_bytes() -> None:
    with pytest.raises(InvalidPdfError):
        count_pages(b"this is not a pdf")


def test_render_thumbnails_rejects_garbage_bytes() -> None:
    with pytest.raises(InvalidPdfError):
        render_thumbnails(b"this is not a pdf")


def test_slide_deck_key_is_scoped_per_session() -> None:
    assert slide_deck_key("abc") != slide_deck_key("def")


def test_slide_thumbnail_key_is_scoped_per_session_and_page() -> None:
    assert slide_thumbnail_key("abc", 0) != slide_thumbnail_key("abc", 1)
    assert slide_thumbnail_key("abc", 0) != slide_thumbnail_key("def", 0)
