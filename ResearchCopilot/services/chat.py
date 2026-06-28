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
    ):
        self._llm = llm
        self._embedder = embedder
        self._retriever = retriever

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

        # 5. Build citations from retrieved sources
        citations = [
            Citation(
                document_id=chunk.document_id,
                title=chunk.metadata.get("title", "Unknown"),
                authors=chunk.metadata.get("authors", ""),
                year=chunk.metadata.get("year"),
                chunk_id=chunk.chunk_id,
                snippet=chunk.content[:200],
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
