from storage.models import DocumentRecord, ChunkRecord, VectorDocument, RetrievalResult


def test_document_record_minimal():
    doc = DocumentRecord(
        id="doc-1",
        document_type="literature",
        title="Test Paper",
    )
    assert doc.id == "doc-1"
    assert doc.document_type == "literature"
    assert doc.authors is None
    assert doc.extra is None


def test_document_record_with_extra():
    doc = DocumentRecord(
        id="doc-2",
        document_type="experiment",
        title="CV Experiment",
        extra={"technique": "CV", "scan_rate": "50 mV/s"},
    )
    assert doc.extra["technique"] == "CV"


def test_chunk_record():
    chunk = ChunkRecord(
        id="chunk-1",
        document_id="doc-1",
        chunk_index=0,
        content="Introduction text...",
        chroma_id="chroma-abc",
        token_count=150,
        page_number=1,
        start_offset=0,
        end_offset=500,
    )
    assert chunk.page_number == 1
    assert chunk.token_count == 150


def test_vector_document():
    vd = VectorDocument(
        id="vd-1",
        embedding=[0.1, 0.2, 0.3],
        content="sample text",
        metadata={"document_id": "doc-1", "title": "Test"},
    )
    assert len(vd.embedding) == 3
    assert vd.metadata["document_id"] == "doc-1"


def test_retrieval_result():
    rr = RetrievalResult(
        id="vd-1",
        content="sample text",
        metadata={"document_id": "doc-1"},
        score=0.95,
    )
    assert rr.score == 0.95
