# Phase 1: Config + AI Providers + Storage — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the bottom three layers of ResearchCopilot — Config, AI Providers, and Storage — as the foundation for all subsequent phases.

**Architecture:** All modules follow Interface First — every concrete class implements an ABC defined in an `interfaces.py`. Provider layer abstracts LLM and Embedding behind minimal interfaces. Storage layer splits into FileStore (filesystem), MetadataStore (SQLite + FTS5), and VectorStore (ChromaDB).

**Tech Stack:** Python 3.12+, openai SDK, chromadb, PyMuPDF (install only, not used yet), pydantic, PyYAML, python-dotenv, pytest, pytest-asyncio

## Global Constraints

- Python >= 3.12
- All API keys loaded from `.env`, never hardcoded in config classes
- Async/await for all I/O operations (Storage, Providers)
- Interface First: every concrete class implements an abstract base class
- Keep Interfaces Minimal: each ABC has ≤4 abstract methods
- 100% of public methods covered by unit tests
- Commit after each task

---

### Task 1: Project Setup & Dependencies

**Files:**
- Modify: `requirements.txt`
- Create: `.env.template`

**Interfaces:**
- Produces: `pip install -r requirements.txt` succeeds, `.env.template` available

- [ ] **Step 1: Write requirements.txt**

```text
# Core
python-dotenv>=1.0.0
pyyaml>=6.0
pydantic>=2.0.0

# AI Providers
openai>=1.0.0

# Storage
chromadb>=0.5.0
aisqlite>=0.20.0

# PDF (Phase 2, install now)
PyMuPDF>=1.23.0

# CLI (Phase 3, install now)
rich>=13.0.0
prompt-toolkit>=3.0.0
click>=8.0.0

# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
```

- [ ] **Step 2: Create .env.template**

```bash
# ResearchCopilot Environment Variables
# Copy this file to .env and fill in your values

# LLM Provider (DeepSeek via OpenAI-compatible API)
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-v4-pro
LLM_BASE_URL=https://api.deepseek.com/anthropic
LLM_API_KEY=sk-your-key-here

# Embedding Provider
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_BASE_URL=
EMBEDDING_API_KEY=sk-your-key-here
EMBEDDING_DIMENSION=1536

# Storage
CHROMA_PERSIST_DIR=./data/chroma
SQLITE_PATH=./data/research_copilot.db
FILE_STORE_ROOT=./data
```

- [ ] **Step 3: Verify .gitignore covers .env**

Run: `grep "\.env" .gitignore`
Expected: `.env` and `.env.local` are listed

- [ ] **Step 4: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: All packages install without errors

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .env.template
git commit -m "chore: add project dependencies and .env.template"
```

---

### Task 2: Config Models & Settings Loader

**Files:**
- Create: `config/__init__.py`
- Create: `config/model.py`
- Create: `config/loader.py`
- Create: `config/settings.yaml`
- Create: `tests/config/__init__.py`
- Create: `tests/config/test_config.py`

**Interfaces:**
- Produces: `LLMConfig`, `EmbeddingConfig`, `ChunkConfig`, `StorageConfig` dataclasses
- Produces: `load_config() -> (LLMConfig, EmbeddingConfig, ChunkConfig, StorageConfig)`

- [ ] **Step 1: Write config models**

`config/model.py`:
```python
from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    provider: str
    model: str
    base_url: str | None = None
    temperature: float = 0.1
    max_tokens: int = 4096


@dataclass
class EmbeddingConfig:
    provider: str
    model: str
    base_url: str | None = None
    dimension: int = 1536


@dataclass
class ChunkConfig:
    chunk_size: int = 1024
    chunk_overlap: int = 128


@dataclass
class StorageConfig:
    chroma_persist_dir: str = "./data/chroma"
    sqlite_path: str = "./data/research_copilot.db"
    file_store_root: str = "./data"
```

`config/__init__.py`:
```python
from config.model import LLMConfig, EmbeddingConfig, ChunkConfig, StorageConfig

__all__ = ["LLMConfig", "EmbeddingConfig", "ChunkConfig", "StorageConfig"]
```

- [ ] **Step 2: Write failing test for load_config**

`tests/config/test_config.py`:
```python
import pytest
from config.loader import load_config
from config.model import LLMConfig, EmbeddingConfig, ChunkConfig, StorageConfig


@pytest.mark.asyncio
async def test_load_config_defaults():
    """load_config should return config objects with values from .env or defaults."""
    llm, embedding, chunk, storage = load_config()

    assert isinstance(llm, LLMConfig)
    assert isinstance(embedding, EmbeddingConfig)
    assert isinstance(chunk, ChunkConfig)
    assert isinstance(storage, StorageConfig)

    assert chunk.chunk_size == 1024
    assert chunk.chunk_overlap == 128
    assert embedding.dimension == 1536


@pytest.mark.asyncio
async def test_load_config_reads_env(monkeypatch):
    """load_config should read values from environment variables."""
    monkeypatch.setenv("LLM_PROVIDER", "test_provider")
    monkeypatch.setenv("LLM_MODEL", "test_model")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "test_emb")
    monkeypatch.setenv("CHROMA_PERSIST_DIR", "./test_chroma")
    monkeypatch.setenv("SQLITE_PATH", "./test.db")

    llm, embedding, chunk, storage = load_config()

    assert llm.provider == "test_provider"
    assert llm.model == "test_model"
    assert embedding.provider == "test_emb"
    assert storage.chroma_persist_dir == "./test_chroma"
    assert storage.sqlite_path == "./test.db"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/config/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'config.loader'`

- [ ] **Step 4: Write config loader**

`config/loader.py`:
```python
import os
from dotenv import load_dotenv
from config.model import LLMConfig, EmbeddingConfig, ChunkConfig, StorageConfig


def load_config():
    load_dotenv()

    llm = LLMConfig(
        provider=os.getenv("LLM_PROVIDER", "openai"),
        model=os.getenv("LLM_MODEL", "gpt-4o"),
        base_url=os.getenv("LLM_BASE_URL") or None,
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.1")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
    )

    embedding = EmbeddingConfig(
        provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
        model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"),
        base_url=os.getenv("EMBEDDING_BASE_URL") or None,
        dimension=int(os.getenv("EMBEDDING_DIMENSION", "1536")),
    )

    chunk = ChunkConfig(
        chunk_size=int(os.getenv("CHUNK_SIZE", "1024")),
        chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "128")),
    )

    storage = StorageConfig(
        chroma_persist_dir=os.getenv("CHROMA_PERSIST_DIR", "./data/chroma"),
        sqlite_path=os.getenv("SQLITE_PATH", "./data/research_copilot.db"),
        file_store_root=os.getenv("FILE_STORE_ROOT", "./data"),
    )

    return llm, embedding, chunk, storage
