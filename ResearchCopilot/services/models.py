from dataclasses import dataclass, field
from retrieval.models import RetrievedChunk


@dataclass
class Citation:
    """A reference to a cited source."""
    document_id: str
    title: str
    authors: str = ""
    year: int | None = None
    journal: str | None = None
    chunk_id: str | None = None
    snippet: str | None = None
    page_number: int | None = None
    file_path: str | None = None  # absolute path to PDF for file:// link


@dataclass
class ServiceResponse:
    """Unified chat/summarize response."""
    answer: str
    citations: list[Citation] = field(default_factory=list)
    sources: list[RetrievedChunk] = field(default_factory=list)


@dataclass
class SearchResponse:
    """Pure search response — no LLM involved."""
    query: str
    results: list[RetrievedChunk] = field(default_factory=list)
    total_hits: int = 0
