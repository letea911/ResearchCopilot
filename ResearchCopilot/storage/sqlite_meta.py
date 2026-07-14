import aiosqlite
from config.model import StorageConfig
from storage.interfaces import BaseMetadataStore
from storage.models import DocumentRecord, ChunkRecord


class SQLiteMetadataStore(BaseMetadataStore):
    """SQLite-backed metadata store with FTS5 for future keyword search."""

    def __init__(self, config: StorageConfig):
        self._db_path = config.sqlite_path
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self):
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self):
        if self._conn:
            await self._conn.close()

    async def _create_tables(self):
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                document_type TEXT NOT NULL,
                title TEXT NOT NULL,
                authors TEXT,
                year INTEGER,
                journal TEXT,
                doi TEXT UNIQUE,
                keywords TEXT,
                abstract TEXT,
                source_type TEXT DEFAULT 'pdf',
                file_path TEXT,
                extra TEXT,
                collection TEXT DEFAULT '默认库',
                created_at TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS collections (
                name TEXT PRIMARY KEY,
                created_at TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                chroma_id TEXT NOT NULL,
                token_count INTEGER DEFAULT 0,
                page_number INTEGER,
                start_offset INTEGER,
                end_offset INTEGER,
                section TEXT,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            );

            CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
            CREATE INDEX IF NOT EXISTS idx_chunks_chroma_id ON chunks(chroma_id);
            CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
            CREATE INDEX IF NOT EXISTS idx_documents_year ON documents(year);

            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                title, authors, keywords, abstract, content='documents', content_rowid='rowid'
            );

            -- Rebuild FTS index to ensure sync (compensates for missing auto-triggers)
            INSERT INTO documents_fts(documents_fts) VALUES('rebuild');
        """)
        await self._conn.commit()

        # Idempotent migration for existing DBs missing the section column
        try:
            await self._conn.execute("ALTER TABLE chunks ADD COLUMN section TEXT")
            await self._conn.commit()
        except Exception:
            pass  # column already exists

        # Idempotent migration: add `collection` to existing documents (backfills 默认库)
        try:
            await self._conn.execute(
                "ALTER TABLE documents ADD COLUMN collection TEXT DEFAULT '默认库'"
            )
            await self._conn.commit()
        except Exception:
            pass  # column already exists

        # Seed the collections table: always ensure 默认库 exists, and absorb any
        # library names already present on documents (so historical data shows up).
        await self._conn.execute(
            "INSERT OR IGNORE INTO collections (name) VALUES ('默认库')"
        )
        await self._conn.execute(
            """INSERT OR IGNORE INTO collections (name)
               SELECT DISTINCT collection FROM documents
               WHERE collection IS NOT NULL AND collection != ''"""
        )
        await self._conn.commit()

    async def insert_document(self, doc: DocumentRecord) -> None:
        import json
        await self._conn.execute(
            """INSERT INTO documents (id, document_type, title, authors, year,
               journal, doi, keywords, abstract, source_type, file_path,
               extra, collection, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                doc.id, doc.document_type, doc.title, doc.authors,
                doc.year, doc.journal, doc.doi, doc.keywords,
                doc.abstract, doc.source_type, doc.file_path,
                json.dumps(doc.extra) if doc.extra else None,
                doc.collection or "默认库",
                doc.created_at,
            ),
        )
        # Ensure the library exists in the collections table
        await self._conn.execute(
            "INSERT OR IGNORE INTO collections (name) VALUES (?)",
            (doc.collection or "默认库",),
        )
        # Rebuild FTS index to compensate for missing content-sync triggers
        await self._conn.execute(
            "INSERT INTO documents_fts(documents_fts) VALUES('rebuild')"
        )
        await self._conn.commit()

    async def get_document(self, document_id: str) -> DocumentRecord | None:
        import json
        cursor = await self._conn.execute(
            "SELECT * FROM documents WHERE id = ?", (document_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_document(row)

    async def get_document_by_doi(self, doi: str) -> DocumentRecord | None:
        cursor = await self._conn.execute(
            "SELECT * FROM documents WHERE doi = ?", (doi,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_document(row)

    async def list_documents(
        self,
        document_type: str | None = None,
        year: int | None = None,
        collection: str | None = None,
        limit: int = 50,
    ) -> list[DocumentRecord]:
        query = "SELECT * FROM documents WHERE 1=1"
        params = []
        if document_type is not None:
            query += " AND document_type = ?"
            params.append(document_type)
        if year is not None:
            query += " AND year = ?"
            params.append(year)
        if collection is not None:
            query += " AND collection = ?"
            params.append(collection)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor = await self._conn.execute(query, params)
        rows = await cursor.fetchall()
        return [self._row_to_document(r) for r in rows]

    async def list_collections(self) -> list[str]:
        """List all library names (including empty ones)."""
        cursor = await self._conn.execute(
            "SELECT name FROM collections ORDER BY name"
        )
        rows = await cursor.fetchall()
        return [r["name"] for r in rows]

    async def create_collection(self, name: str) -> None:
        """Create a named library (idempotent)."""
        name = (name or "").strip()
        if not name:
            return
        await self._conn.execute(
            "INSERT OR IGNORE INTO collections (name, created_at) VALUES (?, '')",
            (name,),
        )
        await self._conn.commit()

    async def insert_chunks(self, chunks: list[ChunkRecord]) -> None:
        await self._conn.executemany(
            """INSERT INTO chunks (id, document_id, chunk_index, content,
               chroma_id, token_count, page_number, start_offset, end_offset, section)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    c.id, c.document_id, c.chunk_index, c.content,
                    c.chroma_id, c.token_count, c.page_number,
                    c.start_offset, c.end_offset, c.section,
                )
                for c in chunks
            ],
        )
        await self._conn.commit()

    async def get_chunks_by_document(self, document_id: str) -> list[ChunkRecord]:
        cursor = await self._conn.execute(
            "SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index",
            (document_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_chunk(r) for r in rows]

    async def get_chunk_by_chroma_id(self, chroma_id: str) -> ChunkRecord | None:
        cursor = await self._conn.execute(
            "SELECT * FROM chunks WHERE chroma_id = ?", (chroma_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_chunk(row)

    async def update_document_metadata(
        self, document_id, authors=None, year=None, journal=None, doi=None
    ) -> None:
        sets, params = [], []
        if authors is not None:
            sets.append("authors = ?"); params.append(authors)
        if year is not None:
            sets.append("year = ?"); params.append(year)
        if journal is not None:
            sets.append("journal = ?"); params.append(journal)
        if doi is not None:
            sets.append("doi = ?"); params.append(doi)
        if not sets:
            return
        params.append(document_id)
        await self._conn.execute(
            f"UPDATE documents SET {', '.join(sets)} WHERE id = ?", params
        )
        await self._conn.commit()

    def _row_to_document(self, row) -> DocumentRecord:
        import json
        extra = row["extra"]
        return DocumentRecord(
            id=row["id"],
            document_type=row["document_type"],
            title=row["title"],
            authors=row["authors"],
            year=row["year"],
            journal=row["journal"],
            doi=row["doi"],
            keywords=row["keywords"],
            abstract=row["abstract"],
            source_type=row["source_type"],
            file_path=row["file_path"],
            extra=json.loads(extra) if extra else None,
            collection=(row["collection"] if "collection" in row.keys() else None) or "默认库",
            created_at=row["created_at"],
        )

    def _row_to_chunk(self, row) -> ChunkRecord:
        return ChunkRecord(
            id=row["id"],
            document_id=row["document_id"],
            chunk_index=row["chunk_index"],
            content=row["content"],
            chroma_id=row["chroma_id"],
            token_count=row["token_count"],
            page_number=row["page_number"],
            start_offset=row["start_offset"],
            end_offset=row["end_offset"],
            section=row["section"] if "section" in row.keys() else None,
        )
