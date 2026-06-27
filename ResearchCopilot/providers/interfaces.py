from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from models.message import ChatMessage


class BaseLLMProvider(ABC):
    """LLM inference interface — provider-agnostic."""

    @abstractmethod
    async def chat(self, messages: list[ChatMessage], **kwargs) -> str:
        """Send messages and return the complete response."""
        ...

    @abstractmethod
    async def stream(self, messages: list[ChatMessage], **kwargs) -> AsyncIterator[str]:
        """Send messages and yield response tokens as they arrive."""
        ...


class BaseEmbeddingProvider(ABC):
    """Embedding interface — provider-agnostic."""

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Convert a list of texts to embedding vectors."""
        ...