```

Create `config/settings.yaml`:
```yaml
# ResearchCopilot Settings
# Sensitive values (API keys, tokens) go in .env, not here.

llm:
  temperature: 0.1
  max_tokens: 4096

chunk:
  chunk_size: 1024
  chunk_overlap: 128

embedding:
  dimension: 1536
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/config/test_config.py -v`
Expected: 2 PASS

- [ ] **Step 6: Commit**

```bash
git add config/__init__.py config/model.py config/loader.py config/settings.yaml tests/config/
git commit -m "feat: add config models and env-based loader"
```

---

### Task 3: ChatMessage Model

**Files:**
- Create: `models/__init__.py`
- Create: `models/message.py`
- Create: `tests/models/__init__.py`
- Create: `tests/models/test_message.py`

**Interfaces:**
- Produces: `Role` enum, `ChatMessage` dataclass

- [ ] **Step 1: Write ChatMessage model**

`models/message.py`:
```python
from dataclasses import dataclass, field
from enum import Enum


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class ChatMessage:
    role: Role
    content: str
    metadata: dict = field(default_factory=dict)
```

`models/__init__.py`:
```python
from models.message import Role, ChatMessage

__all__ = ["Role", "ChatMessage"]
```

- [ ] **Step 2: Write tests**

`tests/models/test_message.py`:
```python
from models.message import Role, ChatMessage


def test_role_enum_values():
    assert Role.SYSTEM == "system"
    assert Role.USER == "user"
    assert Role.ASSISTANT == "assistant"


def test_chatmessage_creation():
    msg = ChatMessage(role=Role.USER, content="Hello")
    assert msg.role == Role.USER
    assert msg.content == "Hello"
    assert msg.metadata == {}


def test_chatmessage_with_metadata():
    msg = ChatMessage(
        role=Role.ASSISTANT,
        content="The answer is 42.",
        metadata={"citations": ["doc_1"]},
    )
    assert msg.metadata["citations"] == ["doc_1"]


def test_chatmessage_equality():
    a = ChatMessage(role=Role.USER, content="Hi")
    b = ChatMessage(role=Role.USER, content="Hi")
    assert a == b
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/models/test_message.py -v`
Expected: 4 PASS

- [ ] **Step 4: Commit**

```bash
git add models/ tests/models/
git commit -m "feat: add ChatMessage and Role models"
```

---

### Task 4: AI Provider Interfaces

**Files:**
- Create: `providers/__init__.py`
- Create: `providers/interfaces.py`
- Create: `providers/llm/__init__.py`
- Create: `providers/embedding/__init__.py`
- Create: `tests/providers/__init__.py`
- Create: `tests/providers/test_interfaces.py`

**Interfaces:**
- Produces: `BaseLLMProvider` (ABC with `chat` and `stream`)
- Produces: `BaseEmbeddingProvider` (ABC with `embed`)

- [ ] **Step 1: Write provider interfaces**

`providers/interfaces.py`:
```python
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
```

`providers/__init__.py`:
```python
from providers.interfaces import BaseLLMProvider, BaseEmbeddingProvider

__all__ = ["BaseLLMProvider", "BaseEmbeddingProvider"]
```

- [ ] **Step 2: Write interface contracts test**

`tests/providers/test_interfaces.py`:
```python
import pytest
from abc import ABC
from providers.interfaces import BaseLLMProvider, BaseEmbeddingProvider


def test_base_llm_provider_is_abstract():
    assert issubclass(BaseLLMProvider, ABC)
    with pytest.raises(TypeError):
        BaseLLMProvider()  # cannot instantiate ABC


def test_base_llm_provider_declares_chat_and_stream():
    assert hasattr(BaseLLMProvider, "chat")
    assert hasattr(BaseLLMProvider, "stream")


def test_base_embedding_provider_is_abstract():
    assert issubclass(BaseEmbeddingProvider, ABC)
    with pytest.raises(TypeError):
        BaseEmbeddingProvider()


def test_base_embedding_provider_declares_embed():
    assert hasattr(BaseEmbeddingProvider, "embed")


def test_minimal_implementation():
    """Verify a subclass with all methods instantiable."""

    class FakeLLM(BaseLLMProvider):
        async def chat(self, messages, **kwargs):
            return "ok"

        async def stream(self, messages, **kwargs):
            yield "ok"

    class FakeEmbed(BaseEmbeddingProvider):
        async def embed(self, texts):
            return [[0.0] * 3] * len(texts)

    llm = FakeLLM()
    embed = FakeEmbed()
    assert llm is not None
    assert embed is not None
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/providers/test_interfaces.py -v`
Expected: 5 PASS

- [ ] **Step 4: Commit**

```bash
git add providers/ tests/providers/
git commit -m "feat: add BaseLLMProvider and BaseEmbeddingProvider interfaces"
```

---

### Task 5: OpenAI-Compatible LLM Provider

**Files:**
- Create: `providers/llm/openai.py`
- Create: `tests/providers/llm/__init__.py`
- Create: `tests/providers/llm/test_openai.py`

**Interfaces:**
- Consumes: `BaseLLMProvider` from `providers/interfaces.py`
- Consumes: `ChatMessage`, `Role` from `models/message.py`
- Consumes: `LLMConfig` from `config/model.py`
- Produces: `OpenAILLMProvider(BaseLLMProvider)`

- [ ] **Step 1: Write failing test**

`tests/providers/llm/test_openai.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch
from models.message import ChatMessage, Role
from config.model import LLMConfig
from providers.llm.openai import OpenAILLMProvider


@pytest.fixture
def llm_config():
    return LLMConfig(
        provider="deepseek",
        model="deepseek-v4-pro",
        base_url="https://api.deepseek.com/anthropic",
        temperature=0.1,
        max_tokens=4096,
    )


@pytest.fixture
def messages():
    return [
        ChatMessage(role=Role.SYSTEM, content="You are a research assistant."),
        ChatMessage(role=Role.USER, content="What is DFT?"),
    ]


@pytest.mark.asyncio
async def test_chat_returns_string(llm_config, messages):
    mock_response = AsyncMock()
    mock_response.choices = [
        AsyncMock(message=AsyncMock(content="DFT stands for Density Functional Theory."))
    ]

    with patch("openai.resources.chat.completions.AsyncCompletions.create", return_value=mock_response):
        provider = OpenAILLMProvider(llm_config)
        result = await provider.chat(messages)

    assert isinstance(result, str)
    assert "Density Functional Theory" in result


