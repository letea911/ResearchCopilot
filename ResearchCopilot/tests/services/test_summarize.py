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


@pytest.mark.asyncio
async def test_compare_returns_response_with_all_citations():
    llm = AsyncMock()
    llm.chat.return_value = "Paper 1 uses DFT, Paper 2 uses experiments. [1][2]"
    meta = AsyncMock()

    docs = {
        "doc-1": DocumentRecord(id="doc-1", document_type="literature",
                                title="DFT Study", authors="Smith J", year=2024),
        "doc-2": DocumentRecord(id="doc-2", document_type="literature",
                                title="Experimental Study", authors="Wang L", year=2023),
    }
    meta.get_document.side_effect = lambda did: docs.get(did)
    meta.get_chunks_by_document.return_value = [
        ChunkRecord(id="c-1", document_id="doc-1", chunk_index=0,
                    content="Some content", chroma_id="chr-1"),
    ]

    svc = SummarizeService(llm, meta)
    result = await svc.compare(["doc-1", "doc-2"], focus="methods")
    assert isinstance(result, ServiceResponse)
    assert len(result.citations) == 2
    assert result.citations[0].title == "DFT Study"
    assert result.citations[1].title == "Experimental Study"
    # Both papers should appear in the prompt sent to the LLM
    prompt = llm.chat.call_args[0][0][0].content
    assert "DFT Study" in prompt and "Experimental Study" in prompt

