from models.message import ChatMessage, Role
from providers.interfaces import BaseLLMProvider, BaseEmbeddingProvider
from retrieval.interfaces import BaseHybridRetriever
from services.interfaces import BaseChatService
from services.models import ServiceResponse, Citation


SYSTEM_PROMPT = """You are a research assistant specializing in computational chemistry, materials science, and catalysis.

Answer the user's question based on the provided context from scientific literature.

Guidelines:
- Answer accurately based on the context provided
- Cite specific papers when you use information from them: use [1], [2], etc.
- If the context doesn't contain enough information, say so honestly
- Be concise but thorough
- Use scientific terminology appropriate for the domain"""


class ChatService(BaseChatService):
    def __init__(
        self,
        llm: BaseLLMProvider,
        embedder: BaseEmbeddingProvider,
        retriever: BaseHybridRetriever,
        meta_store=None,
        file_store=None,
    ):
        self._llm = llm
        self._embedder = embedder
        self._retriever = retriever
        self._meta_store = meta_store
        self._file_store = file_store

    async def ask(
        self, question: str,
        conversation_history: list[ChatMessage] | None = None,
        top_k: int = 10,
    ) -> ServiceResponse:
        # 1. Embed the question
        embeddings = await self._embedder.embed([question])
        query_embedding = embeddings[0]

        # 2. Retrieve relevant chunks
        retrieved = await self._retriever.search(question, query_embedding, top_k=top_k)

        # 3. Build prompt with context
        context_parts = []
        for i, chunk in enumerate(retrieved):
            src = f"[{i+1}] {chunk.metadata.get('title', 'Unknown')}"
            if chunk.metadata.get("authors"):
                src += f" ({chunk.metadata['authors']}"
                if chunk.metadata.get("year"):
                    src += f", {chunk.metadata['year']}"
                src += ")"
            context_parts.append(f"{src}:\n{chunk.content}")

        context_text = "\n\n".join(context_parts)

        messages = [
            ChatMessage(role=Role.SYSTEM, content=SYSTEM_PROMPT),
            ChatMessage(role=Role.USER, content=f"Context:\n\n{context_text}\n\nQuestion: {question}"),
        ]
        if conversation_history:
            messages = [messages[0]] + conversation_history + [messages[1]]

        # 4. LLM inference
        answer = await self._llm.chat(messages)

        # 5. Resolve file paths for citations from meta_store
        file_paths: dict[str, str | None] = {}
        if self._meta_store and self._file_store:
            for chunk in retrieved:
                doc_id = chunk.document_id
                if doc_id not in file_paths:
                    doc = await self._meta_store.get_document(doc_id)
                    if doc and doc.file_path:
                        abs_path = self._file_store.get_path(doc.file_path)
                        file_paths[doc_id] = str(abs_path)
                    else:
                        file_paths[doc_id] = None

        # 6. Build citations from retrieved sources
        citations = [
            Citation(
                document_id=chunk.document_id,
                title=chunk.metadata.get("title", "Unknown"),
                authors=chunk.metadata.get("authors", ""),
                year=chunk.metadata.get("year"),
                journal=chunk.metadata.get("journal"),
                chunk_id=chunk.chunk_id,
                snippet=chunk.content[:200],
                page_number=chunk.metadata.get("page_number"),
                file_path=file_paths.get(chunk.document_id),
            )
            for chunk in retrieved
        ]

        return ServiceResponse(answer=answer, citations=citations, sources=retrieved)

    async def ask_stream(
        self, question: str,
        conversation_history: list[ChatMessage] | None = None,
        top_k: int = 10,
    ):
        embeddings = await self._embedder.embed([question])
        query_embedding = embeddings[0]
        retrieved = await self._retriever.search(question, query_embedding, top_k=top_k)

        context_parts = []
        for i, chunk in enumerate(retrieved):
            src = f"[{i+1}] {chunk.metadata.get('title', 'Unknown')}"
            context_parts.append(f"{src}:\n{chunk.content}")
        context_text = "\n\n".join(context_parts)

        messages = [
            ChatMessage(role=Role.SYSTEM, content=SYSTEM_PROMPT),
            ChatMessage(role=Role.USER, content=f"Context:\n\n{context_text}\n\nQuestion: {question}"),
        ]
        if conversation_history:
            messages = [messages[0]] + conversation_history + [messages[1]]

        async for token in self._llm.stream(messages):
            yield token
