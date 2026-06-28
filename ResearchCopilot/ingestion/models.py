from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ParsedDocument:
    """Parser output — raw text + source info."""
    source_path: str
    content: str
    source_type: str              # "pdf" | "bibtex" | "markdown"
    raw_metadata: dict = field(default_factory=dict)


@dataclass
class ChunkText:
    """Single text chunk with position info for traceability."""
    document_id: str | None       # may not be assigned yet
    chunk_id: str
    chunk_index: int
    text: str
    page_number: int | None = None
    start_offset: int | None = None
    end_offset: int | None = None


@dataclass
class ChunkedDocument:
    """Chunker output."""
    source_path: str
    chunks: list[ChunkText]
    raw_metadata: dict = field(default_factory=dict)
