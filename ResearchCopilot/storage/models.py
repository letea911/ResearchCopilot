from dataclasses import dataclass, field


@dataclass
class DocumentRecord:
    """Universal document metadata — shared across literature, experiment, dft, note."""
    id: str
    document_type: str             # "literature" | "experiment" | "dft" | "note"
    title: str
    authors: str | None = None
    year: int | None = None
    journal: str | None = None
    doi: str | None = None
    keywords: str | None = None
    abstract: str | None = None
    source_type: str = "pdf"       # "pdf" | "bibtex" | "doi" | "markdown"
    file_path: str | None = None
    extra: dict | None = None      # domain-specific extension field
    created_at: str = ""


@dataclass
class ChunkRecord:
    """A text chunk linked to a document and a ChromaDB vector."""
    id: str
    document_id: str
    chunk_index: int
    content: str
    chroma_id: str
    token_count: int = 0
    page_number: int | None = None
    start_offset: int | None = None
    end_offset: int | None = None


@dataclass
class VectorDocument:
    """A document ready for insertion into the vector store."""
    id: str
    embedding: list[float]
    content: str
    metadata: dict = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """A single hit from the vector store."""
    id: str
    content: str
    metadata: dict
    score: float
