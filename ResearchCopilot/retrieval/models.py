from dataclasses import dataclass, field


@dataclass
class RetrievedChunk:
    """A single retrieval hit — enriched with document metadata."""
    chunk_id: str
    content: str
    document_id: str
    score: float
    metadata: dict = field(default_factory=dict)  # {title, authors, year, journal, document_type, ...}
