from retrieval.interfaces import BaseKeywordRetriever, BaseVectorRetriever, BaseHybridRetriever
from retrieval.models import RetrievedChunk


class WeightedHybridRetriever(BaseHybridRetriever):
    """Hybrid retriever using Reciprocal Rank Fusion (RRF).

    Combines keyword (FTS5) and vector (ChromaDB) results, assigning
    configurable weights to each source and deduplicating by chunk_id.
    """

    def __init__(self, keyword: BaseKeywordRetriever, vector: BaseVectorRetriever):
        self._keyword = keyword
        self._vector = vector
        self._k = 60  # RRF constant

    async def search(
        self,
        query: str,
        embedding: list[float],
        top_k: int = 10,
        document_type: str | None = None,
        collections: list[str] | None = None,
        keyword_weight: float = 0.3,
        vector_weight: float = 0.7,
    ) -> list[RetrievedChunk]:
        # Build the vector-side metadata filter (this closes the gap where the
        # vector retriever was previously called with no filter at all).
        conditions = []
        if document_type:
            conditions.append({"document_type": document_type})
        if collections:
            conditions.append({"collection": {"$in": list(collections)}})
        if len(conditions) == 1:
            where = conditions[0]
        elif len(conditions) > 1:
            where = {"$and": conditions}
        else:
            where = None

        # Run both retrievals with wider top_k for better fusion
        kw_results = await self._keyword.search(
            query, top_k=top_k * 2, document_type=document_type,
            collections=collections,
        )
        vec_results = await self._vector.search(embedding, top_k=top_k * 2, where=where)

        # RRF: score = sum(weight * 1/(k + rank)) per result
        scores: dict[str, tuple[RetrievedChunk, float]] = {}

        for rank, chunk in enumerate(kw_results):
            rrf_score = keyword_weight * (1.0 / (self._k + rank + 1))
            key = chunk.chunk_id
            if key in scores:
                existing, prev_score = scores[key]
                scores[key] = (existing, prev_score + rrf_score)
            else:
                scores[key] = (chunk, rrf_score)

        for rank, chunk in enumerate(vec_results):
            rrf_score = vector_weight * (1.0 / (self._k + rank + 1))
            key = chunk.chunk_id
            if key in scores:
                existing, prev_score = scores[key]
                scores[key] = (existing, prev_score + rrf_score)
            else:
                scores[key] = (chunk, rrf_score)

        # Sort by fused score, return top_k
        sorted_results = sorted(scores.values(), key=lambda x: x[1], reverse=True)
        return [chunk for chunk, _ in sorted_results[:top_k]]
