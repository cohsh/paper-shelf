from __future__ import annotations

import os
from dataclasses import dataclass

import pymupdf

from paper_shelf.exceptions import PDFExtractionError


@dataclass
class ExtractedPaper:
    text: str
    metadata: dict
    page_count: int
    source_path: str
    char_count: int


def extract(pdf_path: str) -> ExtractedPaper:
    """Extract text and metadata from a PDF file."""
    if not os.path.exists(pdf_path):
        raise PDFExtractionError(f"File not found: {pdf_path}")

    if not pdf_path.lower().endswith(".pdf"):
        raise PDFExtractionError(f"Not a PDF file: {pdf_path}")

    try:
        doc = pymupdf.open(pdf_path)
    except Exception as e:
        raise PDFExtractionError(f"Failed to open PDF: {e}") from e

    pages = _extract_text_by_page(doc)
    text = "\n".join(pages)
    metadata = _extract_metadata(doc)
    page_count = len(doc)
    doc.close()

    if len(text.strip()) < 100:
        raise PDFExtractionError(
            "Extracted text is too short. The PDF may be scanned/image-based and require OCR."
        )

    return ExtractedPaper(
        text=text,
        metadata=metadata,
        page_count=page_count,
        source_path=os.path.abspath(pdf_path),
        char_count=len(text),
    )


def _extract_text_by_page(doc: pymupdf.Document) -> list[str]:
    """Extract text from each page with page boundary markers."""
    pages = []
    for i, page in enumerate(doc):
        page_text = page.get_text("text")
        pages.append(f"\n--- Page {i + 1} ---\n{page_text}")
    return pages


def _extract_metadata(doc: pymupdf.Document) -> dict:
    """Extract PDF metadata fields."""
    meta = doc.metadata or {}
    return {
        "title": meta.get("title", ""),
        "author": meta.get("author", ""),
        "subject": meta.get("subject", ""),
        "creator": meta.get("creator", ""),
        "creation_date": meta.get("creationDate", ""),
    }
