import pytest
import pytest_asyncio
import tempfile
import shutil
import os
from pathlib import Path
from config.model import StorageConfig
from storage.models import VectorDocument
from storage.chroma_vector import ChromaVectorStore


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def config(temp_dir):
    return StorageConfig(chroma_persist_dir=temp_dir)


@pytest_asyncio.fixture
async def store(config):
    s = ChromaVectorStore(config)
    await s.initialize()
    yield s
    # No explicit close needed for ChromaDB in-memory/test


@pytest.mark.asyncio
async def test_add_and_count(store):
    assert await store.count() == 0

    docs = [
        VectorDocument(
            id="v-1",
            embedding=[0.1, 0.2, 0.3],
            content="First test document.",
            metadata={"document_id": "doc-1", "title": "Paper A"},
        ),
        VectorDocument(
            id="v-2",
            embedding=[0.4, 0.5, 0.6],
            content="Second test document.",
            metadata={"document_id": "doc-2", "title": "Paper B"},
        ),
    ]
    await store.add(docs)
    assert await store.count() == 2


@pytest.mark.asyncio
async def test_query_returns_results(store):
    await store.add([
        VectorDocument(
            id="qa",
            embedding=[1.0, 0.0, 0.0],
            content="About catalysis.",
            metadata={"document_id": "cat-1"},
        ),
        VectorDocument(
            id="qb",
            embedding=[0.0, 1.0, 0.0],
            content="About electrochemistry.",
            metadata={"document_id": "ec-1"},
        ),
    ])

    results = await store.query([1.0, 0.1, 0.0], top_k=2)
    assert len(results) == 2
    assert results[0].id == "qa"  # closest to query
    assert results[0].score >= results[1].score


@pytest.mark.asyncio
async def test_query_with_metadata_filter(store):
    await store.add([
        VectorDocument(
            id="x",
            embedding=[1.0, 0.0],
            content="Literature paper.",
            metadata={"document_id": "d1", "document_type": "literature"},
        ),
        VectorDocument(
            id="y",
            embedding=[0.9, 0.1],
            content="Experiment data.",
            metadata={"document_id": "d2", "document_type": "experiment"},
        ),
    ])

    results = await store.query(
        [1.0, 0.0], top_k=5,
        where={"document_type": "literature"},
    )
    assert len(results) == 1
    assert results[0].id == "x"


@pytest.mark.asyncio
async def test_delete_removes_vectors(store):
    await store.add([
        VectorDocument(id="del-1", embedding=[0.1], content="del", metadata={}),
        VectorDocument(id="del-2", embedding=[0.2], content="keep", metadata={}),
    ])
    assert await store.count() == 2

    await store.delete(["del-1"])
    assert await store.count() == 1

    results = await store.query([0.0], top_k=5)
    assert results[0].id == "del-2"


@pytest.mark.asyncio
async def test_add_empty_list(store):
    await store.add([])
    assert await store.count() == 0


@pytest.mark.asyncio
async def test_query_empty_store(store):
    results = await store.query([0.1, 0.2])
    assert results == []
