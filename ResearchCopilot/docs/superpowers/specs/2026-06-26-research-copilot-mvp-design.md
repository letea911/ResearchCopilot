# ResearchCopilot MVP Architecture Design

**Date:** 2026-06-26
**Version:** V1.0
**Status:** Approved

---

## 1. Overview

ResearchCopilot is a domain-specific AI research assistant for computational chemistry / materials science / catalysis. It integrates literature knowledge, experiment data, DFT calculations, and personal notes into a unified semantic search and reasoning system.

**MVP Scope:** Literature Module only. Experiment, DFT, and Personal modules are reserved with directory + interface stubs.

### Architecture Principles

- **铁律①: Interface First** — Every module starts with interface definition, then implementation
- **铁律②: Keep Interfaces Minimal** — Only expose stable capabilities; hide all implementation details
- **Hybrid Cloud-Edge** — Local data sovereignty (files, vectors, metadata), cloud reasoning (GPT-5 API)
- **Provider Abstraction** — LLM and Embedding providers are swappable without business logic changes
- **Module Replaceability** — Any module can be replaced independently

---

## 2. Architecture Overview

```
CLI (prompt_toolkit / rich / click)
 │
 ▼
Application Services
 ├── ChatService         → ServiceResponse (answer + citations + sources)
 ├── SearchService       → SearchResponse (pure retrieval, no LLM)
 └── SummarizeService    → ServiceResponse (document-level summarization)
 │
 ▼
Retrieval
 ├── HybridRetriever     → fused list[RetrievedChunk]
 ├── VectorRetriever     → ChromaDB-backed
 └── KeywordRetriever    → SQLite FTS5-backed
 │
 ▼
┌────────────────┐  ┌───────────────────┐  ┌───────────────┐
│ BaseFileStore  │  │ BaseMetadataStore │  │BaseVectorStore│
│ (filesystem)   │  │ (SQLite)          │  │ (ChromaDB)    │
└────────────────┘  └───────────────────┘  └───────────────┘
 │
 ▼
Ingestion Pipeline
 ├── Parser              → ParsedDocument (PDF, BibTeX, Markdown...)
 ├── Normalizer          → text cleaning
 ├── Chunker             → ChunkedDocument (with position metadata)
 ├── MetadataExtractor   → DocumentRecord
 └── Pipeline (orchestrator, idempotent)
 │
 ▼
AI Providers
 ├── BaseLLMProvider     → chat / stream
 └── BaseEmbeddingProvider → embed
 │
 ▼
Config (settings.yaml + .env)
```

---

## 3. Data Models

### 3.1 Universal Document Model

All content types (literature, experiment, DFT, notes) share the same document abstraction:

```python
@dataclass
class DocumentRecord:
    id: str                       # UUID
    document_type: str            # "literature" | "experiment" | "dft" | "note"
    title: str
    authors: str | None = None
    year: int | None = None
    journal: str | None = None
    doi: str | None = None
    keywords: str | None = None
    abstract: str | None = None
    source_type: str              # "pdf" | "bibtex" | "doi" | "markdown"
    file_path: str | None = None  # → BaseFileStore
    extra: dict | None = None     # domain-specific extension
    created_at: str
```

### 3.2 Chunk Model

```python
@dataclass
class ChunkText:
    document_id: str | None
    chunk_id: str
    chunk_index: int
    text: str
    page_number: int | None = None
    start_offset: int | None = None
    end_offset: int | None = None

@dataclass
class ChunkRecord:
    id: str
    document_id: str
    chunk_index: int
    content: str
    chroma_id: str                # → BaseVectorStore
    token_count: int
    page_number: int | None = None
    start_offset: int | None = None
    end_offset: int | None = None
```

### 3.3 Vector & Retrieval Models

```python
@dataclass
class VectorDocument:
    id: str
    embedding: list[float]
    content: str
    metadata: dict                # {document_id, document_type, title, ...}

@dataclass
class RetrievalResult:
    id: str
    content: str
    metadata: dict
    score: float

@dataclass
class RetrievedChunk:
    chunk_id: str
    content: str
    document_id: str
    score: float
    metadata: dict
```

### 3.4 Service Models

