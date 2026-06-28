import uuid
import re
from datetime import datetime, timezone
from ingestion.interfaces import BaseMetadataExtractor
from ingestion.models import ChunkedDocument
from storage.models import DocumentRecord


class RuleBasedMetadataExtractor(BaseMetadataExtractor):
    """Extract metadata using regex rules + filename heuristics.

    Sources checked in order:
    1. raw_metadata dict (from parser -- PDF info, BibTeX fields, etc.)
    2. Filename patterns (e.g., "Author_Year_Title.pdf")
    3. Content-first-line heuristic (often contains title)
    """

    async def extract(self, chunked: ChunkedDocument) -> DocumentRecord:
        raw = chunked.raw_metadata
        source_path = chunked.source_path

        # Extract from filename
        import os
        filename = os.path.basename(source_path)
        stem = os.path.splitext(filename)[0]

        # Title: prefer raw_metadata, then first non-empty chunk line, then filename
        title = raw.get("title", "")
        if not title and chunked.chunks:
            first_line = chunked.chunks[0].text.split("\n")[0].strip()
            if len(first_line) < 200:  # reasonable title length
                title = first_line
        if not title:
            title = stem.replace("_", " ").replace("-", " ")

        # Authors: from raw_metadata
        authors = raw.get("author", raw.get("authors", None))

        # Year: try to find 4-digit year in raw_metadata or filename
        year = None
        year_str = raw.get("year", "")
        if year_str:
            try:
                year = int(year_str)
            except (ValueError, TypeError):
                pass
        if year is None:
            year_match = re.search(r"(19|20)\d{2}", stem)
            if year_match:
                year = int(year_match.group(0))

        # DOI: from raw_metadata
        doi = raw.get("doi", None)
        if not doi:
            # Build search string from filename + raw_metadata string values
            search_parts = [stem] + [str(v) for v in raw.values() if v is not None]
            doi_match = re.search(r"10\.\d{4,}/[^\s]+", " ".join(search_parts))
            if doi_match:
                doi = doi_match.group(0)

        # Keywords: from raw_metadata or None
        keywords = raw.get("keywords", None)

        return DocumentRecord(
            id=str(uuid.uuid4()),
            document_type="literature",
            title=title[:500],
            authors=authors[:500] if authors else None,
            year=year,
            journal=raw.get("journal") or None,
            doi=doi,
            keywords=keywords,
            abstract=None,  # would need LLM extraction, reserved
            source_type=chunked.source_path.split(".")[-1].lower()
                if "." in chunked.source_path else "pdf",
            file_path=None,  # set by pipeline after FileStore.save()
            extra=raw,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
