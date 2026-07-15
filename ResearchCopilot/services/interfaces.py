from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from models.message import ChatMessage
from services.models import ServiceResponse, SearchResponse, ClassifyResult


class BaseChatService(ABC):
    @abstractmethod
    async def ask(self, question: str,
                  conversation_history: list[ChatMessage] | None = None,
                  top_k: int = 10,
                  collections: list[str] | None = None) -> ServiceResponse: ...
    @abstractmethod
    async def ask_stream(self, question: str,
                         conversation_history: list[ChatMessage] | None = None,
                         top_k: int = 10,
                         collections: list[str] | None = None) -> AsyncIterator[str]: ...


class BaseSearchService(ABC):
    @abstractmethod
    async def search(self, query: str, top_k: int = 20,
                     document_type: str | None = None,
                     collections: list[str] | None = None) -> SearchResponse: ...


class BaseSummarizeService(ABC):
    @abstractmethod
    async def summarize(self, document_id: str,
                        focus: str | None = None) -> ServiceResponse: ...
    @abstractmethod
    async def compare(self, document_ids: list[str],
                      focus: str | None = None) -> ServiceResponse: ...


class BaseClassifierService(ABC):
    @abstractmethod
    async def classify_single(self, document_id: str) -> ClassifyResult: ...
    @abstractmethod
    async def classify_batch(self, document_ids: list[str]) -> list[ClassifyResult]: ...
