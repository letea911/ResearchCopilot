import uuid
from config.model import ChunkConfig
from ingestion.interfaces import BaseChunker
from ingestion.models import ParsedDocument, ChunkedDocument, ChunkText


class ScientificChunker(BaseChunker):
    """Split scientific text into chunks respecting section and paragraph boundaries.

    Strategy:
    1. Split by double newline (paragraph boundaries) first
    2. If a paragraph exceeds chunk_size, split by sentence boundaries
    3. Apply chunk_overlap between consecutive chunks
    4. Assign chunk positions (chunk_index, start_offset, end_offset)
    """

    def __init__(self, config: ChunkConfig | None = None):
        self._config = config or ChunkConfig()

    def chunk(self, parsed: ParsedDocument) -> ChunkedDocument:
        text = parsed.content
        paragraphs = text.split("\n\n")

        chunks: list[ChunkText] = []
        current_chunk_parts: list[str] = []
        current_length = 0
        current_start = 0
        chunk_index = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_len = len(para)

            if current_length + para_len > self._config.chunk_size and current_chunk_parts:
                # Finalize current chunk
                chunk_text = "\n\n".join(current_chunk_parts)
                end_offset = current_start + len(chunk_text)
                chunks.append(ChunkText(
                    document_id=None,
                    chunk_id=str(uuid.uuid4()),
                    chunk_index=chunk_index,
                    text=chunk_text,
                    start_offset=current_start,
                    end_offset=end_offset,
                ))
                chunk_index += 1

                # Start new chunk with overlap
                if self._config.chunk_overlap > 0 and len(chunk_text) > self._config.chunk_overlap:
                    overlap_text = chunk_text[-self._config.chunk_overlap:]
                    current_chunk_parts = [overlap_text]
                    current_length = len(overlap_text)
                    current_start = end_offset - self._config.chunk_overlap
                else:
                    current_chunk_parts = []
                    current_length = 0
                    current_start = end_offset

            current_chunk_parts.append(para)
            current_length += para_len + 2  # +2 for the "\n\n" separator

        # Don't forget the last chunk
        if current_chunk_parts:
            chunk_text = "\n\n".join(current_chunk_parts)
            chunks.append(ChunkText(
                document_id=None,
                chunk_id=str(uuid.uuid4()),
                chunk_index=chunk_index,
                text=chunk_text,
                start_offset=current_start,
                end_offset=current_start + len(chunk_text),
            ))

        return ChunkedDocument(
            source_path=parsed.source_path,
            chunks=chunks,
            raw_metadata=parsed.raw_metadata,
        )
