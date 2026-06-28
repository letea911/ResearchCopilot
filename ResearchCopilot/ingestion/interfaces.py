from abc import ABC, abstractmethod
from pathlib import Path
from ingestion.models import ParsedDocument, ChunkedDocument
from storage.models import DocumentRecord


class BaseParser(ABC):
    """Convert a file into ParsedDocument."""

    @abstractmethod
    async def parse(self, source: Path) -> ParsedDocument:
        """Parse a file and return extracted text + metadata."""
        ...

    @abstractmethod
    def supports(self, source: Path) -> bool:
        """Check if this parser handles the given file."""
        ...


class BaseNormalizer(ABC):
    """Normalize raw text — whitespace, line breaks, unicode."""

    @abstractmethod
    def normalize(self, text: str) -> str:
        """Clean and normalize text. Idempotent."""
        ...


class BaseChunker(ABC):
    """Split ParsedDocument into ChunkedDocument."""

    @abstractmethod
    def chunk(self, parsed: ParsedDocument) -> ChunkedDocument:
        """Split text respecting section/paragraph boundaries."""
        ...


class BaseMetadataExtractor(ABC):
    """Extract DocumentRecord from chunked content."""

    @abstractmethod
    async def extract(self, chunked: ChunkedDocument) -> DocumentRecord:
        """Extract metadata (title, authors, year, etc.) from chunked doc."""
        ...
