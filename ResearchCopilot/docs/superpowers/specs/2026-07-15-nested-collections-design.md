# Nested Collections — Hierarchical Library Design Spec

**Date:** 2026-07-15
**Status:** Approved
**Phase:** 9

## Overview

Upgrade the flat library system (Phase 7) to support a two-level hierarchy:
root libraries (e.g. "电催化") → sub-libraries (e.g. "高熵", "OER").
Documents live in leaf sub-libraries. Classification can recommend both levels.
Retrieval on a parent library automatically includes all its children.

## Product Decisions

| Decision | Choice |
|---|---|
| Hierarchy model | Parent-child reference (parent column on collections table) |
| Nesting depth | Maximum 2 levels (root → sub) |
| Document membership | Single leaf sub-library only |
| Classification granularity | AI recommends both parent and sub-library |
| Retrieval scope | Checking parent = auto-include all child sub-libraries |

## Data Model

### collections table (SQLite)

```sql
CREATE TABLE IF NOT EXISTS collections (
    name TEXT PRIMARY KEY,
    parent TEXT DEFAULT NULL,   -- NULL = root-level
    created_at TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_collections_parent ON collections(parent);
```

Examples:

| name | parent |
|---|---|
| 默认库 | NULL |
| 电催化 | NULL |
| 高熵 | 电催化 |
| 异质结构 | 电催化 |
| OER | 电催化 |

### DocumentRecord

Unchanged. `collection: str = "默认库"` stores the leaf sub-library name.
Parent relationship is resolved via the collections table, not duplicated on documents.

### Migration

Idempotent (same pattern as section + collection columns):
```sql
ALTER TABLE collections ADD COLUMN parent TEXT DEFAULT NULL;
```
All existing collections get `parent = NULL` (root-level). No data loss.
40 existing documents in "默认库" remain there — "默认库" becomes a root library.

## API Design

### SQLiteMetadataStore — new/changed methods

```python
async def create_collection(self, name: str, parent: str | None = None) -> None:
    """Create a library, optionally under a parent (max 2 levels)."""

async def list_collections(self, parent: str | None = None) -> list[str]:
    """List libraries. parent=None returns root; parent='X' returns children of X."""

async def get_collection_tree(self) -> list[dict]:
    """Return full hierarchy as [{"name":..., "parent":..., "children":[...]}, ...]."""

async def expand_collections(self, names: list[str]) -> list[str]:
    """Given a set of library names, expand parent libraries to include all their
    leaf children. Used by retrieval to auto-include sub-libraries.
    Example: ["电催化"] → ["电催化", "高熵", "异质结构", "OER"]"""

async def rename_collection(self, old_name: str, new_name: str) -> bool:
    """Existing method; works for both root and sub-libraries. Also renames
    references in child rows' parent column."""

async def list_documents(..., collection: str | None = None, ...):
    """Existing; unchanged. Callers use expand_collections before passing names."""
```

### BaseMetadataStore (interfaces.py)

Synchronize new/changed abstract signatures:
`create_collection(name, parent=None)`, `list_collections(parent=None)`,
`get_collection_tree()`, `expand_collections(names)`.

### BaseVectorStore

No changes required. `backfill_metadata` and `update_metadata_by_filter` already
handle metadata key-value updates. When a sub-library is renamed, the caller
(rename_collection flow) calls `update_metadata_by_filter` with the old/new name.

## Retrieval Flow

```
User checks ["电催化"] in GUI
  → chat_panel._current_collections() returns ["电催化"]
  → chat.ask(collections=["电催化"])
  → meta_store.expand_collections(["电催化"])
      → SELECT name FROM collections WHERE parent IN ('电催化')
      → returns ["电催化", "高熵", "异质结构", "OER"]
  → hybrid.search(collections=["电催化", "高熵", "异质结构", "OER"])
      → keyword: WHERE d.collection IN (?, ?, ?, ?)
      → vector: where={"collection": {"$in": [...]}}
```

If user checks nothing → `collections=None` → no filter (all libraries).