```python
@dataclass
class ChatMessage:
    role: Role                     # system | user | assistant
    content: str
    metadata: dict                 # reserved

@dataclass
class Citation:
    document_id: str
    title: str
    authors: str
    year: int | None
    chunk_id: str | None
    snippet: str | None

@dataclass
class ServiceResponse:
    answer: str
    citations: list[Citation]
    sources: list[RetrievedChunk]

@dataclass
class SearchResponse:
    query: str
    results: list[RetrievedChunk]
    total_hits: int
```

### 3.5 Ingestion Models

```python
@dataclass
class ParsedDocument:
    source_path: str
    content: str
    source_type: str              # "pdf" | "bibtex" | "markdown"
    raw_metadata: dict

@dataclass
class ChunkedDocument:
    source_path: str
    chunks: list[ChunkText]
    raw_metadata: dict

@dataclass
class IndexedDocument:
    document: DocumentRecord
    chunks: list[str]
    chunk_positions: list[int]
```

---

## 4. Interface Definitions

### 4.1 Config Layer

```python
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
    chroma_persist_dir: str
    sqlite_path: str
    file_store_root: str
```

API keys are loaded from `.env`, not from config classes.

### 4.2 AI Providers

```python
class BaseLLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[ChatMessage], **kwargs) -> str: ...
    @abstractmethod
    async def stream(self, messages: list[ChatMessage], **kwargs) -> AsyncIterator[str]: ...

class BaseEmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
```

### 4.3 Storage

```python
class BaseFileStore(ABC):
    @abstractmethod
    def save(self, source: Path, category: str) -> str: ...
    @abstractmethod
    def get_path(self, relative_path: str) -> Path: ...
    @abstractmethod
    def list(self, category: str) -> list[str]: ...
    @abstractmethod
    def delete(self, relative_path: str) -> None: ...

class BaseMetadataStore(ABC):
    @abstractmethod
    async def insert_document(self, doc: DocumentRecord) -> None: ...
    @abstractmethod
    async def get_document(self, document_id: str) -> DocumentRecord | None: ...
    @abstractmethod
    async def get_document_by_doi(self, doi: str) -> DocumentRecord | None: ...
    @abstractmethod
    async def list_documents(self, document_type: str | None = None,
                             year: int | None = None, limit: int = 50) -> list[DocumentRecord]: ...
    @abstractmethod
    async def insert_chunks(self, chunks: list[ChunkRecord]) -> None: ...
    @abstractmethod
    async def get_chunks_by_document(self, document_id: str) -> list[ChunkRecord]: ...
    @abstractmethod
    async def get_chunk_by_chroma_id(self, chroma_id: str) -> ChunkRecord | None: ...

class BaseVectorStore(ABC):
    @abstractmethod
    async def add(self, docs: list[VectorDocument]) -> None: ...
    @abstractmethod
    async def query(self, embedding: list[float], top_k: int = 10,
                    where: dict | None = None) -> list[RetrievalResult]: ...
    @abstractmethod
    async def delete(self, ids: list[str]) -> None: ...
    @abstractmethod
    async def count(self) -> int: ...
```

### 4.4 Retrieval

```python
class BaseKeywordRetriever(ABC):
    @abstractmethod
    async def search(self, query: str, top_k: int = 10,
                     document_type: str | None = None) -> list[RetrievedChunk]: ...

class BaseVectorRetriever(ABC):
    @abstractmethod
    async def search(self, embedding: list[float], top_k: int = 10,
                     where: dict | None = None) -> list[RetrievedChunk]: ...

class BaseHybridRetriever(ABC):
    @abstractmethod
    async def search(self, query: str, embedding: list[float], top_k: int = 10,
                     document_type: str | None = None,
                     keyword_weight: float = 0.3, vector_weight: float = 0.7,
                     ) -> list[RetrievedChunk]: ...
```

### 4.5 Ingestion Pipeline

