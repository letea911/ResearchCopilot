import pytest
from unittest.mock import AsyncMock, patch
from config.model import EmbeddingConfig
from providers.embedding.openai import OpenAIEmbeddingProvider


@pytest.fixture(autouse=True)
def _set_api_key(monkeypatch):
    """Ensure EMBEDDING_API_KEY is set for all tests."""
    monkeypatch.setenv("EMBEDDING_API_KEY", "test-key")


@pytest.fixture
def emb_config():
    return EmbeddingConfig(
        provider="openai",
        model="text-embedding-3-small",
        dimension=1536,
    )


@pytest.mark.asyncio
async def test_embed_returns_correct_shape(emb_config):
    mock_embeddings = [
        AsyncMock(embedding=[0.1] * 1536),
        AsyncMock(embedding=[0.2] * 1536),
    ]
    mock_response = AsyncMock(data=mock_embeddings)

    with patch("openai.resources.embeddings.AsyncEmbeddings.create", return_value=mock_response):
        provider = OpenAIEmbeddingProvider(emb_config)
        result = await provider.embed(["text one", "text two"])

    assert len(result) == 2
    assert len(result[0]) == 1536
    assert len(result[1]) == 1536


@pytest.mark.asyncio
async def test_embed_single_text(emb_config):
    mock_response = AsyncMock(data=[AsyncMock(embedding=[0.5] * 1536)])

    with patch("openai.resources.embeddings.AsyncEmbeddings.create", return_value=mock_response):
        provider = OpenAIEmbeddingProvider(emb_config)
        result = await provider.embed(["hello"])

    assert len(result) == 1
    assert result[0] == [0.5] * 1536


@pytest.mark.asyncio
async def test_embed_empty_list(emb_config):
    provider = OpenAIEmbeddingProvider(emb_config)
    result = await provider.embed([])
    assert result == []