Expansion is called in exactly one place: `hybrid.search()` receives already-expanded
lists from the service layer, or the hybrid layer calls `expand_collections` internally.
The plan will decide the exact boundary.

## Classification Prompt Changes

Current prompt returns single `suggested_collection` + `new_collection`.
Upgraded to return two-level structure:

```json
{
  "keywords": ["OER", "LDH", "electrocatalysis"],
  "abstract": "This paper investigates...",
  "suggested_parent": "电催化",
  "suggested_sub": "高熵",
  "new_parent": "",
  "new_sub": "",
  "confidence": 0.88
}
```

Rules embedded in the prompt:
- Prefer placing in existing sub-libraries when possible
- If paper fits under an existing parent but needs a new sub, fill `suggested_parent` + `new_sub`
- Only suggest `new_parent` if no existing parent fits at all
- `new_*` fields are empty when existing libraries suffice

### ClassifyResult dataclass

Add fields: `suggested_parent: str = ""`, `new_parent: str = ""`.

### ClassifierDialog table

Target library QComboBox renders hierarchy as "电催化 → 高熵".
The classifier pre-selects the AI-recommended entry.

## GUI Changes

### library_panel.py — QTreeWidget

Three-level tree:
```
☑ 默认库 (40)          ← root library (checkable)
   ├─ 📄 paper A        ← document (not checkable)
   └─ 📄 paper B

☑ 电催化 (0)            ← root library with children
   ├─ ☑ 高熵 (12)       ← sub-library (checkable)
   │   ├─ 📄 ...
   │   └─ 📄 ...
   ├─ ☐ 异质结构 (8)
   └─ ☑ OER (5)
```

Checkbox propagation:
- Check parent → auto-check all sub-library children
- Uncheck parent → auto-uncheck all sub-library children
- Unchecking a sub-library individually → parent goes to "partial" (半勾) state
- `selected_collections()` returns the leaf-most checked names for retrieval

### library_panel.py — toolbar changes

- "新建库" dialog: add optional `QComboBox` for parent library
  ("无 (根级)" + all root library names)
- "导入到" dropdown: shows all leaf + sub-libraries with indent or "→" notation
- Double-click rename: works on both root and sub-library nodes

### classifier_dialog.py

- Target library QComboBox: hierarchical display ("电催化 → 高熵")
- Pre-selection based on AI's `suggested_parent` + `suggested_sub`

## Testing

### Storage
- `test_create_sub_collection`: create child, verify parent set
- `test_list_collections_by_parent`: filter by parent
- `test_expand_collections`: expand parent to include children
- `test_get_collection_tree`: full hierarchy
- `test_rename_sub_collection`: rename updates parent refs in sibling rows
- `test_rename_parent_collection`: rename cascades to children's parent column

### Retrieval
- `test_expand_before_search`: hybrid receives expanded list
- `test_parent_check_includes_sub_libraries`: end-to-end

### GUI
- Tree builds three-level hierarchy correctly
- Checkbox propagation (parent ↔ children)
- Import target dropdown shows hierarchical entries
- Rename on sub-library node works

### Classifier
- `test_classify_returns_two_level`: mock LLM returns parent+sub
- `test_classify_prompt_includes_hierarchy`: verify collections are formatted as "parent → sub"

### Regression
- All existing tests (storage 40, services 14, CLI 10, retrieval 5) pass unchanged
- `tests/cli` — no existing command signatures break (new optional parameters only)

## Migration Path

1. Run ALTER TABLE migration on startup (idempotent, auto-skipped if column exists)
2. All existing collections become root-level (parent=NULL)
3. All existing documents stay in their current collection
4. User can gradually organize by creating sub-libraries and re-classifying documents

## Scope Boundaries

**In scope**: data model, storage API, retrieval expansion, GUI tree + checkboxes,
classifier prompt upgrade, migration.

**Out of scope**: arbitrary depth (>2 levels), multi-parent collections,
bulk move documents between libraries (already possible via classifier or
one-by-one metadata update), drag-drop reordering in tree.
