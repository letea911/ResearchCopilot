import pytest
from config.loader import load_config
from config.model import LLMConfig, EmbeddingConfig, ChunkConfig, StorageConfig


@pytest.mark.asyncio
async def test_load_config_defaults():
    """load_config should return config objects with values from .env or defaults."""
    llm, embedding, chunk, storage = load_config()

    assert isinstance(llm, LLMConfig)
    assert isinstance(embedding, EmbeddingConfig)
    assert isinstance(chunk, ChunkConfig)
    assert isinstance(storage, StorageConfig)

    assert chunk.chunk_size == 1024
    assert chunk.chunk_overlap == 128
    assert embedding.dimension == 1536


@pytest.mark.asyncio
async def test_load_config_reads_env(monkeypatch):
    """load_config should read values from environment variables."""
    monkeypatch.setenv("LLM_PROVIDER", "test_provider")
    monkeypatch.setenv("LLM_MODEL", "test_model")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "test_emb")
    monkeypatch.setenv("CHROMA_PERSIST_DIR", "./test_chroma")
    monkeypatch.setenv("SQLITE_PATH", "./test.db")

    llm, embedding, chunk, storage = load_config()

    assert llm.provider == "test_provider"
    assert llm.model == "test_model"
    assert embedding.provider == "test_emb"
    assert storage.chroma_persist_dir == "./test_chroma"
    assert storage.sqlite_path == "./test.db"
