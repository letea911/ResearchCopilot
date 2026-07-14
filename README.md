# ResearchCopilot

AI-powered research literature assistant.
C:/ProgramData/anaconda3/python.exe -m cli.main ask "你的问题"

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

### 2026-07-14
- **今日目标**: Phase 6 — 桌面图形界面（GUI）
- **完成事项**:
  - ✅ 抽出 `core/context.py`（共享依赖构建，CLI 和 GUI 都用，CLI 未破坏）
  - ✅ 框架决策：PySide6 在 Anaconda 有 Qt DLL 冲突 → 改用 PyQt5 + qasync（已卸载 PySide6）
  - ✅ PyQt5 桌面界面：`gui/main.py`（qasync 入口）+ `main_window.py`（布局+拖拽+后台加载模型）+ `chat_panel.py`（问答+引用+PDF跳转+多轮历史）+ `library_panel.py`（文献列表+库状态）
  - ✅ `run_gui.bat` 双击启动脚本
  - ✅ 导入 + 离屏构造测试通过（窗口对象可正常创建）
  - ✅ 修复 list-docs 装饰器再次回归（补回 `@cli.command(name="list-docs")`，CLI 10/10 PASS）
- **遇到问题**: PySide6 6.11 与 Anaconda 自带 PyQt5 的 Qt DLL 撞车（procedure not found）→ 改用环境已有的 PyQt5；list-docs 装饰器多次回归（这次确认落地）
- **明日计划**: 用户亲测 GUI（双击 run_gui.bat）；后续 Experiments 实验数据模块

### 2026-07-08
- **今日目标**: Phase 5 实用性增强 — 引用溯源 + 元数据质量 + 批量导入
- **完成事项**:
  - ✅ 增强引用：Citation 增加 journal/page/file_path，CLI 显示 `📚 References` + `📄 Open PDF`（Ctrl+click 跳转原文）
  - ✅ P0-1：LLM 辅助元数据提取（regex 优先，DeepSeek 兜底乱码/标题误判/错误年份）
  - ✅ 修复 regex bug：作者清理误删 a-e 字母（Hybrid→Hyri）
  - ✅ 新增乱码检测 `_looks_garbled` + 标题误判检测 `_looks_like_title`
  - ✅ P0-2：`research ingest-dir` 批量导入命令
  - ✅ 导入 40 篇真实高熵 LDH 论文，重提取后 38/40 拿到干净作者名
  - ✅ **P1-A**：Section 切分 + 页码溯源 —— chunker 识别论文章节（Introduction/Methods/Results/Conclusion）+ 计算页码，引用显示 "Results And Discussion, p.1"
  - ✅ 修复 section 检测：双栏 PDF 整页合成一段，改逐行扫描标题
  - ✅ ChatService 从 SQLite 回查 section/page（兼容旧向量库）
  - ✅ **P1-B**：`research chat` 交互式多轮对话（内存维护 history，支持追问）
  - ✅ 重建 40 篇 651 chunks 的 section + 页码
  - ✅ 测试：全模块 PASS（1 个 pre-existing 幂等测试无关失败）
- **遇到问题**: PDF 文本提取质量差导致作者乱码（LLM 兜底）；section 标题在双栏 PDF 页中间行（改逐行扫描）；旧向量库无 section metadata（改 SQLite 回查）
- **明日计划**: P2（BibTeX 解析器 + compare() 多篇对比）

### 2026-07-07
- **今日目标**: Phase 4 — DeepSeek 替换 + 端到端验证 MVP
- **完成事项**:
  - ✅ 本地 Embedding Provider（BGE-small-en-v1.5, 384d, 免费免 API）
  - ✅ .env 配置 + DeepSeek API 连通性验证（模型 deepseek-chat, base_url /v1）
  - ✅ OpenAI → DeepSeek 全项目替换（provider、config、CLI、ROADMAP、spec）
  - ✅ FTS5 关键词检索修复（自然语言转义 + LIKE 回退）
  - ✅ CLI 上下文初始化修复（_get_context 懒加载）
  - ✅ **端到端验证通过**：`research ingest` → `research search` → `research ask` 全链路
- **遇到问题**: DeepSeek 模型名需用 `deepseek-chat` 非 `v4-pro`；OpenAI SDK 需 `/v1` 路径；FTS5 不接收自然语言；CLI Context 未注入
- **明日计划**: 导入真实论文开始使用，批量导入优化

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

