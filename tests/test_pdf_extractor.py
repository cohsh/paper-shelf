import os
import tempfile

import pymupdf
import pytest

from src.exceptions import PDFExtractionError
from src.pdf_extractor import ExtractedPaper, extract


@pytest.fixture
def sample_pdf():
    """Create a simple test PDF with known content."""
    doc = pymupdf.open()
    page = doc.new_page()
    text = "Test Paper Title\n\nThis is a test paper with some content.\nIt has multiple lines of text for testing purposes."
    page.insert_text((72, 72), text, fontsize=12)

    page2 = doc.new_page()
    page2.insert_text((72, 72), "Page 2 content here.", fontsize=12)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        doc.save(f.name)
        doc.close()
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def empty_pdf():
    """Create an empty PDF (no text content)."""
    doc = pymupdf.open()
    doc.new_page()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        doc.save(f.name)
        doc.close()
        yield f.name
    os.unlink(f.name)


def test_extract_success(sample_pdf):
    result = extract(sample_pdf)
    assert isinstance(result, ExtractedPaper)
    assert result.page_count == 2
    assert result.char_count > 0
    assert "Test Paper Title" in result.text
    assert "Page 2 content" in result.text
    assert "--- Page 1 ---" in result.text
    assert "--- Page 2 ---" in result.text


def test_extract_metadata(sample_pdf):
    result = extract(sample_pdf)
    assert isinstance(result.metadata, dict)
    assert "title" in result.metadata
    assert "author" in result.metadata


def test_extract_file_not_found():
    with pytest.raises(PDFExtractionError, match="File not found"):
        extract("/nonexistent/path/paper.pdf")


def test_extract_not_pdf():
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        f.write(b"not a pdf")
        f.flush()
        try:
            with pytest.raises(PDFExtractionError, match="Not a PDF"):
                extract(f.name)
        finally:
            os.unlink(f.name)


def test_extract_empty_pdf(empty_pdf):
    with pytest.raises(PDFExtractionError, match="too short"):
        extract(empty_pdf)


def test_extract_source_path(sample_pdf):
    result = extract(sample_pdf)
    assert os.path.isabs(result.source_path)
