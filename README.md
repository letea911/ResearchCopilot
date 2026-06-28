# ResearchCopilot

AI-powered research literature assistant.

---

## 🧭 工作流纪律 (Workflow Discipline)

每日开发必须遵循以下流程：

### 1. 计划 (Plan)
- [ ] 明确今日开发目标，写在下方日志中
- [ ] 评估任务优先级 (P0 > P1 > P2)
- [ ] 预估每个任务的时间

### 2. 编码 (Code)
- [ ] 分支开发：新功能使用 `feature/xxx` 分支
- [ ] 小步提交：每完成一个独立功能点就 commit
- [ ] Commit 规范：`type: description` (feat/fix/docs/refactor/test)

### 3. 测试 (Test)
- [ ] 自测通过后再合并到 main
- [ ] 关键功能写单元测试

### 4. 同步 (Sync)
- [ ] 每天收工前 push 到 GitHub
- [ ] 更新下方日志，记录今日进展

---

## 📋 每日开发日志 (Daily Dev Log)

### 2026-06-28
- **今日目标**: Phase 1 Task 7-11 全部完成 + Phase 2 Ingestion Pipeline
- **完成事项**:
  - ✅ **Phase 1 收尾**：Storage Models + Interfaces + FileStore + SQLite + ChromaDB（32/32 PASS）
  - ✅ **Phase 2-1**：Ingestion Models + Interfaces — Parser, Normalizer, Chunker, MetadataExtractor（13/13 PASS）
  - ✅ **Phase 2-2**：PDF Parser — PyMuPDF 集成（5/5 PASS）
  - ✅ **Phase 2-3**：Text Normalizer + Scientific Chunker（13/13 PASS）
  - ✅ **Phase 2-4**：Metadata Extractor + IngestionPipeline 编排 + 幂等校验（6/6 PASS）
  - ✅ **Phase 1 + Phase 2 全部完成！全量 87/87 PASS**
- **遇到问题**: chromadb 1.5.9 拒绝空 dict metadata；pytest-asyncio 1.4.0 需 @pytest_asyncio.fixture；datetime.utcnow() 已弃用
- **明日计划**: Phase 3 Retrieval + Services（Keyword/Vector/Hybrid Retriever → Chat/Search/Summarize Service）

### 2026-06-27
- **今日目标**: Phase 1 Task 3-5（ChatMessage → AI Provider Interfaces → OpenAI LLM Provider）
- **完成事项**:
  - ✅ Task 3：ChatMessage 模型（4/4 PASS）
  - ✅ Task 4：AI Provider 接口 — BaseLLMProvider + BaseEmbeddingProvider（5/5 PASS）
  - ✅ Task 5：OpenAI LLM Provider 实现（4/4 PASS）
  - ✅ Task 6：OpenAI Embedding Provider 实现（3/3 PASS）
- **遇到问题**: Task 5 派发时被意外中断，重新派发后顺利完成
- **明日计划**: Phase 1 Task 7-11（Storage Models → Storage Interfaces → 三个 Storage 实现）

### 2026-06-26
- **今日目标**: 完成 ResearchCopilot 架构设计 + Phase 1 前两个 Task
- **完成事项**:
  - ✅ 项目脚手架搭建（目录结构 + LICENSE + .gitignore）
  - ✅ Git 全局配置（letea911 / 1215303245@qq.com）
  - ✅ SSH 配置并同步到 GitHub（https://github.com/letea911/ResearchCopilot）
  - ✅ Brainstorming：需求澄清、架构设计、7 层接口定义
  - ✅ Architecture Design Spec 撰写
  - ✅ ROADMAP.md 开发路线图 + 进度追踪
  - ✅ 两条铁律确立：Interface First + Keep Interfaces Minimal
  - ✅ Phase 1 Task 1：项目依赖 + .env.template
  - ✅ Phase 1 Task 2：Config 模型 + 设置加载器（2/2 tests PASS）
  - ✅ 开发追踪 memory 保存
- **遇到问题**: HTTPS 无法连接 GitHub → 切换 SSH 解决
- **明日计划**: Phase 1 Task 3-11 继续推进（ChatMessage → AI Providers → Storage）

---

> 模板：每天复制上一日格式，填写当日内容。

