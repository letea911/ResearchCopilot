import pytest
from unittest.mock import AsyncMock
from services.search import SearchService
from services.models import SearchResponse
from retrieval.models import RetrievedChunk


@pytest.fixture
def svc():
    embedder = AsyncMock()
    embedder.embed.return_value = [[0.1] * 3]
    retriever = AsyncMock()
    retriever.search.return_value = [
        RetrievedChunk(chunk_id="c-1", content="Result 1", document_id="d1", score=0.9),
    ]
    return SearchService(embedder, retriever)


@pytest.mark.asyncio
async def test_search_returns_response(svc):
    result = await svc.search("TiO2")
    assert isinstance(result, SearchResponse)
    assert result.query == "TiO2"
    assert result.total_hits == 1
    assert result.results[0].content == "Result 1"
