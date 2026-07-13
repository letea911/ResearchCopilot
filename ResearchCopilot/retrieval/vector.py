from storage.interfaces import BaseVectorStore, BaseMetadataStore
from retrieval.interfaces import BaseVectorRetriever
from retrieval.models import RetrievedChunk


class ChromaVectorRetriever(BaseVectorRetriever):
    """Vector retriever wrapping ChromaDB's similarity search.

    Uses BaseVectorStore.query() for vector similarity and enriches results
    with document metadata from BaseMetadataStore when needed.
    """

    def __init__(self, vector_store: BaseVectorStore, meta_store: BaseMetadataStore):
        self._vector_store = vector_store
        self._meta_store = meta_store

    async def search(
        self, embedding: list[float], top_k: int = 10, where: dict | None = None
    ) -> list[RetrievedChunk]:
        results = await self._vector_store.query(embedding, top_k=top_k, where=where)

        return [
            RetrievedChunk(
                chunk_id=r.id,
                content=r.content,
                document_id=r.metadata.get("document_id", ""),
                score=r.score,
                metadata={
                    "title": r.metadata.get("title", ""),
                    "document_type": r.metadata.get("document_type", ""),
                    "chunk_index": r.metadata.get("chunk_index"),
                    "section": r.metadata.get("section"),
                    "page_number": r.metadata.get("page_number"),
                    **{k: v for k, v in r.metadata.items()
                       if k not in ("document_id", "title", "document_type",
                                    "chunk_index", "section", "page_number")},
                },
            )
            for r in results
        ]
