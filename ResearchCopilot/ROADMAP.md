# ResearchCopilot — Development Roadmap

> **扫描指南**：新对话开始时，只需阅读「当前状态」+ 「下一步」即可恢复上下文。

---

## 当前状态

- 📅 最后更新：2026-07-08
- 🔄 当前阶段：Phase 5 — 实用性增强（引用 + 元数据 + 批量导入）
- ⏳ 下一里程碑：P1 优化（Chunk 按 section 切分 + 对话历史）

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

### Phase 2: Ingestion Pipeline ✅

| 任务 | 状态 | 日期 |
|---|---|---|
| Ingestion 数据模型 + 接口 (Parser, Normalizer, Chunker, MetadataExtractor) | ✅ | 2026-06-28 |
| PDF Parser (PyMuPDF) | ✅ | 2026-06-28 |
| Text Normalizer | ✅ | 2026-06-28 |
| Scientific Chunker | ✅ | 2026-06-28 |
| Rule-Based Metadata Extractor + IngestionPipeline 编排 (幂等) | ✅ | 2026-06-28 |
| `research ingest` CLI 命令 | ⬜ | - |
| 集成测试 (导入 10 篇 PDF) | ⬜ | - |

**测试总计：87/87 PASS**

### Phase 3: Retrieval + Services ✅

| 任务 | 状态 | 日期 |
|---|---|---|
| Retrieval 数据模型 + 接口 (KeywordRetriever, VectorRetriever, HybridRetriever) | ✅ | 2026-06-28 |
| Keyword Retriever — SQLite FTS5 | ✅ | 2026-06-28 |
| Vector Retriever — ChromaDB | ✅ | 2026-06-28 |
| Hybrid Retriever — RRF fusion | ✅ | 2026-06-28 |
| ChatService (ask + ask_stream) | ✅ | 2026-06-28 |
| SearchService (纯检索) | ✅ | 2026-06-28 |
| SummarizeService (文档摘要) | ✅ | 2026-06-28 |
| CLI 命令 (ingest, ask, search, summarize, list-docs, status) | ✅ | 2026-06-28 |
| 集成测试 (端到端问答) | ⬜ | - |

**测试总计：95/95 PASS**

### Phase 4: Polish & Sync ✅

| 任务 | 状态 | 日期 |
|---|---|---|
| 本地 Embedding Provider (BGE-small, 免费免 API) | ✅ | 2026-07-07 |
| .env 配置 + DeepSeek API 调通 | ✅ | 2026-07-07 |
| OpenAI → DeepSeek 全项目替换 | ✅ | 2026-07-07 |
| FTS5 查询转义修复 + LIKE 回退 | ✅ | 2026-07-07 |
| CLI 懒加载初始化修复 | ✅ | 2026-07-07 |
| 端到端验证（ingest → search → ask 全链路） | ✅ | 2026-07-07 |
| Git push + GitHub sync | ✅ | 2026-07-07 |

**测试总计：全量 PASS ✅**
**MVP 状态：可用 🎉**

### Phase 5: 实用性增强 ⬅ 进行中

| 任务 | 状态 | 日期 |
|---|---|---|
| 增强引用（journal + page + file_path，Ctrl+click 打开 PDF） | ✅ | 2026-07-08 |
| LLM 辅助元数据提取（regex 优先，DeepSeek 兜底乱码/标题误判） | ✅ | 2026-07-08 |
| `research ingest-dir` 批量导入命令 | ✅ | 2026-07-08 |
| 真实文献库：40 篇高熵 LDH，38/40 拿到干净作者名 | ✅ | 2026-07-08 |
| P1: Chunk 按 section 切分 | ⬜ | - |
| P1: 对话历史支持（多轮追问） | ⬜ | - |
| P2: BibTeX 解析器 + compare() 多篇对比 | ⬜ | - |

**已知限制：** 少数 PDF 作者仍误提取（软件用户名如 Administrator/lgq）；journal 偶有关键词误报（Science）

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
| LLM | DeepSeek V4 Pro | .env 配置，可换 |
| Embedding | BGE-small-en-v1.5 (384d, 本地免费) | 可选 OpenAI / BGE-large |
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
| 2026-07-08 | Phase 5：增强引用 + PDF 直达 + LLM 元数据提取 + ingest-dir 批量导入（38/40 干净作者）|
| 2026-07-07 | Phase 4 完成！DeepSeek API 调通 + 本地 BGE Embedding + 端到端 `research ask` 可运行 |
| 2026-06-28 | Phase 1 + 2 + 3 全部完成！95/95 PASS。Storage + AI + Ingestion + Retrieval + Services + CLI |
| 2026-06-27 | Phase 1 Task 3-6：ChatMessage + Provider Interfaces + OpenAI LLM + Embedding Provider |
| 2026-06-26 | 项目脚手架 + 全栈接口设计 + Spec 定稿 + Git/SSH 配置 + Phase 1 Task 1-2 |
