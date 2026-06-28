import pytest
import tempfile
from pathlib import Path
from ingestion.parsers.pdf import PyMuPDFParser


@pytest.fixture
def parser():
    return PyMuPDFParser()


def test_supports_pdf(parser):
    assert parser.supports(Path("test.pdf")) is True
    assert parser.supports(Path("test.PDF")) is True
    assert parser.supports(Path("test.txt")) is False
    assert parser.supports(Path("test.docx")) is False


@pytest.mark.asyncio
async def test_parse_empty_pdf(parser):
    """Parse a minimal valid PDF."""
    import fitz
    # Create a minimal PDF with fitz
    doc = fitz.open()
    doc.new_page()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_path = f.name
    doc.save(tmp_path)
    doc.close()

    try:
        result = await parser.parse(Path(tmp_path))
        assert result.source_type == "pdf"
        assert result.source_path == tmp_path
        assert isinstance(result.content, str)
        assert result.raw_metadata["page_count"] == 1
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_parse_pdf_with_text(parser):
    """Parse a PDF that contains actual text."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello from PyMuPDF!")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_path = f.name
    doc.save(tmp_path)
    doc.close()

    try:
        result = await parser.parse(Path(tmp_path))
        assert "Hello from PyMuPDF" in result.content
        assert result.source_type == "pdf"
        assert result.raw_metadata["page_count"] == 1
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_parse_multi_page_pdf(parser):
    """Parse a multi-page PDF."""
    import fitz
    doc = fitz.open()
    for i in range(3):
        page = doc.new_page()
        page.insert_text((72, 72), f"Page {i+1}")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_path = f.name
    doc.save(tmp_path)
    doc.close()

    try:
        result = await parser.parse(Path(tmp_path))
        assert result.raw_metadata["page_count"] == 3
        assert "Page 1" in result.content
        assert "Page 2" in result.content
        assert "Page 3" in result.content
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_parse_nonexistent_file(parser):
    """Parsing a nonexistent file should raise an error."""
    with pytest.raises(Exception):
        await parser.parse(Path("/nonexistent/path/file.pdf"))
