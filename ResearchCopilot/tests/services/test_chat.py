import pytest
from unittest.mock import AsyncMock
from services.chat import ChatService
from services.models import ServiceResponse
from retrieval.models import RetrievedChunk


@pytest.fixture
def mock_llm():
    m = AsyncMock()
    m.chat.return_value = "TiO2 has a band gap of approximately 3.2 eV [1]."
    return m


@pytest.fixture
def mock_embedder():
    m = AsyncMock()
    m.embed.return_value = [[0.1] * 3]
    return m


@pytest.fixture
def mock_retriever():
    m = AsyncMock()
    m.search.return_value = [
        RetrievedChunk(chunk_id="c-1", content="TiO2 anatase band gap is 3.2 eV.",
                       document_id="doc-1", score=0.95,
                       metadata={"title": "DFT Study of TiO2", "authors": "Smith J", "year": 2024}),
    ]
    return m


@pytest.mark.asyncio
async def test_ask_returns_service_response(mock_llm, mock_embedder, mock_retriever):
    svc = ChatService(mock_llm, mock_embedder, mock_retriever)
    result = await svc.ask("What is the band gap of TiO2?")
    assert isinstance(result, ServiceResponse)
    assert "TiO2" in result.answer
    assert len(result.citations) == 1
    assert result.citations[0].title == "DFT Study of TiO2"


@pytest.mark.asyncio
async def test_ask_stream_yields_tokens(mock_llm, mock_embedder, mock_retriever):
    async def _fake_stream(messages):
        for token in ["TiO2", " band", " gap"]:
            yield token

    mock_llm.stream = _fake_stream
    svc = ChatService(mock_llm, mock_embedder, mock_retriever)
    tokens = []
    async for t in svc.ask_stream("What is TiO2?"):
        tokens.append(t)
    assert len(tokens) == 3
    assert "".join(tokens) == "TiO2 band gap"
