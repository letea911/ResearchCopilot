from abc import ABC, abstractmethod
from retrieval.models import RetrievedChunk


class BaseKeywordRetriever(ABC):
    """Keyword-based retrieval — SQLite FTS5 by default."""

    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int = 10,
        document_type: str | None = None,
        collections: list[str] | None = None,
    ) -> list[RetrievedChunk]:
        """Search by keyword query. Returns chunks with metadata."""
        ...


class BaseVectorRetriever(ABC):
    """Vector similarity retrieval — ChromaDB by default."""

    @abstractmethod
    async def search(
        self,
        embedding: list[float],
        top_k: int = 10,
        where: dict | None = None,
    ) -> list[RetrievedChunk]:
        """Search by embedding vector. Returns chunks with metadata."""
        ...


class BaseHybridRetriever(ABC):
    """Hybrid retrieval — fuses keyword + vector results."""

    @abstractmethod
    async def search(
        self,
        query: str,
        embedding: list[float],
        top_k: int = 10,
        document_type: str | None = None,
        collections: list[str] | None = None,
        keyword_weight: float = 0.3,
        vector_weight: float = 0.7,
    ) -> list[RetrievedChunk]:
        """Search by both keyword and vector, fuse results."""
        ...
