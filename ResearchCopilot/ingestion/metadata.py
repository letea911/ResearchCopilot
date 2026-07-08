import uuid
import re
from datetime import datetime, timezone
from ingestion.interfaces import BaseMetadataExtractor
from ingestion.models import ChunkedDocument
from storage.models import DocumentRecord


# Known journal names mapped by abbreviation or keyword
_JOURNAL_PATTERNS = [
    "Advanced Materials", "Advanced Energy Materials", "Advanced Science",
    "Advanced Functional Materials", "Adv Funct Materials", "Adv Energy Materials",
    "Small", "Nature", "Science", "ACS Nano", "Nano Letters",
    "Journal of the American Chemical Society", "Angewandte Chemie",
    "Chemical Engineering Journal", "Journal of Catalysis", "Applied Catalysis",
    "Energy & Environmental Science", "Journal of Materials Chemistry",
    "Electrochimica Acta", "Journal of Power Sources",
]


class RuleBasedMetadataExtractor(BaseMetadataExtractor):
    """Extract metadata using regex rules + filename heuristics + content parsing.

    Sources checked in order:
    1. raw_metadata dict (from parser — PDF info, BibTeX fields, etc.)
    2. Content header parsing (text before Abstract/Introduction)
    3. Filename patterns
    """

    async def extract(self, chunked: ChunkedDocument) -> DocumentRecord:
        raw = chunked.raw_metadata
        source_path = chunked.source_path

        import os
        filename = os.path.basename(source_path)
        stem = os.path.splitext(filename)[0]

        # Get the full text of the first chunk (usually contains header info)
        first_chunk_text = chunked.chunks[0].text if chunked.chunks else ""

        # === Title ===
        title = raw.get("title", "")
        if not title:
            title = self._extract_title_from_content(first_chunk_text)
        if not title:
            title = stem.replace("_", " ").replace("-", " ")

        # === Authors ===
        authors = raw.get("author", raw.get("authors", None))
        if not authors:
            authors = self._extract_authors_from_content(first_chunk_text)

        # === Year ===
        year = None
        year_str = raw.get("year", "")
        if year_str:
            try:
                year = int(year_str)
            except (ValueError, TypeError):
                pass
        if year is None:
            year = self._extract_year_from_content(first_chunk_text)
        if year is None:
            year_match = re.search(r"(19|20)\d{2}", stem)
            if year_match:
                year = int(year_match.group(0))

        # === Journal ===
        journal = raw.get("journal") or None
        if not journal:
            journal = self._extract_journal_from_content(first_chunk_text)
        if not journal:
            journal = self._extract_journal_from_filename(filename)

        # === DOI ===
        doi = raw.get("doi", None)
        if not doi:
            search_parts = [stem] + [str(v) for v in raw.values() if v is not None]
            doi_match = re.search(r"10\.\d{4,}/[^\s]+", " ".join(search_parts))
            if doi_match:
                doi = doi_match.group(0)

        keywords = raw.get("keywords", None)

        return DocumentRecord(
            id=str(uuid.uuid4()),
            document_type="literature",
            title=title[:500],
            authors=authors[:500] if authors else None,
            year=year,
            journal=journal,
            doi=doi,
            keywords=keywords,
            abstract=None,
            source_type=chunked.source_path.split(".")[-1].lower()
                if "." in chunked.source_path else "pdf",
            file_path=None,
            extra=raw,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def _extract_title_from_content(self, text: str) -> str:
        """Extract title from the first meaningful line(s) of the paper."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines:
            return ""
        # Title is typically the first line, sometimes spans 2 lines
        # Skip lines that look like journal headers, DOIs, or page numbers
        skip_patterns = [
            r"^(www\.|http|DOI:|https?://)",  # URLs
            r"^\d+$",  # just numbers
            r"^[A-Z][a-z]+ \d{4}",  # "January 2024" — date headers
        ]
        title_lines = []
        for line in lines[:5]:  # Look at first 5 lines
            if any(re.match(p, line) for p in skip_patterns):
                continue
            if len(line) < 200 and not line.startswith("Abstract"):
                title_lines.append(line)
                if len(" ".join(title_lines)) > 30:
                    break
        return " ".join(title_lines)[:500]

    def _extract_authors_from_content(self, text: str) -> str | None:
        """Extract authors from the content header area."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if len(lines) < 2:
            return None

        # Blacklist: lines that should NOT be treated as authors
        skip_words = [
            "www.", "http://", "https://", "DOI:", "wileyonlinelibrary",
            " RESEARCH ", "Research Article", "ARTICLE ", "Received:",
            "Accepted:", "Published:", "Abstract", "Introduction",
            "Supplementary", "Supporting Information", "© ", "Copyright",
            "Adv Funct", "Adv Energy", "Advanced Materials", "Advanced Science",
            "Small ", "Nature ", "Science ", "Journal of",
        ]

        for i, line in enumerate(lines[:12]):
            if i == 0:
                continue  # Skip title line

            # Stop at section headers
            if re.match(r"^(Abstract|Introduction|Results|Experimental|Method|Received|Accepted|Published|ARTICLE|Keywords)", line, re.IGNORECASE):
                break

            # Skip blacklisted lines
            if any(w.lower() in line.lower() for w in skip_words):
                continue

            # Real author line: contains name patterns like "Smith J" or "Wang L, Zhang K"
            # Must contain at least one capitalized letter followed by lowercase (a real name)
            # and be reasonably short
            if len(line) < 10 or len(line) > 300:
                continue

            # Check for real name patterns: "Word Word" or "Word, Word" or "Word Initial"
            # Must have at least 2+ groups of letters (words)
            words = [w for w in re.findall(r"[A-Za-zÀ-ɏ]+", line) if len(w) > 1]
            if len(words) >= 2:
                # Clean superscripts, affiliation markers
                cleaned = re.sub(r"[¹²³⁴⁵⁶⁷⁸⁹⁰abcde,*†‡§¶@]", "", line)
                # Remove parenthetical content (affiliations)
                cleaned = re.sub(r"\([^)]*\)", "", cleaned)
                cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
                if 10 < len(cleaned) < 300:
                    return cleaned
        return None

    def _extract_year_from_content(self, text: str) -> int | None:
        """Extract year from the content header."""
        # Look for year in first 500 chars — often in "(2024)" format or "Received: ... 2024"
        header = text[:500]
        # Pattern: parentheses with year
        m = re.search(r"\((\d{4})\)", header)
        if m:
            return int(m.group(1))
        # Pattern: "Published: 2024" or similar
        m = re.search(r"(?:Published|Received|Accepted)[:\s]+.*?(\d{4})", header)
        if m:
            return int(m.group(1))
        # Pattern: journal volume format "24 (2024)" or "Volume 24, 2024"
        m = re.search(r"(?:Vol(?:ume)?\s*\d+[,\s]+)?\(?(\d{4})\)?", header)
        if m and 1990 <= int(m.group(1)) <= 2030:
            return int(m.group(1))
        return None

    def _extract_journal_from_content(self, text: str) -> str | None:
        """Extract journal name from the content header/footer."""
        header = text[:500]
        for journal in _JOURNAL_PATTERNS:
            if journal.lower() in header.lower():
                return journal
        return None

    def _extract_journal_from_filename(self, filename: str) -> str | None:
        """Extract journal name from filename patterns."""
        # Filenames like: "Advanced Materials - 2024 - Hu - Title.pdf"
        # or: "Adv Funct Materials - 2025 - Liu - Title.pdf"
        # or: "1-s2.0-S1385894726022989-main.pdf" (Elsevier — can't extract)
        for journal in _JOURNAL_PATTERNS:
            if journal.lower() in filename.lower():
                return journal
        return None
