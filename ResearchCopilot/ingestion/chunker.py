import re
import uuid
from config.model import ChunkConfig
from ingestion.interfaces import BaseChunker
from ingestion.models import ParsedDocument, ChunkedDocument, ChunkText


SECTION_RE = re.compile(
    r"^\s*(?:\d+\.?\s*)?(Abstract|Introduction|Experimental|Methods?|Materials?|Results?(?:\s+and\s+Discussion)?|Discussion|Conclusions?|References|Acknowledge?ments?)\b",
    re.IGNORECASE,
)


class ScientificChunker(BaseChunker):
    """Split scientific text into chunks respecting section and paragraph boundaries.

    Strategy:
    1. Split by double newline (paragraph boundaries) first
    2. If a paragraph exceeds chunk_size, split by sentence boundaries
    3. Apply chunk_overlap between consecutive chunks
    4. Assign chunk positions (chunk_index, start_offset, end_offset)
    5. Track the current paper section and compute page numbers per chunk
    """

    def __init__(self, config: ChunkConfig | None = None):
        self._config = config or ChunkConfig()

    def _build_page_ends(self, page_texts: list[str]) -> list[int]:
        """Cumulative page-end offsets matching the "\\n\\n".join() layout."""
        page_ends: list[int] = []
        cumulative = 0
        for page_text in page_texts:
            cumulative += len(page_text) + 2  # +2 for the "\n\n" join separator
            page_ends.append(cumulative)
        return page_ends

    def _page_for_offset(self, offset: int | None, page_ends: list[int]) -> int | None:
        """Return the 1-indexed page a given start_offset falls into."""
        if not page_ends or offset is None:
            return None
        for i, end in enumerate(page_ends):
            if offset < end:
                return i + 1
        return len(page_ends)

    def _detect_section(self, para: str) -> str | None:
        """Scan each line of a paragraph for a section heading.

        Real PDFs (esp. two-column) merge a whole page into one paragraph,
        so the heading like '1. Introduction' sits on an interior line rather
        than the paragraph start. Returns the LAST heading found (closest to
        the text that follows), or None.
        """
        found: str | None = None
        for line in para.split("\n"):
            line = line.strip()
            if not line or len(line) > 60:  # headings are short lines
                continue
            m = SECTION_RE.match(line)
            if m:
                found = m.group(1).title()
        return found

    def chunk(self, parsed: ParsedDocument) -> ChunkedDocument:
        text = parsed.content
        paragraphs = text.split("\n\n")
        page_ends = self._build_page_ends(parsed.page_texts)

        chunks: list[ChunkText] = []
        current_chunk_parts: list[str] = []
        current_length = 0
        current_start = 0
        chunk_index = 0
        current_section: str | None = None

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            detected = self._detect_section(para)
            if detected:
                current_section = detected

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
                    section=current_section,
                    page_number=self._page_for_offset(current_start, page_ends),
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
                section=current_section,
                page_number=self._page_for_offset(current_start, page_ends),
            ))

        return ChunkedDocument(
            source_path=parsed.source_path,
            chunks=chunks,
            raw_metadata=parsed.raw_metadata,
        )
