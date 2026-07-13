from abc import ABC, abstractmethod
from pathlib import Path
from storage.models import DocumentRecord, ChunkRecord, VectorDocument, RetrievalResult


class BaseFileStore(ABC):
    """Raw file storage — save, retrieve, list, delete by category."""

    @abstractmethod
    def save(self, source: Path, category: str) -> str:
        """Copy file into file_store/<category>/, return relative path."""
        ...

    @abstractmethod
    def get_path(self, relative_path: str) -> Path:
        """Resolve a relative path to an absolute path."""
        ...

    @abstractmethod
    def list(self, category: str) -> list[str]:
        """List all file paths under a category."""
        ...

    @abstractmethod
    def delete(self, relative_path: str) -> None:
        """Delete a file from the store."""
        ...


class BaseMetadataStore(ABC):
    """Document and chunk metadata storage — SQLite-backed."""

    @abstractmethod
    async def insert_document(self, doc: DocumentRecord) -> None:
        """Insert a new document record."""
        ...

    @abstractmethod
    async def get_document(self, document_id: str) -> DocumentRecord | None:
        """Retrieve a document by ID."""
        ...

    @abstractmethod
    async def get_document_by_doi(self, doi: str) -> DocumentRecord | None:
        """Find a document by DOI."""
        ...

    @abstractmethod
    async def list_documents(
        self,
        document_type: str | None = None,
        year: int | None = None,
        limit: int = 50,
    ) -> list[DocumentRecord]:
        """List documents with optional filters."""
        ...

    @abstractmethod
    async def insert_chunks(self, chunks: list[ChunkRecord]) -> None:
        """Insert chunk records in batch."""
        ...

    @abstractmethod
    async def get_chunks_by_document(self, document_id: str) -> list[ChunkRecord]:
        """Get all chunks for a document, ordered by chunk_index."""
        ...

    @abstractmethod
    async def get_chunk_by_chroma_id(self, chroma_id: str) -> ChunkRecord | None:
        """Find a chunk by its ChromaDB vector ID."""
        ...

    @abstractmethod
    async def update_document_metadata(
        self, document_id: str,
        authors: str | None = None,
        year: int | None = None,
        journal: str | None = None,
        doi: str | None = None,
    ) -> None:
        """Update only the provided (non-None) metadata fields of a document."""
        ...


class BaseVectorStore(ABC):
    """Vector storage and similarity search — ChromaDB-backed."""

    @abstractmethod
    async def add(self, docs: list[VectorDocument]) -> None:
        """Add documents with embeddings to the vector store."""
        ...

    @abstractmethod
    async def query(
        self,
        embedding: list[float],
        top_k: int = 10,
        where: dict | None = None,
    ) -> list[RetrievalResult]:
        """Query by embedding vector with optional metadata filter."""
        ...

    @abstractmethod
    async def delete(self, ids: list[str]) -> None:
        """Delete vectors by ID."""
        ...

    @abstractmethod
    async def count(self) -> int:
        """Return the total number of vectors in the store."""
        ...
