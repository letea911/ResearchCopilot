import pytest
from unittest.mock import AsyncMock
from ingestion.models import ChunkedDocument, ChunkText
from ingestion.metadata import LLMMetadataExtractor


@pytest.fixture
def mock_llm():
    m = AsyncMock()
    m.chat.return_value = '{"title": "Test Paper", "authors": "Smith J, Wang L", "year": 2024, "journal": "Nature Materials"}'
    return m


@pytest.fixture
def chunked_doc():
    # Garbled/sparse header: rule-based extraction yields empty authors and
    # journal (the real PyMuPDF scenario), so the LLM fallback is exercised.
    return ChunkedDocument(
        source_path="/papers/test.pdf",
        chunks=[
            ChunkText(document_id=None, chunk_id="c-0", chunk_index=0,
                       text="Test Paper\n\nAbstract\n\nThis work reports a study that regex cannot parse for authors."),
        ],
        raw_metadata={},
    )


@pytest.mark.asyncio
async def test_llm_fills_missing_authors_and_journal(mock_llm, chunked_doc):
    extractor = LLMMetadataExtractor(mock_llm)
    doc = await extractor.extract(chunked_doc)
    assert doc.authors == "Smith J, Wang L"
    assert doc.journal == "Nature Materials"
    assert doc.year == 2024


@pytest.mark.asyncio
async def test_rule_based_works_without_llm(chunked_doc):
    """Without LLM provider, should still work (rule-based only)."""
    extractor = LLMMetadataExtractor()  # no LLM
    doc = await extractor.extract(chunked_doc)
    assert doc.title is not None  # at least title from first line


@pytest.mark.asyncio
async def test_llm_handles_json_wrapped_in_markdown(mock_llm, chunked_doc):
    mock_llm.chat.return_value = '```json\n{"title": "T", "authors": "A B", "year": 2023, "journal": "J"}\n```'
    extractor = LLMMetadataExtractor(mock_llm)
    doc = await extractor.extract(chunked_doc)
    assert doc.authors == "A B"
    assert doc.journal == "J"
