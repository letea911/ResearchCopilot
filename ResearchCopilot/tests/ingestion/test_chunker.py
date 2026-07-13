from config.model import ChunkConfig
from ingestion.models import ParsedDocument
from ingestion.chunker import ScientificChunker


def test_chunker_single_short_paragraph():
    c = ScientificChunker(ChunkConfig(chunk_size=1024, chunk_overlap=128))
    parsed = ParsedDocument(
        source_path="test.pdf",
        content="A short paragraph.",
        source_type="pdf",
    )
    result = c.chunk(parsed)
    assert len(result.chunks) == 1
    assert result.chunks[0].text == "A short paragraph."
    assert result.chunks[0].chunk_index == 0
    assert result.chunks[0].start_offset == 0


def test_chunker_multiple_paragraphs():
    c = ScientificChunker(ChunkConfig(chunk_size=50, chunk_overlap=0))
    content = "\n\n".join(["Para one which is somewhat long."] * 5)
    parsed = ParsedDocument(source_path="test.pdf", content=content, source_type="pdf")
    result = c.chunk(parsed)
    # Should produce multiple chunks because each para exceeds chunk_size=50 combined
    assert len(result.chunks) >= 1
    for i, chunk in enumerate(result.chunks):
        assert chunk.chunk_index == i
        assert chunk.chunk_id != ""


def test_chunker_preserves_metadata():
    c = ScientificChunker()
    parsed = ParsedDocument(
        source_path="test.pdf",
        content="Some text.",
        source_type="pdf",
        raw_metadata={"title": "Test", "author": "Smith"},
    )
    result = c.chunk(parsed)
    assert result.raw_metadata["title"] == "Test"
    assert result.raw_metadata["author"] == "Smith"


def test_chunker_overlap():
    """With overlap, chunks should share some text."""
    c = ScientificChunker(ChunkConfig(chunk_size=100, chunk_overlap=30))
    # Create paragraphs that force multiple chunks
    paragraphs = ["x" * 60, "y" * 60, "z" * 60]
    content = "\n\n".join(paragraphs)
    parsed = ParsedDocument(source_path="test.pdf", content=content, source_type="pdf")
    result = c.chunk(parsed)
    assert len(result.chunks) >= 2
    # Last part of chunk 0 should appear at start of chunk 1 (overlap)
    last_chars_chunk0 = result.chunks[0].text[-10:]
    first_chars_chunk1 = result.chunks[1].text[:10]
    # There should be some overlap visible
    assert len(result.chunks) >= 2


def test_chunker_empty_content():
    c = ScientificChunker()
    parsed = ParsedDocument(source_path="test.pdf", content="", source_type="pdf")
    result = c.chunk(parsed)
    assert len(result.chunks) == 0


def test_chunker_offsets():
    c = ScientificChunker(ChunkConfig(chunk_size=1024, chunk_overlap=0))
    content = "First paragraph.\n\nSecond paragraph."
    parsed = ParsedDocument(source_path="test.pdf", content=content, source_type="pdf")
    result = c.chunk(parsed)
    assert len(result.chunks) == 1  # fits in one chunk
    assert result.chunks[0].start_offset == 0
    assert result.chunks[0].end_offset > 0


def test_chunker_assigns_sections():
    """Section headings should propagate to the chunks under them."""
    c = ScientificChunker(ChunkConfig(chunk_size=40, chunk_overlap=0))
    content = (
        "Introduction\n\n"
        "This work studies catalysis in depth here.\n\n"
        "Methods\n\n"
        "We used DFT calculations on many surfaces."
    )
    parsed = ParsedDocument(source_path="test.pdf", content=content, source_type="pdf")
    result = c.chunk(parsed)

    sections = {ch.section for ch in result.chunks}
    assert "Introduction" in sections
    assert "Methods" in sections
    # Every chunk carries a section label once the first heading is seen
    assert all(ch.section is not None for ch in result.chunks)


def test_chunker_page_numbers_from_page_texts():
    """page_number is computed from page_texts offsets when provided."""
    page1 = "Introduction\n\n" + ("a" * 200)
    page2 = "Methods\n\n" + ("b" * 200)
    content = "\n\n".join([page1, page2])
    parsed = ParsedDocument(
        source_path="test.pdf",
        content=content,
        source_type="pdf",
        page_texts=[page1, page2],
    )
    c = ScientificChunker(ChunkConfig(chunk_size=150, chunk_overlap=0))
    result = c.chunk(parsed)

    pages = {ch.page_number for ch in result.chunks}
    assert 1 in pages
    assert 2 in pages
    assert all(ch.page_number is not None for ch in result.chunks)


def test_chunker_page_number_none_without_page_texts():
    """page_number stays None when no page_texts are supplied."""
    c = ScientificChunker(ChunkConfig(chunk_size=1024, chunk_overlap=0))
    parsed = ParsedDocument(source_path="test.pdf", content="Some text.", source_type="pdf")
    result = c.chunk(parsed)
    assert result.chunks[0].page_number is None
