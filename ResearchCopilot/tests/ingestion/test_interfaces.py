import pytest
from pathlib import Path
from ingestion.interfaces import BaseParser, BaseNormalizer, BaseChunker, BaseMetadataExtractor
from ingestion.models import ParsedDocument, ChunkedDocument, ChunkText
from storage.models import DocumentRecord


class FakeParser(BaseParser):
    async def parse(self, source: Path) -> ParsedDocument:
        return ParsedDocument(source_path=str(source), content="text", source_type="pdf")
    def supports(self, source: Path) -> bool:
        return source.suffix == ".pdf"


class FakeNormalizer(BaseNormalizer):
    def normalize(self, text: str) -> str:
        return text.lstrip().replace("\r\n", "\n")


class FakeChunker(BaseChunker):
    def chunk(self, parsed: ParsedDocument) -> ChunkedDocument:
        c = ChunkText(document_id=None, chunk_id="c-0", chunk_index=0, text=parsed.content)
        return ChunkedDocument(source_path=parsed.source_path, chunks=[c])


class FakeMetadataExtractor(BaseMetadataExtractor):
    async def extract(self, chunked: ChunkedDocument) -> DocumentRecord:
        return DocumentRecord(id="doc-1", document_type="literature", title="Extracted Title")


def test_parser_is_abstract():
    with pytest.raises(TypeError):
        BaseParser()


def test_normalizer_is_abstract():
    with pytest.raises(TypeError):
        BaseNormalizer()


def test_chunker_is_abstract():
    with pytest.raises(TypeError):
        BaseChunker()


def test_metadata_extractor_is_abstract():
    with pytest.raises(TypeError):
        BaseMetadataExtractor()


def test_fake_parser_supports():
    p = FakeParser()
    assert p.supports(Path("test.pdf")) is True
    assert p.supports(Path("test.txt")) is False


def test_fake_normalizer():
    n = FakeNormalizer()
    assert n.normalize("  hello  \r\n") == "hello  \n"


def test_fake_chunker():
    parsed = ParsedDocument(source_path="test.pdf", content="sample", source_type="pdf")
    c = FakeChunker()
    result = c.chunk(parsed)
    assert len(result.chunks) == 1
    assert result.chunks[0].text == "sample"


@pytest.mark.asyncio
async def test_fake_metadata_extractor():
    chunked = ChunkedDocument(source_path="test.pdf", chunks=[])
    e = FakeMetadataExtractor()
    result = await e.extract(chunked)
    assert result.title == "Extracted Title"
    assert result.document_type == "literature"