```python
class BaseParser(ABC):
    @abstractmethod
    async def parse(self, source: Path) -> ParsedDocument: ...
    @abstractmethod
    def supports(self, source: Path) -> bool: ...

class BaseNormalizer(ABC):
    @abstractmethod
    def normalize(self, text: str) -> str: ...

class BaseChunker(ABC):
    @abstractmethod
    def chunk(self, parsed: ParsedDocument) -> ChunkedDocument: ...

class BaseMetadataExtractor(ABC):
    @abstractmethod
    async def extract(self, chunked: ChunkedDocument) -> DocumentRecord: ...
```

### 4.6 Application Services

```python
class BaseChatService(ABC):
    @abstractmethod
    async def ask(self, question: str,
                  conversation_history: list[ChatMessage] | None = None,
                  top_k: int = 10) -> ServiceResponse: ...
    @abstractmethod
    async def ask_stream(self, question: str,
                         conversation_history: list[ChatMessage] | None = None,
                         top_k: int = 10) -> AsyncIterator[str]: ...

class BaseSearchService(ABC):
    @abstractmethod
    async def search(self, query: str, top_k: int = 20,
                     document_type: str | None = None) -> SearchResponse: ...

class BaseSummarizeService(ABC):
    @abstractmethod
    async def summarize(self, document_id: str,
                        focus: str | None = None) -> ServiceResponse: ...
    @abstractmethod
    async def compare(self, document_ids: list[str],
                      focus: str | None = None) -> ServiceResponse: ...
```

---

## 5. Data Flow

### 5.1 Ingestion Flow

```
Source File → Parser → ParsedDocument
              Normalizer → cleaned text
              Chunker → ChunkedDocument (with positions)
              MetadataExtractor → DocumentRecord
              ─── FileStore.save()
              ─── MetadataStore.insert_document()
              ─── EmbeddingProvider.embed()
              ─── VectorStore.add()
              ─── MetadataStore.insert_chunks()
              → document_id
```

Idempotency: file hash check before processing to avoid duplicate ingestion.

### 5.2 Query Flow

```
User Question
    → EmbeddingProvider.embed([question])
    → HybridRetriever.search(query, embedding)
        ├── KeywordRetriever → SQLite FTS5
        └── VectorRetriever → ChromaDB
    → Context Assembly (Prompt Builder)
    → LLMProvider.chat(messages)
    → Citation Parsing
    → ServiceResponse (answer + citations + sources)
```

### 5.3 Search Flow (no LLM)

```
User Query
    → EmbeddingProvider.embed([query])
    → HybridRetriever.search(query, embedding)
    → SearchResponse (results + total_hits)
```

### 5.4 Summarize Flow

```
document_id
    → MetadataStore.get_chunks_by_document(doc_id)
    → Prompt Assembly (system + chunks + focus)
    → LLMProvider.chat(messages)
    → ServiceResponse
```

---

## 6. Project Structure

```
ResearchCopilot/
├── config/
│   ├── settings.yaml
│   └── model.py              # LLMConfig, EmbeddingConfig, ChunkConfig, StorageConfig
├── providers/
│   ├── interfaces.py         # BaseLLMProvider, BaseEmbeddingProvider
│   ├── llm/
│   │   ├── openai.py
│   │   └── deepseek.py
│   └── embedding/
│       ├── openai.py
│       └── bge.py
├── storage/
│   ├── interfaces.py         # BaseFileStore, BaseMetadataStore, BaseVectorStore
│   ├── models.py             # DocumentRecord, ChunkRecord, VectorDocument, RetrievalResult
│   ├── file_store.py
│   ├── sqlite_meta.py
│   └── chroma_vector.py
├── retrieval/
│   ├── interfaces.py         # BaseKeywordRetriever, BaseVectorRetriever, BaseHybridRetriever
│   ├── models.py             # RetrievedChunk
│   ├── keyword.py            # SQLiteFTS5Retriever
│   ├── vector.py             # ChromaVectorRetriever
│   └── hybrid.py
├── ingestion/
│   ├── interfaces.py         # BaseParser, BaseNormalizer, BaseChunker, BaseMetadataExtractor
│   ├── models.py             # ParsedDocument, ChunkedDocument, IndexedDocument, ChunkText
│   ├── pipeline.py           # IngestionPipeline (orchestrator)
│   ├── parsers/
│   │   └── pdf.py            # PyMuPDFParser
│   ├── normalizer.py
│   ├── chunker.py            # ScientificChunker
│   └── metadata.py           # MetadataExtractor
├── services/
│   ├── interfaces.py         # BaseChatService, BaseSearchService, BaseSummarizeService
│   ├── models.py             # ChatMessage, Citation, ServiceResponse, SearchResponse
│   ├── chat.py
│   ├── search.py
│   └── summarize.py
├── models/
│   └── message.py            # ChatMessage, Role
├── cli/
│   ├── main.py               # Entry point
│   └── commands.py           # ResearchCLI
├── tests/
├── data/
│   ├── papers/
│   ├── experiments/
│   └── notes/
├── .env
├── settings.yaml
└── requirements.txt
```

