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


COMPARE_PROMPT = """You are a research assistant. Compare the following scientific papers side by side.

Focus on: {focus}

For the comparison, address these dimensions across all papers:
1. Research objective / problem addressed
2. Methods / approach
3. Key findings and performance data (cite specific numbers where available)
4. Strengths and limitations
5. How they differ and what they agree on

Reference each paper by its number [1], [2], etc.

Papers:
{papers}"""


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

    async def compare(self, document_ids: list[str],
                      focus: str | None = None) -> ServiceResponse:
        focus_text = focus or "general comparison"
        paper_blocks = []
        citations = []

        for i, doc_id in enumerate(document_ids):
            doc = await self._meta_store.get_document(doc_id)
            chunks = await self._meta_store.get_chunks_by_document(doc_id)
            # Use up to the first 5 chunks per paper to stay within context
            excerpt = "\n\n".join(c.content for c in chunks[:5])
            title = doc.title if doc else f"Document {doc_id}"
            paper_blocks.append(f"[{i+1}] {title}:\n{excerpt}")

            file_path = None
            if doc and doc.file_path and self._file_store:
                file_path = str(self._file_store.get_path(doc.file_path))
            citations.append(Citation(
                document_id=doc_id,
                title=doc.title if doc else "Unknown",
                authors=doc.authors if doc else "",
                year=doc.year if doc else None,
                journal=doc.journal if doc else None,
                file_path=file_path,
            ))

        prompt = COMPARE_PROMPT.format(
            focus=focus_text, papers="\n\n---\n\n".join(paper_blocks)
        )
        answer = await self._llm.chat([ChatMessage(role=Role.USER, content=prompt)])

        return ServiceResponse(answer=answer, citations=citations)
