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
        # ChromaDB rejects empty dict metadata and None-valued keys;
        # strip None values and convert empty dicts to None.
        def _clean(md: dict) -> dict | None:
            cleaned = {k: v for k, v in md.items() if v is not None}
            return cleaned or None

        metadatas = [_clean(d.metadata) for d in docs]
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

    async def backfill_metadata(self, key: str, value: str) -> int:
        """Set metadata[key]=value on every vector currently missing that key.

        Fetches all existing vectors' metadata (no embeddings), finds those
        without `key`, and updates only their metadata — vectors are NOT
        recomputed. Returns the number updated.
        """
        got = self._collection.get(include=["metadatas"])
        ids = got.get("ids") or []
        metadatas = got.get("metadatas") or []

        upd_ids, upd_mds = [], []
        for i, vid in enumerate(ids):
            md = metadatas[i] if i < len(metadatas) and metadatas[i] else {}
            if md.get(key) in (None, ""):
                new_md = dict(md)
                new_md[key] = value
                upd_ids.append(vid)
                upd_mds.append(new_md)

        if upd_ids:
            self._collection.update(ids=upd_ids, metadatas=upd_mds)
        return len(upd_ids)
