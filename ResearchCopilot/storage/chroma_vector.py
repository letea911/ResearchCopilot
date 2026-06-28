import chromadb
from config.model import StorageConfig
from storage.interfaces import BaseVectorStore
from storage.models import VectorDocument, RetrievalResult


class ChromaVectorStore(BaseVectorStore):
    """ChromaDB-backed vector store."""

    def __init__(self, config: StorageConfig):
        self._persist_dir = config.chroma_persist_dir
        self._client = None
        self._collection = None

    async def initialize(self):
        self._client = chromadb.PersistentClient(path=self._persist_dir)
        self._collection = self._client.get_or_create_collection(
            name="research_documents"
        )

    async def add(self, docs: list[VectorDocument]) -> None:
        if not docs:
            return
        # ChromaDB rejects empty dict metadata; convert to None
        metadatas = [d.metadata if d.metadata else None for d in docs]
        self._collection.add(
            ids=[d.id for d in docs],
            embeddings=[d.embedding for d in docs],
            documents=[d.content for d in docs],
            metadatas=metadatas,
        )

    async def query(
        self,
        embedding: list[float],
        top_k: int = 10,
        where: dict | None = None,
    ) -> list[RetrievalResult]:
        kwargs = {
            "query_embeddings": [embedding],
            "n_results": top_k,
        }
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)

        if not results["ids"] or not results["ids"][0]:
            return []

        return [
            RetrievalResult(
                id=results["ids"][0][i],
                content=results["documents"][0][i] or "",
                metadata=results["metadatas"][0][i] or {},
                score=1.0 - results["distances"][0][i]
                if results.get("distances") else 0.0,
            )
            for i in range(len(results["ids"][0]))
        ]

    async def delete(self, ids: list[str]) -> None:
        if ids:
            self._collection.delete(ids=ids)

    async def count(self) -> int:
        return self._collection.count()
