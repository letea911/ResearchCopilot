from providers.interfaces import BaseEmbeddingProvider
from retrieval.interfaces import BaseHybridRetriever
from services.interfaces import BaseSearchService
from services.models import SearchResponse


class SearchService(BaseSearchService):
    """Pure retrieval search — no LLM involved."""

    def __init__(self, embedder: BaseEmbeddingProvider, retriever: BaseHybridRetriever):
        self._embedder = embedder
        self._retriever = retriever

    async def search(self, query: str, top_k: int = 20,
                     document_type: str | None = None,
                     collections: list[str] | None = None) -> SearchResponse:
        embeddings = await self._embedder.embed([query])
        results = await self._retriever.search(
            query, embeddings[0], top_k=top_k, document_type=document_type,
            collections=collections,
        )
        return SearchResponse(query=query, results=results, total_hits=len(results))
