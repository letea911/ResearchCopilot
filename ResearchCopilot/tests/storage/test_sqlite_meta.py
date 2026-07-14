import pytest
import pytest_asyncio
import tempfile
import os
from pathlib import Path
from config.model import StorageConfig
from storage.models import DocumentRecord, ChunkRecord
from storage.sqlite_meta import SQLiteMetadataStore


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def config(db_path):
    return StorageConfig(sqlite_path=db_path)


@pytest_asyncio.fixture
async def store(config):
    s = SQLiteMetadataStore(config)
    await s.initialize()
    yield s
    await s.close()


@pytest.mark.asyncio
async def test_insert_and_get_document(store):
    doc = DocumentRecord(
        id="doc-1",
        document_type="literature",
        title="Density Functional Theory Basics",
        authors="Kohn W, Sham L",
        year=1965,
        journal="Physical Review",
        doi="10.1103/physrev.140.a1133",
        keywords="DFT, Kohn-Sham",
        source_type="pdf",
        file_path="papers/dft_basics.pdf",
        created_at="2026-06-26",
    )
    await store.insert_document(doc)
    result = await store.get_document("doc-1")
    assert result is not None
    assert result.title == "Density Functional Theory Basics"
    assert result.authors == "Kohn W, Sham L"
    assert result.year == 1965
    assert result.doi == "10.1103/physrev.140.a1133"


@pytest.mark.asyncio
async def test_get_document_not_found(store):
    result = await store.get_document("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_get_document_by_doi(store):
    doc = DocumentRecord(
        id="doc-2", document_type="literature", title="Test",
        doi="10.1000/test",
    )
    await store.insert_document(doc)
    result = await store.get_document_by_doi("10.1000/test")
    assert result is not None
    assert result.id == "doc-2"


@pytest.mark.asyncio
async def test_list_documents_filter_by_type(store):
    await store.insert_document(DocumentRecord(
        id="lit-1", document_type="literature", title="Paper A"))
    await store.insert_document(DocumentRecord(
        id="exp-1", document_type="experiment", title="Experiment A"))

    papers = await store.list_documents(document_type="literature")
    assert len(papers) == 1
    assert papers[0].id == "lit-1"


@pytest.mark.asyncio
async def test_list_documents_filter_by_year(store):
    await store.insert_document(DocumentRecord(
        id="a", document_type="literature", title="Old", year=2000))
    await store.insert_document(DocumentRecord(
        id="b", document_type="literature", title="New", year=2024))

    results = await store.list_documents(year=2024)
    assert len(results) == 1
    assert results[0].id == "b"


@pytest.mark.asyncio
async def test_list_documents_limit(store):
    for i in range(10):
        await store.insert_document(DocumentRecord(
            id=f"doc-{i}", document_type="literature", title=f"Paper {i}"))
    results = await store.list_documents(limit=5)
    assert len(results) == 5


@pytest.mark.asyncio
async def test_insert_and_get_chunks(store):
    await store.insert_document(DocumentRecord(
        id="doc-3", document_type="literature", title="Chunk Test"))
    chunks = [
        ChunkRecord(
            id="c-0", document_id="doc-3", chunk_index=0,
            content="First chunk.", chroma_id="chroma-0", token_count=3),
        ChunkRecord(
            id="c-1", document_id="doc-3", chunk_index=1,
            content="Second chunk.", chroma_id="chroma-1", token_count=3,
            page_number=2, start_offset=100, end_offset=200),
    ]
    await store.insert_chunks(chunks)

    retrieved = await store.get_chunks_by_document("doc-3")
    assert len(retrieved) == 2
    assert retrieved[0].chunk_index == 0
    assert retrieved[1].chunk_index == 1
    assert retrieved[1].page_number == 2


@pytest.mark.asyncio
async def test_get_chunk_by_chroma_id(store):
    await store.insert_document(DocumentRecord(
        id="doc-4", document_type="literature", title="Chroma Lookup"))
    await store.insert_chunks([
        ChunkRecord(id="c-x", document_id="doc-4", chunk_index=0,
                    content="Find me.", chroma_id="chroma-find"),
    ])
    result = await store.get_chunk_by_chroma_id("chroma-find")
    assert result is not None
    assert result.id == "c-x"


@pytest.mark.asyncio
async def test_duplicate_document_id_raises(store):
    doc = DocumentRecord(id="dup", document_type="literature", title="First")
    await store.insert_document(doc)
    with pytest.raises(Exception):
        await store.insert_document(doc)


@pytest.mark.asyncio
async def test_document_default_collection(store):
    await store.insert_document(DocumentRecord(
        id="c-def", document_type="literature", title="No lib specified"))
    result = await store.get_document("c-def")
    assert result.collection == "默认库"


@pytest.mark.asyncio
async def test_list_documents_filter_by_collection(store):
    await store.insert_document(DocumentRecord(
        id="oer-1", document_type="literature", title="OER paper",
        collection="OER"))
    await store.insert_document(DocumentRecord(
        id="ldh-1", document_type="literature", title="LDH paper",
        collection="LDH"))

    oer = await store.list_documents(collection="OER")
    assert len(oer) == 1
    assert oer[0].id == "oer-1"


@pytest.mark.asyncio
async def test_list_and_create_collections(store):
    # 默认库 is always seeded
    assert "默认库" in await store.list_collections()

    await store.create_collection("OER")
    await store.create_collection("OER")  # idempotent
    cols = await store.list_collections()
    assert "OER" in cols
    assert cols.count("OER") == 1


@pytest.mark.asyncio
async def test_insert_document_registers_collection(store):
    await store.insert_document(DocumentRecord(
        id="auto-lib", document_type="literature", title="Auto",
        collection="高熵"))
    assert "高熵" in await store.list_collections()
