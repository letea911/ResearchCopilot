import os
from dotenv import load_dotenv
from config.model import LLMConfig, EmbeddingConfig, ChunkConfig, StorageConfig


def load_config():
    load_dotenv()

    llm = LLMConfig(
        provider=os.getenv("LLM_PROVIDER", "openai"),
        model=os.getenv("LLM_MODEL", "gpt-4o"),
        base_url=os.getenv("LLM_BASE_URL") or None,
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
    )

    embedding = EmbeddingConfig(
        provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
        model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        base_url=os.getenv("EMBEDDING_BASE_URL") or None,
        dimension=int(os.getenv("EMBEDDING_DIMENSION", "1536")),
    )

    chunk = ChunkConfig(
        chunk_size=int(os.getenv("CHUNK_SIZE", "1024")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "128")),
    )

    storage = StorageConfig(
        chroma_persist_dir=os.getenv("CHROMA_PERSIST_DIR", "./data/chroma"),
        sqlite_path=os.getenv("SQLITE_PATH", "./data/research_copilot.db"),
        file_store_root=os.getenv("FILE_STORE_ROOT", "./data"),
    )

    return llm, embedding, chunk, storage
