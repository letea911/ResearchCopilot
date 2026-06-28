import pytest
from unittest.mock import AsyncMock
from services.summarize import SummarizeService
from services.models import ServiceResponse
from storage.models import DocumentRecord, ChunkRecord


@pytest.fixture
def svc():
    llm = AsyncMock()
    llm.chat.return_value = "This paper studies TiO2 photocatalysis using DFT."
    meta = AsyncMock()
    meta.get_document.return_value = DocumentRecord(
        id="doc-1", document_type="literature", title="TiO2 Study",
        authors="Smith J", year=2024,
    )
    meta.get_chunks_by_document.return_value = [
        ChunkRecord(id="c-1", document_id="doc-1", chunk_index=0,
                    content="Introduction...", chroma_id="chr-1"),
    ]
    return SummarizeService(llm, meta)


@pytest.mark.asyncio
async def test_summarize_returns_response(svc):
    result = await svc.summarize("doc-1")
    assert isinstance(result, ServiceResponse)
    assert "TiO2" in result.answer
    assert len(result.citations) == 1
    assert result.citations[0].title == "TiO2 Study"
