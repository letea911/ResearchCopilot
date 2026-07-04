import pytest
from config.model import EmbeddingConfig
from providers.embedding.local import LocalEmbeddingProvider


@pytest.fixture
def config():
    return EmbeddingConfig(
        provider="local",
        model="BAAI/bge-small-en-v1.5",
        dimension=384,
    )


@pytest.mark.asyncio
async def test_embed_returns_correct_shape(config):
    provider = LocalEmbeddingProvider(config)
    result = await provider.embed(["Hello world", "Another text"])
    assert len(result) == 2
    assert len(result[0]) == 384
    assert len(result[1]) == 384


@pytest.mark.asyncio
async def test_embed_single_text(config):
    provider = LocalEmbeddingProvider(config)
    result = await provider.embed(["single text"])
    assert len(result) == 1
    assert len(result[0]) == 384


@pytest.mark.asyncio
async def test_embed_empty_list(config):
    provider = LocalEmbeddingProvider(config)
    result = await provider.embed([])
    assert result == []
