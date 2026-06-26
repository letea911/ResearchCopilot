from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    provider: str
    model: str
    base_url: str | None = None
    temperature: float = 0.1
    max_tokens: int = 4096


@dataclass
class EmbeddingConfig:
    provider: str
    model: str
    base_url: str | None = None
    dimension: int = 1536


@dataclass
class ChunkConfig:
    chunk_size: int = 1024
    chunk_overlap: int = 128


@dataclass
class StorageConfig:
    chroma_persist_dir: str = "./data/chroma"
    sqlite_path: str = "./data/research_copilot.db"
    file_store_root: str = "./data"
