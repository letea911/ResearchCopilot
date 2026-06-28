import aiosqlite
from config.model import StorageConfig
from retrieval.interfaces import BaseKeywordRetriever
from retrieval.models import RetrievedChunk


class SQLiteFTS5Retriever(BaseKeywordRetriever):
    """Keyword retriever using SQLite FTS5 full-text search.

    Searches the documents_fts virtual table (which indexes title, authors,
    keywords, abstract from the documents table), then returns all chunks
    belonging to matching documents.
    """

    def __init__(self, config: StorageConfig):
        self._db_path = config.sqlite_path

    async def search(
        self, query: str, top_k: int = 10, document_type: str | None = None
    ) -> list[RetrievedChunk]:
        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = aiosqlite.Row
            # FTS5 content-sync table on documents: rowid matches documents.rowid.
            # Find documents matching the FTS5 query, then retrieve their chunks.
            sql = """
                SELECT c.id as chunk_id, c.content, c.document_id,
                       d.title, d.authors, d.year, d.journal, d.document_type
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE d.rowid IN (
                    SELECT rowid FROM documents_fts WHERE documents_fts MATCH ?
                )
            """
            params = [query]
            if document_type:
                sql += " AND d.document_type = ?"
                params.append(document_type)
            sql += " ORDER BY d.rowid LIMIT ?"
            params.append(top_k)

            cursor = await conn.execute(sql, params)
            rows = await cursor.fetchall()

            return [
                RetrievedChunk(
                    chunk_id=row["chunk_id"],
                    content=row["content"],
                    document_id=row["document_id"],
                    score=1.0,  # FTS5 doesn't provide relevance score in this query
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
