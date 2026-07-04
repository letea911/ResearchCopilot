import re
import aiosqlite
from config.model import StorageConfig
from retrieval.interfaces import BaseKeywordRetriever
from retrieval.models import RetrievedChunk


class SQLiteFTS5Retriever(BaseKeywordRetriever):
    """Keyword retriever using SQLite FTS5 + LIKE fallback.

    Strategy:
    1. Extract meaningful keywords from the query
    2. Try FTS5 MATCH first (fast, on indexed documents)
    3. Fall back to LIKE search on chunks.content if FTS5 returns nothing
    """

    # Words to skip when building search query
    _STOP_WORDS = {
        "the", "a", "an", "is", "are", "was", "were", "of", "in", "on", "at",
        "to", "for", "with", "by", "from", "and", "or", "not", "but", "what",
        "how", "why", "when", "where", "who", "which", "does", "do", "did",
        "can", "could", "would", "should", "will", "shall", "has", "have", "had",
        "be", "been", "being", "it", "its", "this", "that", "these", "those",
    }

    def __init__(self, config: StorageConfig):
        self._db_path = config.sqlite_path

    def _extract_keywords(self, query: str, max_terms: int = 10) -> str:
        """Extract meaningful keywords from a natural language query for FTS5.

        Strips punctuation, removes stop words, wraps each term in quotes.
        Returns FTS5-safe query string like '"TiO2" "band" "gap"'
        """
        # Remove special characters that break FTS5
        cleaned = re.sub(r"[^\w\s-]", " ", query)
        # Extract meaningful words (keep hyphenated terms like N-doped)
        words = [w.strip("-") for w in cleaned.split() if len(w.strip("-")) > 1]
        # Filter stop words (case-insensitive)
        keywords = [w for w in words if w.lower() not in self._STOP_WORDS]
        # Take top N and quote each
        terms = keywords[:max_terms]
        if not terms:
            # Fallback: use the longest words
            terms = sorted(words, key=len, reverse=True)[:5]
        # Quote each term for FTS5 safety
        return " ".join(f'"{t}"' for t in terms)

    async def search(
        self, query: str, top_k: int = 10, document_type: str | None = None
    ) -> list[RetrievedChunk]:
        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row

            fts_query = self._extract_keywords(query)
            rows = []

            # Strategy 1: Try FTS5 MATCH
            try:
                sql = """
                    SELECT c.id as chunk_id, c.content, c.document_id,
                           d.title, d.authors, d.year, d.journal, d.document_type
                    FROM chunks c
                    JOIN documents d ON c.document_id = d.id
                    WHERE d.rowid IN (
                        SELECT rowid FROM documents_fts WHERE documents_fts MATCH ?
                    )
                """
                params = [fts_query]
                if document_type:
                    sql += " AND d.document_type = ?"
                    params.append(document_type)
                sql += " ORDER BY d.rowid LIMIT ?"
                params.append(top_k)

                cursor = await conn.execute(sql, params)
                rows = await cursor.fetchall()
            except Exception:
                rows = []

            # Strategy 2: Fall back to LIKE on chunk content
            if not rows:
                like_terms = fts_query.replace('"', "").split()
                if like_terms:
                    conditions = " OR ".join(["c.content LIKE ?" for _ in like_terms])
                    sql = f"""
                        SELECT c.id as chunk_id, c.content, c.document_id,
                               d.title, d.authors, d.year, d.journal, d.document_type
                        FROM chunks c
                        JOIN documents d ON c.document_id = d.id
                        WHERE ({conditions})
                    """
                    params = [f"%{t}%" for t in like_terms]
                    if document_type:
                        sql += " AND d.document_type = ?"
                        params.append(document_type)
                    sql += " LIMIT ?"
                    params.append(top_k)

                    cursor = await conn.execute(sql, params)
                    rows = await cursor.fetchall()

            return [
                RetrievedChunk(
                    chunk_id=row["chunk_id"],
                    content=row["content"],
                    document_id=row["document_id"],
                    score=1.0,
                    metadata={
                        "title": row["title"] or "",
                        "authors": row["authors"] or "",
                        "year": row["year"],
                        "journal": row["journal"] or "",
                        "document_type": row["document_type"],
                    },
                )
                for row in rows
            ]
