import pytest
import pytest_asyncio
import tempfile
import os
from config.model import StorageConfig
from storage.sqlite_meta import SQLiteMetadataStore
from storage.models import DocumentRecord, ChunkRecord
from retrieval.keyword import SQLiteFTS5Retriever


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest_asyncio.fixture
async def populated_store(db_path):
    config = StorageConfig(sqlite_path=db_path)
    store = SQLiteMetadataStore(config)
    await store.initialize()
    # Insert test documents — FTS5 content-sync triggers auto-index these
    await store.insert_document(DocumentRecord(
        id="doc-1", document_type="literature",
        title="DFT Study of TiO2 Band Gap",
        authors="Smith J", year=2024, journal="Nature",
    ))
    await store.insert_document(DocumentRecord(
        id="doc-2", document_type="experiment",
        title="CV Analysis of Perovskite",
        authors="Wang L", year=2023, journal="Science",
    ))
    await store.insert_chunks([
        ChunkRecord(id="c-1", document_id="doc-1", chunk_index=0,
                    content="The band gap of TiO2 anatase is 3.2 eV.", chroma_id="chroma-1"),
        ChunkRecord(id="c-2", document_id="doc-2", chunk_index=0,
                    content="Perovskite solar cells show high efficiency.", chroma_id="chroma-2"),
    ])
    yield store
    await store.close()


@pytest.mark.asyncio
async def test_keyword_search_finds_chunk(db_path, populated_store):
    """FTS5 should find chunks for documents matching the query."""
    retriever = SQLiteFTS5Retriever(StorageConfig(sqlite_path=db_path))
    # FTS5 indexes document title/authors/keywords/abstract.
    # "TiO2" appears in doc-1's title.
    results = await retriever.search("TiO2")
    assert len(results) >= 1
    # Should return chunks from the matching document
    chunk_ids = {r.chunk_id for r in results}
    assert "c-1" in chunk_ids


@pytest.mark.asyncio
async def test_keyword_search_empty_result(db_path, populated_store):
    retriever = SQLiteFTS5Retriever(StorageConfig(sqlite_path=db_path))
    results = await retriever.search("xyznonexistent12345")
    assert len(results) == 0


@pytest.mark.asyncio
async def test_keyword_search_with_document_type_filter(db_path, populated_store):
    retriever = SQLiteFTS5Retriever(StorageConfig(sqlite_path=db_path))
    # "Perovskite" is in doc-2's title, document_type=experiment
    results = await retriever.search("Perovskite", document_type="experiment")
    assert len(results) >= 1
    for r in results:
        assert r.metadata["document_type"] == "experiment"


@pytest.mark.asyncio
async def test_keyword_search_metadata_populated(db_path, populated_store):
    retriever = SQLiteFTS5Retriever(StorageConfig(sqlite_path=db_path))
    results = await retriever.search("TiO2")
    assert len(results) >= 1
    r = results[0]
    assert r.metadata["title"] == "DFT Study of TiO2 Band Gap"
    assert r.metadata["authors"] == "Smith J"
    assert r.metadata["year"] == 2024
    assert r.metadata["journal"] == "Nature"
    assert r.score == 1.0
