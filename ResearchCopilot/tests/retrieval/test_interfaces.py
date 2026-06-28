import pytest
from retrieval.interfaces import BaseKeywordRetriever, BaseVectorRetriever, BaseHybridRetriever


class FakeKeyword(BaseKeywordRetriever):
    async def search(self, query, top_k=10, document_type=None):
        from retrieval.models import RetrievedChunk
        return [RetrievedChunk(chunk_id="k-1", content=f"kw:{query}", document_id="d1", score=1.0)]


class FakeVector(BaseVectorRetriever):
    async def search(self, embedding, top_k=10, where=None):
        from retrieval.models import RetrievedChunk
        return [RetrievedChunk(chunk_id="v-1", content="vec hit", document_id="d2", score=0.9)]


class FakeHybrid(BaseHybridRetriever):
    async def search(self, query, embedding, top_k=10, document_type=None, keyword_weight=0.3, vector_weight=0.7):
        from retrieval.models import RetrievedChunk
        return [
            RetrievedChunk(chunk_id="h-1", content=f"hybrid:{query}", document_id="d3", score=0.95),
            RetrievedChunk(chunk_id="h-2", content="another", document_id="d4", score=0.80),
        ]


def test_keyword_retriever_abstract():
    with pytest.raises(TypeError):
        BaseKeywordRetriever()


def test_vector_retriever_abstract():
    with pytest.raises(TypeError):
        BaseVectorRetriever()


def test_hybrid_retriever_abstract():
    with pytest.raises(TypeError):
        BaseHybridRetriever()


@pytest.mark.asyncio
async def test_fake_keyword():
    r = FakeKeyword()
    results = await r.search("TiO2")
    assert len(results) == 1
    assert "kw:TiO2" in results[0].content


@pytest.mark.asyncio
async def test_fake_vector():
    r = FakeVector()
    results = await r.search([0.1, 0.2])
    assert len(results) == 1
    assert results[0].score == 0.9


@pytest.mark.asyncio
async def test_fake_hybrid():
    r = FakeHybrid()
    results = await r.search("query", [0.1, 0.2])
    assert len(results) == 2
    assert results[0].score >= results[1].score
