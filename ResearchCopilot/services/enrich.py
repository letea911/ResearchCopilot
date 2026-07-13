import re
from difflib import SequenceMatcher
from ingestion.bibtex import BibTeXParser, BibEntry
from storage.interfaces import BaseMetadataStore


class MetadataEnricher:
    """Match .bib entries to library documents and fix their metadata."""

    def __init__(self, meta_store: BaseMetadataStore, threshold: float = 0.85):
        self._meta_store = meta_store
        self._parser = BibTeXParser()
        self._threshold = threshold

    @staticmethod
    def _norm(title: str) -> str:
        return re.sub(r"[^a-z0-9]", "", (title or "").lower())

    async def enrich_from_bib(self, bib_path) -> dict:
        """Returns {'matched': N, 'updated': N, 'unmatched': [titles]}."""
        entries = self._parser.parse_entries(bib_path)
        docs = await self._meta_store.list_documents(limit=10000)

        matched, updated, unmatched = 0, 0, []
        for entry in entries:
            doc = self._find_match(entry, docs)
            if doc is None:
                unmatched.append(entry.title[:60])
                continue
            matched += 1
            await self._meta_store.update_document_metadata(
                doc.id,
                authors=entry.authors,
                year=entry.year,
                journal=entry.journal,
                doi=entry.doi,
            )
            updated += 1
        return {"matched": matched, "updated": updated, "unmatched": unmatched,
                "total_entries": len(entries)}

    def _find_match(self, entry: BibEntry, docs: list):
        # 1. DOI exact match
        if entry.doi:
            for d in docs:
                if d.doi and d.doi.lower() == entry.doi.lower():
                    return d
        # 2. Title similarity
        entry_norm = self._norm(entry.title)
        if not entry_norm:
            return None
        best, best_score = None, 0.0
        for d in docs:
            score = SequenceMatcher(None, entry_norm, self._norm(d.title)).ratio()
            if score > best_score:
                best, best_score = d, score
        return best if best_score >= self._threshold else None
