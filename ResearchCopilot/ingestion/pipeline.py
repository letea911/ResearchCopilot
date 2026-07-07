import hashlib
import uuid
from pathlib import Path
from ingestion.interfaces import BaseParser, BaseNormalizer, BaseChunker, BaseMetadataExtractor
from storage.interfaces import BaseFileStore, BaseMetadataStore, BaseVectorStore
from storage.models import ChunkRecord, VectorDocument
from providers.interfaces import BaseEmbeddingProvider


class IngestionPipeline:
    """Orchestrate the full ingestion flow with idempotency via file hash."""

    def __init__(
        self,
        parsers: dict[str, BaseParser],   # {"pdf": PyMuPDFParser(), ...}
        normalizer: BaseNormalizer,
        chunker: BaseChunker,
        metadata_extractor: BaseMetadataExtractor,
        embedder: BaseEmbeddingProvider,
        file_store: BaseFileStore,
        meta_store: BaseMetadataStore,
        vector_store: BaseVectorStore,
    ):
        self._parsers = parsers
        self._normalizer = normalizer
        self._chunker = chunker
        self._metadata_extractor = metadata_extractor
        self._embedder = embedder
        self._file_store = file_store
        self._meta_store = meta_store
        self._vector_store = vector_store

    def _get_parser(self, source: Path) -> BaseParser | None:
        suffix = source.suffix.lower()
        if suffix in self._parsers:
            return self._parsers[suffix]
        for parser in self._parsers.values():
            if parser.supports(source):
                return parser
        return None

    def _compute_hash(self, source: Path) -> str:
        """Compute SHA-256 hash of file for dedup."""
        hasher = hashlib.sha256()
        with open(source, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    async def ingest(self, source: Path) -> str:
        """Ingest a single file. Returns document_id. Idempotent via file hash."""
        file_hash = self._compute_hash(source)

        # Idempotency check: skip if source file already matches a stored file_path
        docs = await self._meta_store.list_documents(limit=10000)
        source_name = source.name
        for d in docs:
            if d.file_path and source_name in d.file_path:
                print(f'  SKIP: {source_name} (already imported as {d.id[:8]})')
                return d.id

        # 1. Parse
        parser = self._get_parser(source)
        if parser is None:
            raise ValueError(f"No parser found for {source.suffix}")

        parsed = await parser.parse(source)

        # 2. Normalize
        parsed.content = self._normalizer.normalize(parsed.content)

        # 3. Chunk
        chunked = self._chunker.chunk(parsed)

        # 4. Extract metadata
        doc_record = await self._metadata_extractor.extract(chunked)
        # Store file hash in extra for dedup, preserve real DOI
        if doc_record.extra is None:
            doc_record.extra = {}
        doc_record.extra["file_hash"] = file_hash

        # 5. File Store
        file_path = self._file_store.save(source, category="papers")
        doc_record.file_path = file_path

        # 6. Metadata Store -- insert document
        await self._meta_store.insert_document(doc_record)

        # 7. Embedding + Vector Store
        if chunked.chunks:
            texts = [c.text for c in chunked.chunks]
            embeddings = await self._embedder.embed(texts)

            vector_docs = []
            chunk_records = []
            for i, chunk_text in enumerate(chunked.chunks):
                chroma_id = str(uuid.uuid4())
                chunk_text.document_id = doc_record.id
                chunk_text.chunk_id = chroma_id

                vector_docs.append(VectorDocument(
                    id=chroma_id,
                    embedding=embeddings[i],
                    content=chunk_text.text,
                    metadata={
                        "document_id": doc_record.id,
                        "document_type": doc_record.document_type,
                        "title": doc_record.title,
                        "chunk_index": i,
                    },
                ))

                chunk_records.append(ChunkRecord(
                    id=chroma_id,
                    document_id=doc_record.id,
                    chunk_index=i,
                    content=chunk_text.text,
                    chroma_id=chroma_id,
                    token_count=len(chunk_text.text.split()),
                    page_number=chunk_text.page_number,
                    start_offset=chunk_text.start_offset,
                    end_offset=chunk_text.end_offset,
                ))

            await self._vector_store.add(vector_docs)
            await self._meta_store.insert_chunks(chunk_records)

        return doc_record.id

    async def ingest_batch(self, sources: list[Path]) -> list[str]:
        """Ingest multiple files. Returns list of document_ids."""
        results = []
        for source in sources:
            try:
                doc_id = await self.ingest(source)
                results.append(doc_id)
            except Exception as e:
                results.append(f"ERROR:{source}:{e}")
        return results
