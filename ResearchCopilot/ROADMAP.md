# ResearchCopilot — Development Roadmap

> **扫描指南**：新对话开始时，只需阅读「当前状态」+ 「下一步」即可恢复上下文。

---

## 当前状态

- 📅 最后更新：2026-06-28
- 🔄 当前阶段：Phase 1 完成 → Phase 2 Ingestion Pipeline
- ⏳ 下一里程碑：PDF 导入 + 向量检索可用

---

## 开发铁律

1. **Interface First** — 任何模块先定义接口，再写实现
2. **Keep Interfaces Minimal** — 接口只定义稳定能力，细节藏在实现层

---

## 整体路线图

### Phase 0: 架构设计 ✅

| 任务 | 状态 | 日期 |
|---|---|---|
| 项目脚手架搭建 | ✅ | 2026-06-26 |
| 需求澄清 (brainstorming) | ✅ | 2026-06-26 |
| 接口设计 (Config / Providers / Storage / Retrieval / Ingestion / Services / CLI) | ✅ | 2026-06-26 |
| Architecture Design Spec 撰写 | ✅ | 2026-06-26 |
| ROADMAP.md (本文件) | ✅ | 2026-06-26 |

**产出物**：[docs/superpowers/specs/2026-06-26-research-copilot-mvp-design.md](docs/superpowers/specs/2026-06-26-research-copilot-mvp-design.md)

### Phase 1: MVP Core — Storage + AI Providers ✅

| 任务 | 状态 | 日期 |
|---|---|---|
| 项目依赖 + .env.template | ✅ | 2026-06-26 |
| Config 层实现 (settings.yaml + .env 加载) | ✅ | 2026-06-26 |
| ChatMessage 模型 | ✅ | 2026-06-27 |
| AI Provider 接口 (BaseLLMProvider + BaseEmbeddingProvider) | ✅ | 2026-06-27 |
| OpenAI LLM Provider 实现 | ✅ | 2026-06-27 |
| OpenAI Embedding Provider 实现 | ✅ | 2026-06-27 |
| Storage 数据模型 (DocumentRecord, ChunkRecord, VectorDocument, RetrievalResult) | ✅ | 2026-06-28 |
| Storage 接口 (BaseFileStore, BaseMetadataStore, BaseVectorStore) | ✅ | 2026-06-28 |
| LocalFileStore 实现 | ✅ | 2026-06-28 |
| SQLiteMetadataStore 实现 (SQLite + FTS5) | ✅ | 2026-06-28 |
| ChromaVectorStore 实现 (ChromaDB) | ✅ | 2026-06-28 |

**测试总计：32/32 PASS**

### Phase 2: Ingestion Pipeline

| 任务 | 状态 | 日期 |
|---|---|---|
| PDF Parser (PyMuPDF) | ✅ | 2026-06-28 |
| Text Normalizer | ✅ | 2026-06-28 |
| Scientific Chunker | ✅ | 2026-06-28 |
| Rule-Based Metadata Extractor | ✅ | 2026-06-28 |
| IngestionPipeline 编排 + 幂等 | ✅ | 2026-06-28 |
| `research ingest` CLI 命令 | ⬜ | - |
| 集成测试 (导入 10 篇 PDF) | ⬜ | - |

### Phase 3: Retrieval + Services

| 任务 | 状态 | 日期 |
|---|---|---|
| Keyword Retriever (SQLite FTS5) | ⬜ | - |
| Vector Retriever (ChromaDB) | ⬜ | - |
| Hybrid Retriever (RRF fusion) | ⬜ | - |
| ChatService (ask + ask_stream) | ⬜ | - |
| SearchService (纯检索) | ⬜ | - |
| SummarizeService (文档摘要) | ⬜ | - |
| `research ask/search/summarize` CLI | ⬜ | - |
| 集成测试 (端到端问答) | ⬜ | - |

### Phase 4: Polish & Sync

| 任务 | 状态 | 日期 |
|---|---|---|
| CLI 美化 (rich 格式输出) | ⬜ | - |
| 错误处理完善 | ⬜ | - |
| 性能优化 (批量导入 100+ PDF) | ⬜ | - |
| Git push + GitHub sync | ⬜ | - |
| README 更新 | ⬜ | - |

### Future: 后续版本

| 模块 | 说明 |
|---|---|
| Experiments 数据库 | CV / EIS / DRT 实验数据 |
| DFT / Theory 数据库 | VASP / CP2K 计算数据 |
| Personal KB | 聊天记录 / 笔记 |
| Agent 调度层 | 全局智能规划 |

---

## 技术选型速查

| 层 | 技术 | 备注 |
|---|---|---|
| LLM | DeepSeek V4 Pro (via OpenAI-compatible API) | .env 配置，可换 |
| Embedding | OpenAI text-embedding-3-small (1536d) | 后续支持 BGE |
| 向量库 | ChromaDB | 本地持久化 |
| 元数据 | SQLite + FTS5 | 全文搜索 |
| PDF 解析 | PyMuPDF | 支持双栏/图表 |
| CLI | rich + prompt_toolkit + click | 终端美化 |
| 语言 | Python 3.12+ | async/await 全异步 |

---

## 设计文档索引

| 文档 | 路径 |
|---|---|
| Architecture Design Spec | [docs/superpowers/specs/2026-06-26-research-copilot-mvp-design.md](docs/superpowers/specs/2026-06-26-research-copilot-mvp-design.md) |
| README (with daily log) | [README.md](README.md) |
| ROADMAP (本文件) | [ROADMAP.md](ROADMAP.md) |

---

## 开发日志（近期）

> 详细每日记录见根目录 [README.md](../README.md) 的「每日开发日志」部分。

| 日期 | 关键进展 |
|---|---|
| 2026-06-28 | Phase 1 完成！Task 7-11：Storage Models + Interfaces + FileStore + SQLite + ChromaDB (32/32 PASS) |
| 2026-06-27 | Phase 1 Task 3-6：ChatMessage + Provider Interfaces + OpenAI LLM + Embedding Provider |
| 2026-06-26 | 项目脚手架 + 全栈接口设计 + Spec 定稿 + Git/SSH 配置 + Phase 1 Task 1-2 |
