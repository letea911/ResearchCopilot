# Reading Lists — 一键产生分组 (Virtual Reading Lists)

> 状态：设计已确认，待实施

## 概述

用户在聊天问答中根据检索结果选择性导出文献，一键创建虚拟阅读分组。分组中的文献保留在原库（不移动），方便后续写论文时查阅含相关解释的参考文献。

## 动机

- 写讨论时需要快速找到"讨论过某个具体话题"的文献
- 现有分类体系按主题/材料组织，缺少"按研究问题"的临时分组
- 不希望移动文献（破坏原有库结构），只需要快捷引用集合

## 数据模型

### 新表：`reading_lists`

```sql
CREATE TABLE IF NOT EXISTS reading_lists (
    id TEXT PRIMARY KEY,          -- UUID
    name TEXT NOT NULL,           -- 用户手动输入
    query TEXT DEFAULT '',        -- 触发搜索的问题（可选保留）
    created_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS reading_list_items (
    list_id TEXT REFERENCES reading_lists(id) ON DELETE CASCADE,
    document_id TEXT REFERENCES documents(id),
    added_at TEXT DEFAULT '',
    PRIMARY KEY (list_id, document_id)
);
```

- 不改动现有 `documents.collection` 字段
- 一篇文献可以加入多个阅读清单，删除清单不影响文献
- 删除文献时级联删除 `reading_list_items` 中的对应行

### 存储接口新增方法

```python
# BaseMetadataStore 新增
async def create_reading_list(name: str, query: str = "") -> str  # 返回 list_id
async def add_to_reading_list(list_id: str, document_ids: list[str]) -> int  # 返回新增数
async def remove_from_reading_list(list_id: str, document_id: str) -> None
async def get_reading_lists() -> list[dict]  # [{id, name, query, count, created_at}]
async def get_reading_list_items(list_id: str) -> list[DocumentRecord]
async def delete_reading_list(list_id: str) -> None
```

## 交互流程

```
1. 用户在聊天区提问："查找关于LDH含有d带中心讨论的文章"
2. 系统正常检索 → LLM生成回答 + 引用列表
3. 每条引用下方出现 ☐ "加入导出列表" 复选框
4. 用户勾选想要的文献（如 3/8 篇）
5. 底部 [📂 导出勾选的 N 篇为分组] 按钮亮起
6. 用户点击按钮 → 弹出命名框（手动输入）→ 确认
7. 保存 → library_panel 自动刷新 → 新分组出现在"📋 阅读清单"下
8. 展开分组 → 看到文献列表 → 双击总结 → 右键跳转PDF
```

## GUI 改动

### chat_panel.py — 引用加复选框

- 每条引用渲染时增加 `QCheckBox("加入导出列表")`
- 维护 `_export_checkboxes: dict[str, QCheckBox]` 映射（citation_id → checkbox）
- 底部已有按钮区，新增 `QPushButton("📂 导出勾选的 N 篇为分组")`
- 按钮状态：勾选 ≥1 篇时 enabled，否则 disabled
- 点击按钮 → 弹出 `QInputDialog.getText` → 调用 `asyncio.ensure_future(_export_to_list(name))`

### library_panel.py — 树中加入阅读清单分区

- 在树底部（或独立区域）添加"📋 阅读清单"分区标题
- 每个清单显示名称 + 文献数
- 展开清单 → 显示文献（和普通库下文献显示方式一致）
- 清单节点：
  - 右键菜单：「重命名」「删除清单」「从清单中移除」  
  - **不可勾选**（不参与检索范围限定）
  - 不可拖入导入
- 文献节点：
  - 双击 → 总结（和现有行为一致）
  - 右键 → 「跳转PDF」(QDesktopServices.openUrl) / 「从本清单移除」

### main_window.py — 信号接线

- chat_panel 新增信号 `export_to_list_requested(str, list[str])` → (name, doc_ids)
- main_window 连接信号 → 调用 storage API 创建清单
- 完成后 `asyncio.ensure_future(library_panel.refresh())`

## 技术约束

- 虚拟分组**不参与**向量检索的 collections 过滤（因为没有 collection 字段）
- 阅读清单中的文献如果被删除了，清单中对应条目级联删除（外键 CASCADE）
- 阅读清单不计入 `expand_collections`（不影响现有检索逻辑）
- 幂等迁移：`reading_lists` 和 `reading_list_items` 使用 `CREATE TABLE IF NOT EXISTS`

## 验证

1. `tests/storage/test_sqlite_meta.py` — 补 reading list CRUD 测试（6 个）
2. GUI 亲测：提问 → 勾选 → 导出 → 展开清单 → 双击总结 → 跳转PDF
