from ingestion.models import ParsedDocument, ChunkText, ChunkedDocument


def test_parsed_document_defaults():
    doc = ParsedDocument(source_path="/tmp/test.pdf", content="Hello world", source_type="pdf")
    assert doc.raw_metadata == {}
    assert doc.source_type == "pdf"


def test_parsed_document_with_metadata():
    doc = ParsedDocument(
        source_path="/tmp/test.pdf",
        content="Content",
        source_type="pdf",
        raw_metadata={"title": "Test Paper", "year": 2024},
    )
    assert doc.raw_metadata["title"] == "Test Paper"


def test_chunk_text_with_positions():
    chunk = ChunkText(
        document_id=None,
        chunk_id="c-0",
        chunk_index=0,
        text="Introduction paragraph.",
        page_number=1,
        start_offset=0,
        end_offset=100,
    )
    assert chunk.page_number == 1
    assert chunk.start_offset == 0


def test_chunk_text_minimal():
    chunk = ChunkText(document_id="doc-1", chunk_id="c-0", chunk_index=0, text="Minimal.")
    assert chunk.page_number is None
    assert chunk.start_offset is None


def test_chunked_document():
    chunks = [
        ChunkText(document_id="doc-1", chunk_id="c-0", chunk_index=0, text="First."),
        ChunkText(document_id="doc-1", chunk_id="c-1", chunk_index=1, text="Second."),
    ]
    doc = ChunkedDocument(source_path="/tmp/test.pdf", chunks=chunks)
    assert len(doc.chunks) == 2
    assert doc.chunks[0].chunk_index == 0
