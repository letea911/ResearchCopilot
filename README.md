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

### 2026-07-15 (Phase 9)
- **今日目标**: Phase 9 库嵌套（两级父子引用）
- **完成事项**:
  - ✅ **Phase 1 存储**：collections 表加 parent 列（幂等迁移）+ `create_collection(name,parent)`/`list_collections(parent)`/`get_collection_tree()`/`expand_collections(names)`/`rename_collection` 级联 parent
  - ✅ **Phase 2 检索**：hybrid.search 接入 `expand_collections`（父库勾选→自动展开子库）+ meta_store 注入
  - ✅ **Phase 3 分类器**：prompt 两级推荐（suggested_parent/sub + new_parent/sub）+ ClassifyResult 扩展
  - ✅ **Phase 4 GUI 库面板**：QTreeWidget 三层树 + 勾选联动（父勾=全子勾，半勾支持）+ 新建库 parent 下拉 + 导入下拉嵌套「→」格式
  - ✅ **Phase 5 GUI 分类器**：弹窗目标库下拉嵌套显示 + 保存解析「父→子」
  - ✅ **验证**：storage 45 + services 14 + CLI 10 = 69/69 PASS
- **明日计划**: 用户亲测嵌套库；后续 Experiments 实验数据模块

### 2026-07-15 (Phase 8)
- **今日目标**: Phase 8 AI 分类器（自动提取关键词+摘要+推荐分组）
- **完成事项**:
  - ✅ **Phase 1 存储扩展**：`update_document_metadata` 加 keywords/abstract/collection 参数 + FTS5 重建（更新后关键词可被 FTS 搜索到）
  - ✅ **Phase 2 服务**：`ClassifierService.classify_single/batch` — 复用 summarize 的"拿全文→调 LLM→解析 JSON"链路 + metadata 的 `temperature=0.0` 模式；`ClassifyResult` dataclass
  - ✅ **Phase 3 GUI**：`ClassifierDialog(QDialog+QTableWidget)` — 两种范围（整个库/勾选文献）；AI 分析时进度显示；表格逐行：关键词(可编辑)+摘要(可编辑)+目标库(QComboBox 含"新建xxx")+置信度；全部保存按钮
  - ✅ **Phase 4 CLI**：`classify` 命令 — `--doc-id` / `--collection` / `--dry-run`
  - ✅ **验证**：storage 37 + services 14(含 5 个新 classify 测试) + CLI 10 + retrieval 5 = 66/66 PASS
- **明日计划**: 用户亲测分类器；后续 Experiments 实验数据模块

### 2026-07-15 (Phase 7)
- **今日目标**: Phase 7 多文献库（命名库 + 按库导入 + 按库检索问答）
- **完成事项**:
  - ✅ **Phase A 存储层**：DocumentRecord 加 `collection` 字段（默认"默认库"）；SQLite 幂等迁移（ALTER TABLE ADD COLUMN DEFAULT）平滑兼容40篇；collections 库名表 + list_collections/create_collection
  - ✅ **Phase B 导入**：`ingest(source, collection)`；向量 metadata 加 `collection` 键
  - ✅ **Phase C 检索**：keyword/hybrid/service 全链路 collections 过滤 + 补向量不过滤老缺口
  - ✅ **Phase D CLI**：所有命令 `--collection` + 新命令 list-collections/backfill-collections
  - ✅ **Phase E GUI**：左侧 QTreeWidget（可勾选库+文献子节点）；导入到下拉+新建库+导入PDF按钮；按库问答
  - ✅ **验证**：96/96 PASS（storage 36 + ingestion 47 + retrieval/services 30 + cli 10）+ offscreen 集成树构建通过
- **遇到问题**: 新增 ABC 方法后 test_interfaces 假类缺实现(2 fail)→补方法；hybrid 断言要同步更新
- **明日计划**: 用户亲测多库功能；后续 Experiments 实验数据模块

### 2026-07-14
- **今日目标**: Phase 6 桌面 GUI 打磨（联调修 bug + 易用性）
- **完成事项**:
  - ✅ 修双击闪退：`run_gui.bat` 写死 Anaconda python（系统有 3 个 python，双击时会挑到没装库的那个）+ 日志兜底 `gui_error.log`
  - ✅ 修引用 PDF 乱码：QTextBrowser 不再自己加载 `file:///`，改 `QDesktopServices.openUrl` 用系统默认阅读器外部打开
  - ✅ 一键总结该篇：双击左侧文献 → 聊天区直接出 AI 摘要（复用 `summarize` 服务，零业务改动）
  - ✅ 聊天区小修：“思考中…”答完自动删除 + 每次追加自动滚到底
  - ✅ 修界面“未响应”：`LocalEmbeddingProvider.embed()` 的模型加载/编码移到后台线程（`run_in_executor`），不再阻塞 qasync 事件循环=界面线程（顺带修好每次提问/拖拽导入的短暂卡顿）
  - ✅ 验证：GUI import OK；`tests/cli` 10/10 PASS + `test_local` 3/3 PASS（未碰 CLI，无回归）
- **遇到问题**: 双击 .bat 的 `python` 指向不确定（PATH 里三个 python）→ 写死路径；`file://` 链接被 QTextBrowser 当文档加载 → 改外部打开
- **明日计划**: 用户亲测；后续 Experiments 实验数据模块

### 2026-07-14 (GUI 完成)
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

