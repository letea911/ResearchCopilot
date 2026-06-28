import pytest
from ingestion.models import ChunkedDocument, ChunkText
from ingestion.metadata import RuleBasedMetadataExtractor


@pytest.fixture
def extractor():
    return RuleBasedMetadataExtractor()


@pytest.mark.asyncio
async def test_extract_from_raw_metadata(extractor):
    chunked = ChunkedDocument(
        source_path="/papers/Smith_2024_DFT.pdf",
        chunks=[
            ChunkText(document_id=None, chunk_id="c-0", chunk_index=0,
                       text="A Novel DFT Study of TiO2\n\nIntroduction..."),
        ],
        raw_metadata={
            "title": "A Novel DFT Study of TiO2",
            "author": "Smith J, Wang L",
            "year": "2024",
            "doi": "10.1000/test.123",
        },
    )
    doc = await extractor.extract(chunked)
    assert doc.title == "A Novel DFT Study of TiO2"
    assert doc.authors == "Smith J, Wang L"
    assert doc.year == 2024
    assert doc.doi == "10.1000/test.123"
    assert doc.document_type == "literature"


@pytest.mark.asyncio
async def test_extract_from_filename(extractor):
    chunked = ChunkedDocument(
        source_path="/papers/Smith_2023_Catalysis.pdf",
        chunks=[],
        raw_metadata={},
    )
    doc = await extractor.extract(chunked)
    assert "Smith" in doc.title
    assert doc.year == 2023


@pytest.mark.asyncio
async def test_extract_fallback_to_first_line(extractor):
    chunked = ChunkedDocument(
        source_path="/papers/paper.pdf",
        chunks=[
            ChunkText(document_id=None, chunk_id="c-0", chunk_index=0,
                       text="Enhanced Oxygen Reduction on Perovskite Oxides\n\nAbstract..."),
        ],
        raw_metadata={},
    )
    doc = await extractor.extract(chunked)
    assert "Enhanced Oxygen Reduction" in doc.title
