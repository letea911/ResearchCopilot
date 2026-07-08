from models.message import ChatMessage, Role
from providers.interfaces import BaseLLMProvider
from storage.interfaces import BaseMetadataStore
from services.interfaces import BaseSummarizeService
from services.models import ServiceResponse, Citation


SUMMARIZE_PROMPT = """You are a research assistant. Summarize the following scientific paper based on its content chunks.

Focus on: {focus}

Provide:
1. Main objective
2. Key methods
3. Principal findings
4. Significance/impact

Paper chunks:
{chunks}"""


class SummarizeService(BaseSummarizeService):
    def __init__(self, llm: BaseLLMProvider, meta_store: BaseMetadataStore, file_store=None):
        self._llm = llm
        self._meta_store = meta_store
        self._file_store = file_store

    async def summarize(self, document_id: str,
                        focus: str | None = None) -> ServiceResponse:
        doc = await self._meta_store.get_document(document_id)
        chunks = await self._meta_store.get_chunks_by_document(document_id)

        chunks_text = "\n\n---\n\n".join(c.content for c in chunks)
        focus_text = focus or "general summary"

        prompt = SUMMARIZE_PROMPT.format(focus=focus_text, chunks=chunks_text)

        messages = [
            ChatMessage(role=Role.USER, content=prompt),
        ]

        answer = await self._llm.chat(messages)

        # Resolve file path for clickable PDF link
        file_path = None
        if doc and doc.file_path and self._file_store:
            abs_path = self._file_store.get_path(doc.file_path)
            file_path = str(abs_path)

        citation = Citation(
            document_id=document_id,
            title=doc.title if doc else "Unknown",
            authors=doc.authors if doc else "",
            year=doc.year if doc else None,
            journal=doc.journal if doc else None,
            file_path=file_path,
        )

        return ServiceResponse(answer=answer, citations=[citation])