---

## 7. MVP Default Implementations

| Layer | Interface | MVP Default |
|---|---|---|
| LLM | `BaseLLMProvider` | `DeepSeekProvider` (DeepSeek V4 Pro, OpenAI-compatible API) |
| Embedding | `BaseEmbeddingProvider` | `LocalEmbeddingProvider` (`BAAI/bge-small-en-v1.5`, 384d, free) |
| File Store | `BaseFileStore` | `LocalFileStore` (filesystem) |
| Metadata Store | `BaseMetadataStore` | `SQLiteMetadataStore` (with FTS5) |
| Vector Store | `BaseVectorStore` | `ChromaVectorStore` |
| Keyword Retriever | `BaseKeywordRetriever` | `SQLiteFTS5Retriever` |
| Vector Retriever | `BaseVectorRetriever` | `ChromaVectorRetriever` |
| Hybrid Retriever | `BaseHybridRetriever` | `WeightedHybridRetriever` (RRF fusion) |
| PDF Parser | `BaseParser` | `PyMuPDFParser` |
| Normalizer | `BaseNormalizer` | `TextNormalizer` |
| Chunker | `BaseChunker` | `ScientificChunker` |
| Metadata Extractor | `BaseMetadataExtractor` | `RuleBasedMetadataExtractor` (regex + filename) |
| Chat | `BaseChatService` | `ChatService` |
| Search | `BaseSearchService` | `SearchService` |
| Summarize | `BaseSummarizeService` | `SummarizeService` |

---

## 8. Future Modules (Reserved)

The following modules have reserved directories and will implement the same `DocumentRecord` interface with `document_type` values:

- **Experiments** (`experiment`) — CV, EIS, DRT experimental data
- **DFT / Theory** (`dft`) — VASP, CP2K calculation parameters and outputs
- **Personal KB** (`note`) — Chat history, personal notes, analysis records

Each module will add:
- A domain-specific `extra` field schema in `DocumentRecord`
- New parser types (`.csv`, `.json`, `.txt`)
- Domain-specific CLI commands

---

## 9. Verification

### 9.1 Interface Completeness

- [x] Config layer defined (LLM, Embedding, Chunk, Storage)
- [x] AI Provider interfaces (LLM + Embedding)
- [x] Storage interfaces (FileStore + MetadataStore + VectorStore)
- [x] Retrieval interfaces (Keyword + Vector + Hybrid)
- [x] Ingestion interfaces (Parser + Normalizer + Chunker + MetadataExtractor + Pipeline)
- [x] Service interfaces (Chat + Search + Summarize)
- [x] CLI commands defined

### 9.2 Design Principles Check

- [x] Interface First — All modules defined as ABCs before implementation
- [x] Interfaces Minimal — Each ABC has ≤4 abstract methods
- [x] Provider Abstraction — LLM/Embedding swappable via config
- [x] Module Replaceability — Each module only depends on interfaces above it
- [x] Document-Centric — Unified DocumentRecord across all content types
- [x] Idempotent Ingestion — File hash dedup in Pipeline

### 9.3 Integration Test Scenarios

1. `research ingest paper.pdf` → document ingested, searchable
2. `research search "band gap TiO2"` → returns relevant chunks
3. `research ask "what is the optimal doping concentration?"` → retrieves + reasons
4. `research summarize doc_123 --focus results` → document-level summary with citations
5. Duplicate ingest → idempotent, no duplicate vectors
6. Switch embedding provider in config → existing vectors re-indexed, queries still work