@pytest.mark.asyncio
async def test_chat_converts_chatmessage_to_openai_format(llm_config, messages):
    """ChatMessage.role and .content map to OpenAI dict format."""
    captured = []

    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=AsyncMock(content="ok"))]

    async def capture_create(*, messages, model, temperature, max_tokens, **kwargs):
        captured.append({"messages": messages, "model": model})
        return mock_response

    with patch("openai.resources.chat.completions.AsyncCompletions.create", side_effect=capture_create):
        provider = OpenAILLMProvider(llm_config)
        await provider.chat(messages)

    assert len(captured) == 1
    sent_messages = captured[0]["messages"]
    assert sent_messages[0]["role"] == "system"
    assert sent_messages[0]["content"] == "You are a research assistant."
    assert sent_messages[1]["role"] == "user"
    assert captured[0]["model"] == "deepseek-v4-pro"


@pytest.mark.asyncio
async def test_chat_passes_kwargs(llm_config, messages):
    captured = {}

    mock_response = AsyncMock()
    mock_response.choices = [AsyncMock(message=AsyncMock(content="ok"))]

    async def capture(*, messages, model, **kwargs):
        captured.update(kwargs)
        return mock_response

    with patch("openai.resources.chat.completions.AsyncCompletions.create", side_effect=capture):
        provider = OpenAILLMProvider(llm_config)
        await provider.chat(messages, temperature=0.5, max_tokens=100)

    assert captured["temperature"] == 0.5
    assert captured["max_tokens"] == 100


