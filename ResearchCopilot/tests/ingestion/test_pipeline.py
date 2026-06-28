import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from ingestion.pipeline import IngestionPipeline
from ingestion.parsers.pdf import PyMuPDFParser
from ingestion.normalizer import TextNormalizer
from ingestion.chunker import ScientificChunker
from ingestion.metadata import RuleBasedMetadataExtractor


@pytest.fixture
def mock_embedder():
    m = AsyncMock()
    m.embed.return_value = [[0.1] * 3]
    return m


@pytest.fixture
def mock_file_store():
    m = MagicMock()
    m.save.return_value = "papers/test.pdf"
    return m


@pytest.fixture
def mock_meta_store():
    m = AsyncMock()
    m.get_document_by_doi.return_value = None  # no existing doc
    return m


@pytest.fixture
def mock_vector_store():
    return AsyncMock()


@pytest.fixture
def pipeline(mock_embedder, mock_file_store, mock_meta_store, mock_vector_store):
    return IngestionPipeline(
        parsers={".pdf": PyMuPDFParser()},
        normalizer=TextNormalizer(),
        chunker=ScientificChunker(),
        metadata_extractor=RuleBasedMetadataExtractor(),
        embedder=mock_embedder,
        file_store=mock_file_store,
        meta_store=mock_meta_store,
        vector_store=mock_vector_store,
    )


@pytest.mark.asyncio
async def test_ingest_returns_document_id(pipeline):
    """Ingest a PDF and get back a document_id."""
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Test content for ingestion pipeline.")
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_path = f.name
    doc.save(tmp_path)
    doc.close()

    try:
        doc_id = await pipeline.ingest(Path(tmp_path))
        assert doc_id is not None
        assert isinstance(doc_id, str)
        assert len(doc_id) > 0
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_ingest_idempotent(pipeline, mock_meta_store):
    """Second ingest of same file should return existing doc_id."""
    import fitz
    doc = fitz.open()
    doc.new_page()
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        tmp_path = f.name
    doc.save(tmp_path)
    doc.close()

    try:
        # First ingest
        doc_id1 = await pipeline.ingest(Path(tmp_path))
        # Mock the second call: simulate existing doc
        existing_doc = MagicMock()
        existing_doc.id = doc_id1
        mock_meta_store.get_document_by_doi.return_value = existing_doc
        # Second ingest should return same id
        doc_id2 = await pipeline.ingest(Path(tmp_path))
        assert doc_id1 == doc_id2
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_ingest_no_parser_for_unknown_type(pipeline):
    """Unsupported file type should raise error."""
    with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
        f.write(b"not a real file")
        tmp_path = f.name
    try:
        with pytest.raises(ValueError, match="No parser found"):
            await pipeline.ingest(Path(tmp_path))
    finally:
        Path(tmp_path).unlink(missing_ok=True)
