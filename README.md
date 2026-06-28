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

### 2026-06-28 🚀 超高产日
- **今日目标**: Phase 1 收尾 + Phase 2 + Phase 3 全部完成
- **完成事项**:
  - ✅ **Phase 1 收尾**：Storage + FileStore + SQLite + ChromaDB（32/32 PASS）
  - ✅ **Phase 2**：Ingestion Pipeline — Parser + Normalizer + Chunker + Metadata + Pipeline 编排（87/87 PASS）
  - ✅ **Phase 3-1**：Retrieval Models + Interfaces（8/8 PASS）
  - ✅ **Phase 3-2**：Keyword + Vector + Hybrid Retriever（20/20 PASS）
  - ✅ **Phase 3-3**：ChatService + SearchService + SummarizeService（4/4 PASS）
  - ✅ **Phase 3-4**：CLI — ingest / ask / search / summarize / list-docs / status（7/7 PASS）
  - ✅ **Phase 1+2+3 全部完成！全量 95/95 PASS 🎉**
- **遇到问题**: chromadb 1.5.9 空 metadata 拒绝；FTS5 需手动 rebuild 索引；`list` 与 Python 内置冲突改名 `list-docs`
- **明日计划**: Phase 4 Polish — 真实 PDF 端到端测试 + 错误处理完善 + `research ask` 首次真实调用

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

