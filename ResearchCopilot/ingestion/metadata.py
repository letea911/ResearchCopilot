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
                # Clean superscript digits and affiliation symbols only.
                # NOTE: do NOT strip a-e letters — that mangles real names
                # (e.g. "Hybrid Supercapacitor" → "Hyri Suprpitor").
                cleaned = re.sub(r"[¹²³⁴⁵⁶⁷⁸⁹⁰*†‡§¶]", "", line)
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


import json


class LLMMetadataExtractor(BaseMetadataExtractor):
    """Two-stage metadata extractor: regex first, LLM fallback.

    Stage 1: RuleBasedMetadataExtractor (fast, free)
    Stage 2: LLM (DeepSeek) for any missing fields (authors, journal, year)

    Cost: ~100 tokens per paper when LLM is needed.
    """

    def __init__(self, llm_provider=None):
        """llm_provider: any BaseLLMProvider instance. If None, LLM fallback is skipped."""
        self._rule_based = RuleBasedMetadataExtractor()
        self._llm = llm_provider

    async def extract(self, chunked: ChunkedDocument) -> DocumentRecord:
        # Stage 1: rule-based
        doc = await self._rule_based.extract(chunked)

        # Stage 2: LLM fallback when regex results are missing OR look garbled.
        # PDF text extraction often produces mangled author names (missing
        # vowels) and mis-matched journals, so we validate quality, not just
        # presence.
        needs_llm = (
            not doc.authors
            or not doc.journal
            or self._looks_garbled(doc.authors)
            or self._looks_like_title(doc.authors)
        )
        if self._llm and needs_llm:
            try:
                llm_fields = await self._extract_via_llm(chunked)
                # LLM authors override regex when regex is empty/garbled/title-like
                if llm_fields.get("authors") and (
                    not doc.authors
                    or self._looks_garbled(doc.authors)
                    or self._looks_like_title(doc.authors)
                ):
                    doc.authors = llm_fields["authors"]
                # LLM journal overrides regex when regex is empty
                if llm_fields.get("journal") and not doc.journal:
                    doc.journal = llm_fields["journal"]
                # LLM year fills missing or fixes out-of-range years
                if llm_fields.get("year") and (
                    doc.year is None or not (1980 <= (doc.year or 0) <= 2027)
                ):
                    try:
                        y = int(llm_fields["year"])
                        if 1980 <= y <= 2027:
                            doc.year = y
                    except (ValueError, TypeError):
                        pass
                # Never override title with LLM — regex title is usually fine
            except Exception:
                pass  # LLM failed — keep regex results

        # Sanity: drop clearly-wrong regex years even without LLM
        if doc.year is not None and not (1980 <= doc.year <= 2027):
            doc.year = None

        return doc

    @staticmethod
    def _looks_garbled(text: str | None) -> bool:
        """Detect garbled author strings from bad PDF extraction.

        Heuristic: real names have vowels. Garbled PDF text like
        'Boosting Hyri Suprpitor Prformn' has words with few/no vowels.
        """
        if not text:
            return False
        words = [w for w in re.findall(r"[A-Za-z]+", text) if len(w) >= 4]
        if not words:
            return False
        vowels = set("aeiouAEIOU")
        vowelless = sum(1 for w in words if not (set(w) & vowels))
        # If >30% of 4+ letter words lack vowels, it's garbled
        return (vowelless / len(words)) > 0.3

    # Common words that appear in paper titles but never in author name lists
    _TITLE_WORDS = {
        "boosting", "enhanced", "enhancing", "novel", "study", "studies",
        "performance", "hybrid", "synthesis", "analysis", "investigation",
        "engineering", "efficient", "high", "electrode", "material",
        "materials", "toward", "towards", "via", "for", "using", "based",
        "structure", "structural", "electrocatalyst", "catalysis", "oxygen",
        "evolution", "reaction", "supercapacitor", "electrochemical",
        "review", "application", "applications", "design", "strategy",
    }

    @classmethod
    def _looks_like_title(cls, text: str | None) -> bool:
        """Detect when the 'authors' field is actually title text.

        Rule-based extraction sometimes grabs a title continuation line
        instead of the author list. Real author strings don't contain
        title vocabulary like 'Boosting', 'Performance', 'Hybrid'.
        """
        if not text:
            return False
        words = {w.lower() for w in re.findall(r"[A-Za-z]+", text)}
        return len(words & cls._TITLE_WORDS) >= 1

    async def _extract_via_llm(self, chunked: ChunkedDocument) -> dict:
        """Send first chunk's beginning to LLM, get structured metadata back."""
        from models.message import ChatMessage, Role

        # Take first 800 chars of content (enough for title + authors + journal header)
        text_sample = chunked.chunks[0].text[:800] if chunked.chunks else ""
        filename = chunked.source_path

        prompt = f"""Extract bibliographic metadata from this scientific paper excerpt.
Return ONLY valid JSON, no other text.

{{
  "title": "full paper title",
  "authors": "LastName1 FirstInitial, LastName2 FirstInitial",
  "year": 2024,
  "journal": "full journal name"
}}

Filename: {filename}

Excerpt:
{text_sample}"""

        messages = [
            ChatMessage(role=Role.SYSTEM, content="You are a bibliographic metadata extractor. Return only valid JSON."),
            ChatMessage(role=Role.USER, content=prompt),
        ]

        response = await self._llm.chat(messages, temperature=0.0, max_tokens=200)

        # Parse JSON from response (handle ```json wrappers)
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1]
            if response.endswith("```"):
                response = response[:-3]
        return json.loads(response)
