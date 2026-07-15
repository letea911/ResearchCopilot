import pytest
from pathlib import Path
from storage.interfaces import BaseFileStore, BaseMetadataStore, BaseVectorStore
from storage.models import DocumentRecord, ChunkRecord


class FakeFileStore(BaseFileStore):
    def save(self, source, category):
        return f"{category}/test.pdf"
    def get_path(self, relative_path):
        return Path("/fake") / relative_path
    def list(self, category):
        return [f"{category}/test.pdf"]
    def delete(self, relative_path):
        pass


class FakeMetadataStore(BaseMetadataStore):
    async def insert_document(self, doc): pass
    async def get_document(self, document_id): return None
    async def get_document_by_doi(self, doi): return None
    async def list_documents(self, document_type=None, year=None, collection=None, limit=50): return []
    async def list_collections(self, parent=None): return []
    async def get_collection_tree(self): return []
    async def expand_collections(self, names): return names
    async def create_collection(self, name, parent=None): pass
    async def rename_collection(self, old_name, new_name): return True
    async def delete_collection(self, name, reassign_to="默认库"): return 0
    async def insert_chunks(self, chunks): pass
    async def get_chunks_by_document(self, document_id): return []
    async def get_chunk_by_chroma_id(self, chroma_id): return None
    async def update_document_metadata(self, document_id, authors=None, year=None, journal=None, doi=None, keywords=None, abstract=None, collection=None): pass


class FakeVectorStore(BaseVectorStore):
    async def add(self, docs): pass
    async def query(self, embedding, top_k=10, where=None): return []
    async def delete(self, ids): pass
    async def count(self): return 0
    async def backfill_metadata(self, key, value): return 0
    async def update_metadata_by_filter(self, where, updates): return 0


def test_file_store_instantiable():
    store = FakeFileStore()
    assert store.save(Path("test.pdf"), "papers") == "papers/test.pdf"
    resolved = store.get_path("papers/test.pdf")
    assert resolved.parts[-2:] == ("papers", "test.pdf")


def test_metadata_store_is_abstract():
    with pytest.raises(TypeError):
        BaseMetadataStore()


def test_vector_store_is_abstract():
    with pytest.raises(TypeError):
        BaseVectorStore()


@pytest.mark.asyncio
async def test_metadata_store_minimal_impl():
    store = FakeMetadataStore()
    assert await store.get_document("any") is None
    assert await store.list_documents() == []


@pytest.mark.asyncio
async def test_vector_store_minimal_impl():
    store = FakeVectorStore()
    assert await store.count() == 0
    assert await store.query([0.1]) == []
