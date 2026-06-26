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

