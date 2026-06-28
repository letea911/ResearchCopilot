import pytest
from unittest.mock import AsyncMock
from storage.models import RetrievalResult
from retrieval.vector import ChromaVectorRetriever


@pytest.fixture
def mock_vector_store():
    store = AsyncMock()
    store.query.return_value = [
        RetrievalResult(
            id="chroma-1", content="TiO2 has a band gap of 3.2 eV.",
            metadata={"document_id": "doc-1", "title": "DFT Study",
                       "document_type": "literature", "chunk_index": 0},
            score=0.95,
        ),
    ]
    return store


@pytest.fixture
def mock_meta_store():
    return AsyncMock()


@pytest.fixture
def retriever(mock_vector_store, mock_meta_store):
    return ChromaVectorRetriever(mock_vector_store, mock_meta_store)


@pytest.mark.asyncio
async def test_vector_search_returns_chunks(retriever):
    results = await retriever.search([0.1] * 1536, top_k=5)
    assert len(results) == 1
    assert results[0].chunk_id == "chroma-1"
    assert results[0].score == 0.95
    assert results[0].metadata["title"] == "DFT Study"


@pytest.mark.asyncio
async def test_vector_search_empty(mock_vector_store, mock_meta_store):
    mock_vector_store.query.return_value = []
    r = ChromaVectorRetriever(mock_vector_store, mock_meta_store)
    results = await r.search([0.1] * 10)
    assert results == []


@pytest.mark.asyncio
async def test_vector_search_passes_where_filter(mock_vector_store, mock_meta_store):
    mock_vector_store.query.return_value = []
    r = ChromaVectorRetriever(mock_vector_store, mock_meta_store)
    await r.search([0.1] * 10, where={"document_type": "literature"})
    mock_vector_store.query.assert_called_once_with(
        [0.1] * 10, top_k=10, where={"document_type": "literature"}
    )


@pytest.mark.asyncio
async def test_vector_search_metadata_passthrough(mock_vector_store, mock_meta_store):
    mock_vector_store.query.return_value = [
        RetrievalResult(
            id="chroma-2", content="Perovskite solar cells.",
            metadata={"document_id": "doc-2", "title": "CV Analysis",
                       "document_type": "experiment", "chunk_index": 1,
                       "extra_field": "should pass through"},
            score=0.87,
        ),
    ]
    r = ChromaVectorRetriever(mock_vector_store, mock_meta_store)
    results = await r.search([0.1] * 10)
    assert len(results) == 1
    assert results[0].metadata["extra_field"] == "should pass through"
    # document_id should NOT appear in metadata (it's promoted to the top-level field)
    assert "document_id" not in results[0].metadata
