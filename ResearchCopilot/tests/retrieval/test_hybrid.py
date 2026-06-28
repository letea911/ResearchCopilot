import pytest
from unittest.mock import AsyncMock
from retrieval.models import RetrievedChunk
from retrieval.hybrid import WeightedHybridRetriever


@pytest.fixture
def mock_keyword():
    m = AsyncMock()
    m.search.return_value = [
        RetrievedChunk(chunk_id="k-1", content="TiO2 band gap 3.2 eV",
                       document_id="doc-1", score=1.0,
                       metadata={"title": "DFT Study", "document_type": "literature"}),
    ]
    return m


@pytest.fixture
def mock_vector():
    m = AsyncMock()
    m.search.return_value = [
        RetrievedChunk(chunk_id="v-1", content="TiO2 anatase band gap",
                       document_id="doc-2", score=0.9,
                       metadata={"title": "Another Study", "document_type": "literature"}),
        RetrievedChunk(chunk_id="k-1", content="TiO2 band gap 3.2 eV",
                       document_id="doc-1", score=0.8,
                       metadata={"title": "DFT Study", "document_type": "literature"}),
    ]
    return m


@pytest.fixture
def retriever(mock_keyword, mock_vector):
    return WeightedHybridRetriever(mock_keyword, mock_vector)


@pytest.mark.asyncio
async def test_hybrid_fuses_results(retriever):
    results = await retriever.search("TiO2 band gap", [0.1] * 3, top_k=3)
    assert len(results) >= 1
    # Results should be deduplicated by chunk_id
    chunk_ids = [r.chunk_id for r in results]
    assert len(chunk_ids) == len(set(chunk_ids))  # no duplicates


@pytest.mark.asyncio
async def test_hybrid_honors_top_k(retriever, mock_keyword, mock_vector):
    # Setup many results
    chunks = [RetrievedChunk(
        chunk_id=f"c-{i}", content=f"text {i}", document_id=f"d-{i}", score=1.0 / (i + 1)
    ) for i in range(20)]
    mock_keyword.search.return_value = chunks[:10]
    mock_vector.search.return_value = chunks[10:]

    results = await retriever.search("query", [0.1], top_k=5)
    assert len(results) == 5


@pytest.mark.asyncio
async def test_hybrid_passes_document_type_to_keyword(retriever, mock_keyword):
    await retriever.search("query", [0.1], document_type="literature")
    mock_keyword.search.assert_called_once_with(
        "query", top_k=20, document_type="literature"
    )


@pytest.mark.asyncio
async def test_hybrid_requests_wider_top_k(retriever, mock_keyword, mock_vector):
    await retriever.search("query", [0.1], top_k=10)
    # Should request top_k * 2 from each sub-retriever for better fusion
    mock_keyword.search.assert_called_once_with("query", top_k=20, document_type=None)
    mock_vector.search.assert_called_once_with([0.1], top_k=20)
