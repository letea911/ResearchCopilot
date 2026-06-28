from retrieval.models import RetrievedChunk


def test_retrieved_chunk_defaults():
    chunk = RetrievedChunk(
        chunk_id="c-1",
        content="Some content.",
        document_id="doc-1",
        score=0.85,
    )
    assert chunk.chunk_id == "c-1"
    assert chunk.score == 0.85
    assert chunk.metadata == {}


def test_retrieved_chunk_with_metadata():
    chunk = RetrievedChunk(
        chunk_id="c-1",
        content="Content.",
        document_id="doc-1",
        score=0.92,
        metadata={"title": "Test Paper", "year": 2024},
    )
    assert chunk.metadata["title"] == "Test Paper"
