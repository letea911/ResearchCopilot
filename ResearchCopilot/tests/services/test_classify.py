import json
import pytest
import tempfile, os
import pytest_asyncio
from unittest.mock import AsyncMock

from config.model import StorageConfig
from services.classify import ClassifierService
from services.models import ClassifyResult
from storage.models import DocumentRecord
from storage.sqlite_meta import SQLiteMetadataStore


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest_asyncio.fixture
async def meta_store(db_path):
    cfg = StorageConfig(sqlite_path=db_path)
    s = SQLiteMetadataStore(cfg)
    await s.initialize()
    yield s
    await s.close()


@pytest.fixture
def mock_llm():
    m = AsyncMock()
    m.chat.return_value = json.dumps({
        "keywords": ["OER", "LDH", "electrocatalysis"],
        "abstract": "This paper investigates OER performance of high-entropy LDHs.",
        "suggested_collection": "OER",
        "new_collection": "",
        "confidence": 0.92,
    })
    return m


@pytest.fixture
def service(mock_llm, meta_store):
    return ClassifierService(mock_llm, meta_store)


@pytest.mark.asyncio
async def test_classify_single_returns_structured_result(service, meta_store):
    await meta_store.insert_document(DocumentRecord(
        id="cls-1", document_type="literature", title="Test paper",
        authors="Zhang et al.", collection="默认库",
    ))
    # Add a chunk so there is "full text"
    from storage.models import ChunkRecord
    await meta_store.insert_chunks([
        ChunkRecord(
            id="chk-1", document_id="cls-1", chunk_index=0,
            content="This is the full text of the paper about OER on LDHs.",
            chroma_id="chr-1", token_count=15,
        ),
    ])

    result = await service.classify_single("cls-1")
    assert isinstance(result, ClassifyResult)
    assert result.document_id == "cls-1"
    assert "OER" in result.keywords
    assert "electrocatalysis" in result.keywords
    assert len(result.abstract) > 10
    assert result.suggested_collection == "OER"
    assert result.confidence == 0.92


@pytest.mark.asyncio
async def test_classify_single_document_not_found(service):
    result = await service.classify_single("nonexistent")
    assert result.document_id == "nonexistent"
    assert result.keywords == []
    assert result.abstract == ""


@pytest.mark.asyncio
async def test_classify_batch_collects_all(service, meta_store):
    await meta_store.insert_document(DocumentRecord(
        id="b1", document_type="literature", title="Paper 1", collection="默认库"))
    await meta_store.insert_document(DocumentRecord(
        id="b2", document_type="literature", title="Paper 2", collection="默认库"))
    for cid in ("b1", "b2"):
        from storage.models import ChunkRecord
        await meta_store.insert_chunks([
            ChunkRecord(
                id=f"c-{cid}", document_id=cid, chunk_index=0,
                content="Full text content.", chroma_id=f"chr-{cid}",
                token_count=3,
            ),
        ])

    results = await service.classify_batch(["b1", "b2"])
    assert len(results) == 2
    assert set(r.document_id for r in results) == {"b1", "b2"}


@pytest.mark.asyncio
async def test_classify_batch_skips_errors(service):
    # "bad-id" doesn't exist — should produce an empty result, not crash
    results = await service.classify_batch(["bad-id"])
    assert len(results) == 1
    assert results[0].document_id == "bad-id"
    assert results[0].keywords == []


@pytest.mark.asyncio
async def test_parse_json_with_code_fence():
    raw = '''```json
{"keywords": ["a"], "abstract": "b"}
```'''
    parsed = ClassifierService._parse_json(raw)
    assert parsed["keywords"] == ["a"]

    # No fence at all
    parsed2 = ClassifierService._parse_json('{"x": 1}')
    assert parsed2["x"] == 1