@pytest.mark.asyncio
async def test_stream_yields_tokens(llm_config, messages):
    class FakeStream:
        def __init__(self):
            self._chunks = [
                AsyncMock(choices=[AsyncMock(delta=AsyncMock(content="Hello"))]),
                AsyncMock(choices=[AsyncMock(delta=AsyncMock(content=" world"))]),
                AsyncMock(choices=[AsyncMock(delta=AsyncMock(content=None))]),  # end
            ]
            self._idx = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self._idx >= len(self._chunks):
                raise StopAsyncIteration
            chunk = self._chunks[self._idx]
            self._idx += 1
            return chunk

    with patch("openai.resources.chat.completions.AsyncCompletions.create", return_value=FakeStream()):
        provider = OpenAILLMProvider(llm_config)
        tokens = []
        async for token in provider.stream(messages):
            tokens.append(token)

    assert tokens == ["Hello", " world"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/providers/llm/test_openai.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'providers.llm.openai'`

- [ ] **Step 3: Write OpenAILLMProvider**

`providers/llm/openai.py`:
```python
import openai
from collections.abc import AsyncIterator
from config.model import LLMConfig
from models.message import ChatMessage
from providers.interfaces import BaseLLMProvider


class OpenAILLMProvider(BaseLLMProvider):
    """OpenAI-compatible LLM provider.

    Works with OpenAI, DeepSeek, and any OpenAI-compatible API
    by configuring base_url in LLMConfig.
    """

    def __init__(self, config: LLMConfig):
        self._config = config
        self._client = openai.AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url or None,
        )

    async def chat(self, messages: list[ChatMessage], **kwargs) -> str:
        temperature = kwargs.pop("temperature", self._config.temperature)
        max_tokens = kwargs.pop("max_tokens", self._config.max_tokens)

        response = await self._client.chat.completions.create(
            model=self._config.model,
            messages=self._to_openai_format(messages),
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    async def stream(self, messages: list[ChatMessage], **kwargs) -> AsyncIterator[str]:
        temperature = kwargs.pop("temperature", self._config.temperature)
        max_tokens = kwargs.pop("max_tokens", self._config.max_tokens)

        stream = await self._client.chat.completions.create(
            model=self._config.model,
            messages=self._to_openai_format(messages),
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    def _to_openai_format(self, messages: list[ChatMessage]) -> list[dict]:
        return [
            {"role": msg.role.value, "content": msg.content}
            for msg in messages
        ]
```

Wait — I need to add `api_key` to the config. But the spec says API key comes from .env. So the provider should read it from .env at construction time, or we add it to the config as a non-dataclass field. Let me update: the provider reads the API key directly from environment.

Actually, looking at the spec again: "API keys are loaded from .env, not from config classes." The simplest approach: `OpenAILLMProvider.__init__` reads `os.getenv("LLM_API_KEY")` directly. Let me fix the implementation.

- [ ] **Step 3 (revised): Write OpenAILLMProvider**

`providers/llm/openai.py`:
```python
import os
import openai
from collections.abc import AsyncIterator
from config.model import LLMConfig
from models.message import ChatMessage
from providers.interfaces import BaseLLMProvider


class OpenAILLMProvider(BaseLLMProvider):
    """OpenAI-compatible LLM provider.

    Reads API key from LLM_API_KEY environment variable.
    Compatible with OpenAI, DeepSeek, and any OpenAI-compatible API
    by configuring base_url in LLMConfig.
    """

    def __init__(self, config: LLMConfig):
        self._config = config
        api_key = os.getenv("LLM_API_KEY", "")
        if not api_key:
            raise ValueError("LLM_API_KEY environment variable is not set")
        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=config.base_url or None,
        )

    async def chat(self, messages: list[ChatMessage], **kwargs) -> str:
        temperature = kwargs.pop("temperature", self._config.temperature)
        max_tokens = kwargs.pop("max_tokens", self._config.max_tokens)
        response = await self._client.chat.completions.create(
            model=self._config.model,
            messages=self._to_openai_format(messages),
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return response.choices[0].message.content or ""

    async def stream(self, messages: list[ChatMessage], **kwargs) -> AsyncIterator[str]:
        temperature = kwargs.pop("temperature", self._config.temperature)
        max_tokens = kwargs.pop("max_tokens", self._config.max_tokens)
        stream = await self._client.chat.completions.create(
            model=self._config.model,
            messages=self._to_openai_format(messages),
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
            **kwargs,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content

    def _to_openai_format(self, messages: list[ChatMessage]) -> list[dict]:
        return [{"role": msg.role.value, "content": msg.content} for msg in messages]
```

Actually wait, the tests above use `llm_config` without an `api_key` field (since we removed it from the dataclass). The provider reads the key from the environment. The tests need to mock `os.getenv` or set the env var. Let me update the tests to set `LLM_API_KEY` via monkeypatch.

- [ ] **Step 4: Run tests**

Run: `LLM_API_KEY=test-key pytest tests/providers/llm/test_openai.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add providers/llm/openai.py tests/providers/llm/
git commit -m "feat: add OpenAILLMProvider (OpenAI-compatible)"
```

---

### Task 6: OpenAI Embedding Provider

**Files:**
- Create: `providers/embedding/openai.py`
- Create: `tests/providers/embedding/__init__.py`
- Create: `tests/providers/embedding/test_openai.py`

**Interfaces:**
- Consumes: `BaseEmbeddingProvider` from `providers/interfaces.py`
- Consumes: `EmbeddingConfig` from `config/model.py`
- Produces: `OpenAIEmbeddingProvider(BaseEmbeddingProvider)`

- [ ] **Step 1: Write failing test**

`tests/providers/embedding/test_openai.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch
from config.model import EmbeddingConfig
from providers.embedding.openai import OpenAIEmbeddingProvider


@pytest.fixture
def emb_config():
    return EmbeddingConfig(
        provider="openai",
        model="text-embedding-3-small",
        dimension=1536,
    )


@pytest.mark.asyncio
async def test_embed_returns_correct_shape(emb_config):
    mock_embeddings = [
        AsyncMock(embedding=[0.1] * 1536),
        AsyncMock(embedding=[0.2] * 1536),
    ]
    mock_response = AsyncMock(data=mock_embeddings)

    with patch("openai.resources.embeddings.AsyncEmbeddings.create", return_value=mock_response):
        provider = OpenAIEmbeddingProvider(emb_config)
        result = await provider.embed(["text one", "text two"])

    assert len(result) == 2
    assert len(result[0]) == 1536
    assert len(result[1]) == 1536


@pytest.mark.asyncio
async def test_embed_single_text(emb_config):
    mock_response = AsyncMock(data=[AsyncMock(embedding=[0.5] * 1536)])

    with patch("openai.resources.embeddings.AsyncEmbeddings.create", return_value=mock_response):
        provider = OpenAIEmbeddingProvider(emb_config)
        result = await provider.embed(["hello"])

    assert len(result) == 1
    assert result[0] == [0.5] * 1536


@pytest.mark.asyncio
async def test_embed_empty_list(emb_config):
    provider = OpenAIEmbeddingProvider(emb_config)
    result = await provider.embed([])
    assert result == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/providers/embedding/test_openai.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write OpenAIEmbeddingProvider**

`providers/embedding/openai.py`:
```python
import os
import openai
from config.model import EmbeddingConfig
from providers.interfaces import BaseEmbeddingProvider


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    """OpenAI-compatible embedding provider.

    Reads API key from EMBEDDING_API_KEY environment variable.
    """

    def __init__(self, config: EmbeddingConfig):
        self._config = config
        api_key = os.getenv("EMBEDDING_API_KEY", "")
        if not api_key:
            raise ValueError("EMBEDDING_API_KEY environment variable is not set")
        self._client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=config.base_url or None,
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        response = await self._client.embeddings.create(
            model=self._config.model,
            input=texts,
        )
        return [item.embedding for item in response.data]
```

- [ ] **Step 4: Run tests**

Run: `EMBEDDING_API_KEY=test-key pytest tests/providers/embedding/test_openai.py -v`
Expected: 3 PASS

- [ ] **Step 5: Commit**

```bash
git add providers/embedding/openai.py tests/providers/embedding/
git commit -m "feat: add OpenAIEmbeddingProvider"
```

---

### Task 7: Storage Data Models

**Files:**
- Create: `storage/__init__.py`
- Create: `storage/models.py`
- Create: `tests/storage/__init__.py`
- Create: `tests/storage/test_models.py`

**Interfaces:**
- Produces: `DocumentRecord`, `ChunkRecord`, `VectorDocument`, `RetrievalResult`

- [ ] **Step 1: Write storage models**

`storage/models.py`:
```python
from dataclasses import dataclass, field


@dataclass
class DocumentRecord:
    """Universal document metadata — shared across literature, experiment, dft, note."""
    id: str
    document_type: str             # "literature" | "experiment" | "dft" | "note"
    title: str
    authors: str | None = None
    year: int | None = None
    journal: str | None = None
    doi: str | None = None
    keywords: str | None = None
    abstract: str | None = None
    source_type: str = "pdf"       # "pdf" | "bibtex" | "doi" | "markdown"
    file_path: str | None = None
    extra: dict | None = None      # domain-specific extension field
    created_at: str = ""


@dataclass
class ChunkRecord:
    """A text chunk linked to a document and a ChromaDB vector."""
    id: str
    document_id: str
    chunk_index: int
    content: str
    chroma_id: str
    token_count: int = 0
    page_number: int | None = None
    start_offset: int | None = None
    end_offset: int | None = None


@dataclass
class VectorDocument:
    """A document ready for insertion into the vector store."""
    id: str
    embedding: list[float]
    content: str
    metadata: dict = field(default_factory=dict)


@dataclass
class RetrievalResult:
    """A single hit from the vector store."""
    id: str
    content: str
    metadata: dict
    score: float
```

`storage/__init__.py`:
```python
from storage.models import DocumentRecord, ChunkRecord, VectorDocument, RetrievalResult

__all__ = ["DocumentRecord", "ChunkRecord", "VectorDocument", "RetrievalResult"]
```

- [ ] **Step 2: Write tests**

`tests/storage/test_models.py`:
```python
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
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/storage/test_models.py -v`
Expected: 5 PASS

- [ ] **Step 4: Commit**

```bash
git add storage/__init__.py storage/models.py tests/storage/
git commit -m "feat: add storage data models (DocumentRecord, ChunkRecord, VectorDocument, RetrievalResult)"
```

---

### Task 8: Storage Interfaces

**Files:**
- Modify: `storage/__init__.py`
- Create: `storage/interfaces.py`
- Create: `tests/storage/test_interfaces.py`

**Interfaces:**
- Produces: `BaseFileStore`, `BaseMetadataStore`, `BaseVectorStore`

- [ ] **Step 1: Write storage interfaces**

`storage/interfaces.py`:
```python
from abc import ABC, abstractmethod
from pathlib import Path
from storage.models import DocumentRecord, ChunkRecord, VectorDocument, RetrievalResult


class BaseFileStore(ABC):
    """Raw file storage — save, retrieve, list, delete by category."""

    @abstractmethod
    def save(self, source: Path, category: str) -> str:
        """Copy file into file_store/<category>/, return relative path."""
        ...

    @abstractmethod
    def get_path(self, relative_path: str) -> Path:
        """Resolve a relative path to an absolute path."""
        ...

    @abstractmethod
    def list(self, category: str) -> list[str]:
        """List all file paths under a category."""
        ...

    @abstractmethod
    def delete(self, relative_path: str) -> None:
        """Delete a file from the store."""
        ...


class BaseMetadataStore(ABC):
    """Document and chunk metadata storage — SQLite-backed."""

    @abstractmethod
    async def insert_document(self, doc: DocumentRecord) -> None:
        """Insert a new document record."""
        ...

    @abstractmethod
    async def get_document(self, document_id: str) -> DocumentRecord | None:
        """Retrieve a document by ID."""
        ...

    @abstractmethod
    async def get_document_by_doi(self, doi: str) -> DocumentRecord | None:
        """Find a document by DOI."""
        ...

    @abstractmethod
    async def list_documents(
        self,
        document_type: str | None = None,
        year: int | None = None,
        limit: int = 50,
    ) -> list[DocumentRecord]:
        """List documents with optional filters."""
        ...

    @abstractmethod
    async def insert_chunks(self, chunks: list[ChunkRecord]) -> None:
        """Insert chunk records in batch."""
        ...

    @abstractmethod
    async def get_chunks_by_document(self, document_id: str) -> list[ChunkRecord]:
        """Get all chunks for a document, ordered by chunk_index."""
        ...

    @abstractmethod
    async def get_chunk_by_chroma_id(self, chroma_id: str) -> ChunkRecord | None:
        """Find a chunk by its ChromaDB vector ID."""
        ...


class BaseVectorStore(ABC):
    """Vector storage and similarity search — ChromaDB-backed."""

    @abstractmethod
    async def add(self, docs: list[VectorDocument]) -> None:
        """Add documents with embeddings to the vector store."""
        ...

    @abstractmethod
    async def query(
        self,
        embedding: list[float],
        top_k: int = 10,
        where: dict | None = None,
    ) -> list[RetrievalResult]:
        """Query by embedding vector with optional metadata filter."""
        ...

    @abstractmethod
    async def delete(self, ids: list[str]) -> None:
        """Delete vectors by ID."""
        ...

    @abstractmethod
    async def count(self) -> int:
        """Return the total number of vectors in the store."""
        ...
```

Update `storage/__init__.py`:
```python
from storage.models import DocumentRecord, ChunkRecord, VectorDocument, RetrievalResult
from storage.interfaces import BaseFileStore, BaseMetadataStore, BaseVectorStore

__all__ = [
    "DocumentRecord",
    "ChunkRecord",
    "VectorDocument",
    "RetrievalResult",
    "BaseFileStore",
    "BaseMetadataStore",
    "BaseVectorStore",
]
```

- [ ] **Step 2: Write interface tests**

`tests/storage/test_interfaces.py`:
```python
import pytest
from pathlib import Path
from storage.interfaces import BaseFileStore, BaseMetadataStore, BaseVectorStore
from storage.models import DocumentRecord, ChunkRecord


class FakeFileStore(BaseFileStore):
    def save(self, source, category):
        return f"{category}/test.pdf"
    def get_path(self, relative_path):
        return Path("/fake") / relative_path
    def list(self, category):
        return [f"{category}/test.pdf"]
    def delete(self, relative_path):
        pass


class FakeMetadataStore(BaseMetadataStore):
    async def insert_document(self, doc): pass
    async def get_document(self, document_id): return None
    async def get_document_by_doi(self, doi): return None
    async def list_documents(self, document_type=None, year=None, limit=50): return []
    async def insert_chunks(self, chunks): pass
    async def get_chunks_by_document(self, document_id): return []
    async def get_chunk_by_chroma_id(self, chroma_id): return None


class FakeVectorStore(BaseVectorStore):
    async def add(self, docs): pass
    async def query(self, embedding, top_k=10, where=None): return []
    async def delete(self, ids): pass
    async def count(self): return 0


def test_file_store_instantiable():
    store = FakeFileStore()
    assert store.save(Path("test.pdf"), "papers") == "papers/test.pdf"
    assert str(store.get_path("papers/test.pdf")).endswith("papers/test.pdf")


def test_metadata_store_is_abstract():
    with pytest.raises(TypeError):
        BaseMetadataStore()


def test_vector_store_is_abstract():
    with pytest.raises(TypeError):
        BaseVectorStore()


@pytest.mark.asyncio
async def test_metadata_store_minimal_impl():
    store = FakeMetadataStore()
    assert await store.get_document("any") is None
    assert await store.list_documents() == []


@pytest.mark.asyncio
async def test_vector_store_minimal_impl():
    store = FakeVectorStore()
    assert await store.count() == 0
    assert await store.query([0.1]) == []
```

- [ ] **Step 3: Run tests**

Run: `pytest tests/storage/test_interfaces.py -v`
Expected: 5 PASS

- [ ] **Step 4: Commit**

```bash
git add storage/__init__.py storage/interfaces.py tests/storage/test_interfaces.py
git commit -m "feat: add BaseFileStore, BaseMetadataStore, BaseVectorStore interfaces"
```

---

### Task 9: LocalFileStore Implementation

**Files:**
- Create: `storage/file_store.py`
- Create: `tests/storage/test_file_store.py`

**Interfaces:**
- Consumes: `BaseFileStore` from `storage/interfaces.py`
- Consumes: `StorageConfig` from `config/model.py`
- Produces: `LocalFileStore(BaseFileStore)`

- [ ] **Step 1: Write failing test**

`tests/storage/test_file_store.py`:
```python
import pytest
import tempfile
import shutil
from pathlib import Path
from config.model import StorageConfig
from storage.file_store import LocalFileStore


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d)


@pytest.fixture
def config(temp_dir):
    return StorageConfig(file_store_root=str(temp_dir))


@pytest.fixture
def store(config):
    return LocalFileStore(config)


def test_save_copies_file(store, temp_dir):
    """save() should copy the source file into the store under the right category."""
    src = temp_dir / "source.txt"
    src.write_text("hello world")

    rel_path = store.save(src, "papers")
    assert rel_path.startswith("papers/")
    assert Path(temp_dir / rel_path).exists()
    assert Path(temp_dir / rel_path).read_text() == "hello world"


def test_save_preserves_extension(store, temp_dir):
    src = temp_dir / "paper.pdf"
    src.write_text("pdf content")
    rel_path = store.save(src, "papers")
    assert rel_path.endswith(".pdf")


def test_save_avoids_name_collision(store, temp_dir):
    """If a file with the same name exists, save should not overwrite."""
    src1 = temp_dir / "doc.pdf"
    src1.write_text("version 1")
    src2 = temp_dir / "doc.pdf"  # same name, different temp location
    # We simulate this: create a second source file
    alt_dir = temp_dir / "alt"
    alt_dir.mkdir()
    src2_alt = alt_dir / "doc.pdf"
    src2_alt.write_text("version 2")

    p1 = store.save(src1, "papers")
    p2 = store.save(src2_alt, "papers")

    assert p1 != p2
    assert Path(temp_dir / p1).read_text() == "version 1"
    assert Path(temp_dir / p2).read_text() == "version 2"


def test_get_path_returns_absolute(store, temp_dir):
    src = temp_dir / "test.txt"
    src.write_text("data")
    rel = store.save(src, "notes")

    abs_path = store.get_path(rel)
    assert abs_path.is_absolute()
    assert abs_path.exists()


def test_list_returns_files_in_category(store, temp_dir):
    src = temp_dir / "a.txt"
    src.write_text("a")
    store.save(src, "papers")

    files = store.list("papers")
    assert len(files) == 1
    assert files[0].startswith("papers/")


def test_list_empty_category(store):
    assert store.list("nonexistent") == []


def test_delete_removes_file(store, temp_dir):
    src = temp_dir / "to_delete.txt"
    src.write_text("delete me")
    rel = store.save(src, "papers")

    assert Path(temp_dir / rel).exists()
    store.delete(rel)
    assert not Path(temp_dir / rel).exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/storage/test_file_store.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write LocalFileStore**

`storage/file_store.py`:
```python
import shutil
import uuid
from pathlib import Path
from config.model import StorageConfig
from storage.interfaces import BaseFileStore


class LocalFileStore(BaseFileStore):
    """Filesystem-backed file store."""

    def __init__(self, config: StorageConfig):
        self._root = Path(config.file_store_root).resolve()
        self._root.mkdir(parents=True, exist_ok=True)

    def save(self, source: Path, category: str) -> str:
        category_dir = self._root / category
        category_dir.mkdir(parents=True, exist_ok=True)

        stem = source.stem
        suffix = source.suffix
        unique_name = f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"
        dest = category_dir / unique_name

        shutil.copy2(source, dest)
        return str(dest.relative_to(self._root))

    def get_path(self, relative_path: str) -> Path:
        return self._root / relative_path

    def list(self, category: str) -> list[str]:
        category_dir = self._root / category
        if not category_dir.exists():
            return []
        return [
            str(p.relative_to(self._root))
            for p in category_dir.iterdir()
            if p.is_file()
        ]

    def delete(self, relative_path: str) -> None:
        target = self._root / relative_path
        if target.exists():
            target.unlink()
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/storage/test_file_store.py -v`
Expected: 7 PASS

- [ ] **Step 5: Commit**

```bash
git add storage/file_store.py tests/storage/test_file_store.py
git commit -m "feat: add LocalFileStore implementation"
```

---

### Task 10: SQLiteMetadataStore Implementation

**Files:**
- Create: `storage/sqlite_meta.py`
- Create: `tests/storage/test_sqlite_meta.py`

**Interfaces:**
- Consumes: `BaseMetadataStore` from `storage/interfaces.py`
- Consumes: `StorageConfig` from `config/model.py`
- Consumes: `DocumentRecord`, `ChunkRecord` from `storage/models.py`
- Produces: `SQLiteMetadataStore(BaseMetadataStore)`

- [ ] **Step 1: Write failing test**

`tests/storage/test_sqlite_meta.py`:
```python
import pytest
import tempfile
import os
from pathlib import Path
from config.model import StorageConfig
from storage.models import DocumentRecord, ChunkRecord
from storage.sqlite_meta import SQLiteMetadataStore


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def config(db_path):
    return StorageConfig(sqlite_path=db_path)


@pytest.fixture
async def store(config):
    s = SQLiteMetadataStore(config)
    await s.initialize()
    yield s
    await s.close()


@pytest.mark.asyncio
async def test_insert_and_get_document(store):
    doc = DocumentRecord(
        id="doc-1",
        document_type="literature",
        title="Density Functional Theory Basics",
        authors="Kohn W, Sham L",
        year=1965,
        journal="Physical Review",
        doi="10.1103/physrev.140.a1133",
        keywords="DFT, Kohn-Sham",
        source_type="pdf",
        file_path="papers/dft_basics.pdf",
        created_at="2026-06-26",
    )
    await store.insert_document(doc)
    result = await store.get_document("doc-1")
    assert result is not None
    assert result.title == "Density Functional Theory Basics"
    assert result.authors == "Kohn W, Sham L"
    assert result.year == 1965
    assert result.doi == "10.1103/physrev.140.a1133"


@pytest.mark.asyncio
async def test_get_document_not_found(store):
    result = await store.get_document("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_get_document_by_doi(store):
    doc = DocumentRecord(
        id="doc-2", document_type="literature", title="Test",
        doi="10.1000/test",
    )
    await store.insert_document(doc)
    result = await store.get_document_by_doi("10.1000/test")
    assert result is not None
    assert result.id == "doc-2"


@pytest.mark.asyncio
async def test_list_documents_filter_by_type(store):
    await store.insert_document(DocumentRecord(
        id="lit-1", document_type="literature", title="Paper A"))
    await store.insert_document(DocumentRecord(
        id="exp-1", document_type="experiment", title="Experiment A"))

    papers = await store.list_documents(document_type="literature")
    assert len(papers) == 1
    assert papers[0].id == "lit-1"


@pytest.mark.asyncio
async def test_list_documents_filter_by_year(store):
    await store.insert_document(DocumentRecord(
        id="a", document_type="literature", title="Old", year=2000))
    await store.insert_document(DocumentRecord(
        id="b", document_type="literature", title="New", year=2024))

    results = await store.list_documents(year=2024)
    assert len(results) == 1
    assert results[0].id == "b"


@pytest.mark.asyncio
async def test_list_documents_limit(store):
    for i in range(10):
        await store.insert_document(DocumentRecord(
            id=f"doc-{i}", document_type="literature", title=f"Paper {i}"))
    results = await store.list_documents(limit=5)
    assert len(results) == 5


@pytest.mark.asyncio
async def test_insert_and_get_chunks(store):
    await store.insert_document(DocumentRecord(
        id="doc-3", document_type="literature", title="Chunk Test"))
    chunks = [
        ChunkRecord(
            id="c-0", document_id="doc-3", chunk_index=0,
            content="First chunk.", chroma_id="chroma-0", token_count=3),
        ChunkRecord(
            id="c-1", document_id="doc-3", chunk_index=1,
            content="Second chunk.", chroma_id="chroma-1", token_count=3,
            page_number=2, start_offset=100, end_offset=200),
    ]
    await store.insert_chunks(chunks)

    retrieved = await store.get_chunks_by_document("doc-3")
    assert len(retrieved) == 2
    assert retrieved[0].chunk_index == 0
    assert retrieved[1].chunk_index == 1
    assert retrieved[1].page_number == 2


@pytest.mark.asyncio
async def test_get_chunk_by_chroma_id(store):
    await store.insert_document(DocumentRecord(
        id="doc-4", document_type="literature", title="Chroma Lookup"))
    await store.insert_chunks([
        ChunkRecord(id="c-x", document_id="doc-4", chunk_index=0,
                    content="Find me.", chroma_id="chroma-find"),
    ])
    result = await store.get_chunk_by_chroma_id("chroma-find")
    assert result is not None
    assert result.id == "c-x"


@pytest.mark.asyncio
async def test_duplicate_document_id_raises(store):
    doc = DocumentRecord(id="dup", document_type="literature", title="First")
    await store.insert_document(doc)
    with pytest.raises(Exception):
        await store.insert_document(doc)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/storage/test_sqlite_meta.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write SQLiteMetadataStore**

`storage/sqlite_meta.py`:
```python
import aiosqlite
from config.model import StorageConfig
from storage.interfaces import BaseMetadataStore
from storage.models import DocumentRecord, ChunkRecord


class SQLiteMetadataStore(BaseMetadataStore):
    """SQLite-backed metadata store with FTS5 for future keyword search."""

    def __init__(self, config: StorageConfig):
        self._db_path = config.sqlite_path
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self):
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self):
        if self._conn:
            await self._conn.close()

    async def _create_tables(self):
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                document_type TEXT NOT NULL,
                title TEXT NOT NULL,
                authors TEXT,
                year INTEGER,
                journal TEXT,
                doi TEXT UNIQUE,
                keywords TEXT,
                abstract TEXT,
                source_type TEXT DEFAULT 'pdf',
                file_path TEXT,
                extra TEXT,
                created_at TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                chroma_id TEXT NOT NULL,
                token_count INTEGER DEFAULT 0,
                page_number INTEGER,
                start_offset INTEGER,
                end_offset INTEGER,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            );

            CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
            CREATE INDEX IF NOT EXISTS idx_chunks_chroma_id ON chunks(chroma_id);
            CREATE INDEX IF NOT EXISTS idx_documents_type ON documents(document_type);
            CREATE INDEX IF NOT EXISTS idx_documents_year ON documents(year);

            CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
                title, authors, keywords, abstract, content='documents', content_rowid='rowid'
            );
        """)
        await self._conn.commit()

    async def insert_document(self, doc: DocumentRecord) -> None:
        import json
        await self._conn.execute(
            """INSERT INTO documents (id, document_type, title, authors, year,
               journal, doi, keywords, abstract, source_type, file_path,
               extra, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                doc.id, doc.document_type, doc.title, doc.authors,
                doc.year, doc.journal, doc.doi, doc.keywords,
                doc.abstract, doc.source_type, doc.file_path,
                json.dumps(doc.extra) if doc.extra else None,
                doc.created_at,
            ),
        )
        await self._conn.commit()

    async def get_document(self, document_id: str) -> DocumentRecord | None:
        import json
        cursor = await self._conn.execute(
            "SELECT * FROM documents WHERE id = ?", (document_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_document(row)

    async def get_document_by_doi(self, doi: str) -> DocumentRecord | None:
        cursor = await self._conn.execute(
            "SELECT * FROM documents WHERE doi = ?", (doi,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_document(row)

    async def list_documents(
        self,
        document_type: str | None = None,
        year: int | None = None,
        limit: int = 50,
    ) -> list[DocumentRecord]:
        query = "SELECT * FROM documents WHERE 1=1"
        params = []
        if document_type is not None:
            query += " AND document_type = ?"
            params.append(document_type)
        if year is not None:
            query += " AND year = ?"
            params.append(year)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        cursor = await self._conn.execute(query, params)
        rows = await cursor.fetchall()
        return [self._row_to_document(r) for r in rows]

    async def insert_chunks(self, chunks: list[ChunkRecord]) -> None:
        await self._conn.executemany(
            """INSERT INTO chunks (id, document_id, chunk_index, content,
               chroma_id, token_count, page_number, start_offset, end_offset)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    c.id, c.document_id, c.chunk_index, c.content,
                    c.chroma_id, c.token_count, c.page_number,
                    c.start_offset, c.end_offset,
                )
                for c in chunks
            ],
        )
        await self._conn.commit()

    async def get_chunks_by_document(self, document_id: str) -> list[ChunkRecord]:
        cursor = await self._conn.execute(
            "SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index",
            (document_id,),
        )
        rows = await cursor.fetchall()
        return [self._row_to_chunk(r) for r in rows]

    async def get_chunk_by_chroma_id(self, chroma_id: str) -> ChunkRecord | None:
        cursor = await self._conn.execute(
            "SELECT * FROM chunks WHERE chroma_id = ?", (chroma_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return self._row_to_chunk(row)

    def _row_to_document(self, row) -> DocumentRecord:
        import json
        extra = row["extra"]
        return DocumentRecord(
            id=row["id"],
            document_type=row["document_type"],
            title=row["title"],
            authors=row["authors"],
            year=row["year"],
            journal=row["journal"],
            doi=row["doi"],
            keywords=row["keywords"],
            abstract=row["abstract"],
            source_type=row["source_type"],
            file_path=row["file_path"],
            extra=json.loads(extra) if extra else None,
            created_at=row["created_at"],
        )

    def _row_to_chunk(self, row) -> ChunkRecord:
        return ChunkRecord(
            id=row["id"],
            document_id=row["document_id"],
            chunk_index=row["chunk_index"],
            content=row["content"],
            chroma_id=row["chroma_id"],
            token_count=row["token_count"],
            page_number=row["page_number"],
            start_offset=row["start_offset"],
            end_offset=row["end_offset"],
        )
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/storage/test_sqlite_meta.py -v`
Expected: 9 PASS

- [ ] **Step 5: Commit**

```bash
git add storage/sqlite_meta.py tests/storage/test_sqlite_meta.py
git commit -m "feat: add SQLiteMetadataStore with FTS5"
```

---

### Task 11: ChromaVectorStore Implementation

**Files:**
- Create: `storage/chroma_vector.py`
- Create: `tests/storage/test_chroma_vector.py`

**Interfaces:**
- Consumes: `BaseVectorStore` from `storage/interfaces.py`
- Consumes: `StorageConfig` from `config/model.py`
- Consumes: `VectorDocument`, `RetrievalResult` from `storage/models.py`
- Produces: `ChromaVectorStore(BaseVectorStore)`

- [ ] **Step 1: Write failing test**

`tests/storage/test_chroma_vector.py`:
```python
import pytest
import tempfile
import shutil
import os
from pathlib import Path
from config.model import StorageConfig
from storage.models import VectorDocument
from storage.chroma_vector import ChromaVectorStore


@pytest.fixture
def temp_dir():
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def config(temp_dir):
    return StorageConfig(chroma_persist_dir=temp_dir)


@pytest.fixture
async def store(config):
    s = ChromaVectorStore(config)
    await s.initialize()
    yield s
    # No explicit close needed for ChromaDB in-memory/test


@pytest.mark.asyncio
async def test_add_and_count(store):
    assert await store.count() == 0

    docs = [
        VectorDocument(
            id="v-1",
            embedding=[0.1, 0.2, 0.3],
            content="First test document.",
            metadata={"document_id": "doc-1", "title": "Paper A"},
        ),
        VectorDocument(
            id="v-2",
            embedding=[0.4, 0.5, 0.6],
            content="Second test document.",
            metadata={"document_id": "doc-2", "title": "Paper B"},
        ),
    ]
    await store.add(docs)
    assert await store.count() == 2


@pytest.mark.asyncio
async def test_query_returns_results(store):
    await store.add([
        VectorDocument(
            id="qa",
            embedding=[1.0, 0.0, 0.0],
            content="About catalysis.",
            metadata={"document_id": "cat-1"},
        ),
        VectorDocument(
            id="qb",
            embedding=[0.0, 1.0, 0.0],
            content="About electrochemistry.",
            metadata={"document_id": "ec-1"},
        ),
    ])

    results = await store.query([1.0, 0.1, 0.0], top_k=2)
    assert len(results) == 2
    assert results[0].id == "qa"  # closest to query
    assert results[0].score >= results[1].score


@pytest.mark.asyncio
async def test_query_with_metadata_filter(store):
    await store.add([
        VectorDocument(
            id="x",
            embedding=[1.0, 0.0],
            content="Literature paper.",
            metadata={"document_id": "d1", "document_type": "literature"},
        ),
        VectorDocument(
            id="y",
            embedding=[0.9, 0.1],
            content="Experiment data.",
            metadata={"document_id": "d2", "document_type": "experiment"},
        ),
    ])

    results = await store.query(
        [1.0, 0.0], top_k=5,
        where={"document_type": "literature"},
    )
    assert len(results) == 1
    assert results[0].id == "x"


@pytest.mark.asyncio
async def test_delete_removes_vectors(store):
    await store.add([
        VectorDocument(id="del-1", embedding=[0.1], content="del", metadata={}),
        VectorDocument(id="del-2", embedding=[0.2], content="keep", metadata={}),
    ])
    assert await store.count() == 2

    await store.delete(["del-1"])
    assert await store.count() == 1

    results = await store.query([0.0], top_k=5)
    assert results[0].id == "del-2"


@pytest.mark.asyncio
async def test_add_empty_list(store):
    await store.add([])
    assert await store.count() == 0


@pytest.mark.asyncio
async def test_query_empty_store(store):
    results = await store.query([0.1, 0.2])
    assert results == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/storage/test_chroma_vector.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Write ChromaVectorStore**

`storage/chroma_vector.py`:
```python
import chromadb
from config.model import StorageConfig
from storage.interfaces import BaseVectorStore
from storage.models import VectorDocument, RetrievalResult


class ChromaVectorStore(BaseVectorStore):
    """ChromaDB-backed vector store."""

    def __init__(self, config: StorageConfig):
        self._persist_dir = config.chroma_persist_dir
        self._client: chromadb.PersistentClient | None = None
        self._collection: chromadb.Collection | None = None

    async def initialize(self):
        self._client = chromadb.PersistentClient(path=self._persist_dir)
        self._collection = self._client.get_or_create_collection(
            name="research_documents"
        )

    async def add(self, docs: list[VectorDocument]) -> None:
        if not docs:
            return
        self._collection.add(
            ids=[d.id for d in docs],
            embeddings=[d.embedding for d in docs],
            documents=[d.content for d in docs],
            metadatas=[d.metadata for d in docs],
        )

    async def query(
        self,
        embedding: list[float],
        top_k: int = 10,
        where: dict | None = None,
    ) -> list[RetrievalResult]:
        kwargs = {
            "query_embeddings": [embedding],
            "n_results": top_k,
        }
        if where:
            kwargs["where"] = where

        results = self._collection.query(**kwargs)

        if not results["ids"] or not results["ids"][0]:
            return []

        return [
            RetrievalResult(
                id=results["ids"][0][i],
                content=results["documents"][0][i] or "",
                metadata=results["metadatas"][0][i] or {},
                score=1.0 - results["distances"][0][i]
                if results.get("distances") else 0.0,
            )
            for i in range(len(results["ids"][0]))
        ]

    async def delete(self, ids: list[str]) -> None:
        if ids:
            self._collection.delete(ids=ids)

    async def count(self) -> int:
        return self._collection.count()
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/storage/test_chroma_vector.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add storage/chroma_vector.py tests/storage/test_chroma_vector.py
git commit -m "feat: add ChromaVectorStore implementation"
```

---

## Integration Verification

After all tasks complete, run the full test suite:

```bash
pytest tests/ -v
```

Expected: all ~39 tests PASS

Expected project structure after Phase 1:

```
ResearchCopilot/
├── config/
│   ├── __init__.py
│   ├── model.py
│   ├── loader.py
│   └── settings.yaml
├── providers/
│   ├── __init__.py
│   ├── interfaces.py
│   ├── llm/
│   │   ├── __init__.py
│   │   └── openai.py
│   └── embedding/
│       ├── __init__.py
│       └── openai.py
├── storage/
│   ├── __init__.py
│   ├── models.py
│   ├── interfaces.py
│   ├── file_store.py
│   ├── sqlite_meta.py
│   └── chroma_vector.py
├── models/
│   ├── __init__.py
│   └── message.py
├── tests/
│   ├── config/test_config.py
│   ├── models/test_message.py
│   ├── providers/
│   │   ├── test_interfaces.py
│   │   ├── llm/test_openai.py
│   │   └── embedding/test_openai.py
│   └── storage/
│       ├── test_models.py
│       ├── test_interfaces.py
│       ├── test_file_store.py
│       ├── test_sqlite_meta.py
│       └── test_chroma_vector.py
├── .env.template
└── requirements.txt
```
