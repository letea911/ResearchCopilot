"""ClassifierDialog — AI-powered batch classification of literature."""
import asyncio

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QRadioButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QButtonGroup,
)
from PyQt5.QtCore import Qt


class ClassifierDialog(QDialog):
    """Modal dialog: pick a scope → AI classifies → review & save."""

    def __init__(self, ctx: dict, library_panel, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self._library_panel = library_panel
        self._results: list = []  # ClassifyResult rows to save
        self._saved = False

        self.setWindowTitle("AI 文献分类器")
        self.resize(920, 600)
        self._build_ui()
        # 异步加载库列表（不在 __init__ 里用 run_until_complete）
        asyncio.ensure_future(self._init_collections())

    def was_saved(self) -> bool:
        return self._saved

    # ---- UI construction ----------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # ---- Row 0: scope selection ----
        scope_row = QHBoxLayout()
        self.btn_group = QButtonGroup(self)
        self.radio_all = QRadioButton("整个库")
        self.radio_sel = QRadioButton("勾选的文献")
        self.btn_group.addButton(self.radio_all, 0)
        self.btn_group.addButton(self.radio_sel, 1)
        self.radio_all.setChecked(True)
        scope_row.addWidget(self.radio_all)
        self.scope_combo = QComboBox()
        self.scope_combo.setMinimumWidth(120)
        scope_row.addWidget(self.scope_combo)
        scope_row.addWidget(self.radio_sel)
        scope_row.addStretch()
        self.start_btn = QPushButton("开始分析")
        self.start_btn.clicked.connect(self._on_start)
        scope_row.addWidget(self.start_btn)
        self.status_label = QLabel("")
        scope_row.addWidget(self.status_label)
        layout.addLayout(scope_row)

        # ---- Table ----
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["标题", "AI 关键词", "AI 摘要", "目标库", "置信度"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 200)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 60)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked)
        layout.addWidget(self.table, stretch=1)

        # ---- Bottom bar ----
        bottom = QHBoxLayout()
        bottom.addStretch()
        self.save_btn = QPushButton("全部保存")
        self.save_btn.clicked.connect(self._on_save_all)
        self.save_btn.setEnabled(False)
        bottom.addWidget(self.save_btn)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        bottom.addWidget(close_btn)
        layout.addLayout(bottom)

    # ---- Async init ---------------------------------------------------------

    async def _init_collections(self):
        tree = await self.ctx["meta_store"].get_collection_tree()
        GENERIC = {"默认库", "临时库", "general", "default", "temp", "临时", "默认"}
        specific = []
        generic = []
        for node in tree:
            is_generic_root = node["name"] in GENERIC
            if node["children"]:
                for child in node["children"]:
                    entry = f"{node['name']} → {child}"
                    if is_generic_root or child in GENERIC:
                        generic.append(entry)
                    else:
                        specific.append(entry)
            else:
                if is_generic_root:
                    generic.append(node["name"])
                else:
                    specific.append(node["name"])
        names = specific + generic
        if not names:
            names = ["默认库"]
        self.scope_combo.addItems(names)

    # ---- Start classification ----------------------------------------------

    def _on_start(self):
        self.start_btn.setEnabled(False)
        self.save_btn.setEnabled(False)
        self.table.setRowCount(0)
        self._results = []
        # 转为异步——不能在运行中的事件循环上用 run_until_complete
        asyncio.ensure_future(self._collect_and_run())

    async def _collect_and_run(self):
        doc_ids = await self._collect_doc_ids_async()
        if not doc_ids:
            self.status_label.setText("没有找到文献。")
            self.start_btn.setEnabled(True)
            return
        self.status_label.setText(f"正在分析 0/{len(doc_ids)}…")
        await self._run_classify(doc_ids)

    async def _collect_doc_ids_async(self) -> list[str]:
        if self.radio_sel.isChecked():
            ids = self._library_panel.get_selected_doc_ids()
            return ids or []
        coll_raw = self.scope_combo.currentText()
        if not coll_raw:
            return []
        # "电催化 → 高熵" → leaf name only
        collection = coll_raw.split("→")[-1].strip() if "→" in coll_raw else coll_raw
        docs = await self.ctx["meta_store"].list_documents(
            collection=collection, limit=100000
        )
        return [d.id for d in docs]

    async def _run_classify(self, doc_ids: list[str]):
        meta = self.ctx["meta_store"]
        classify = self.ctx["classify"]

        # 预先批量取所有文档的标题（用于表格显示）
        doc_map = {}
        for did in doc_ids:
            d = await meta.get_document(did)
            if d:
                doc_map[did] = d

        total = len(doc_ids)
        tree_data = await meta.get_collection_tree()
        # Build flat display list: specific libraries first, generic ones last.
        GENERIC = {"默认库", "临时库", "general", "default", "temp", "临时", "默认"}
        specific_names = []
        generic_names = []
        for node in tree_data:
            is_generic_root = node["name"] in GENERIC
            if node["children"]:
                for child in node["children"]:
                    entry = f"{node['name']} → {child}"
                    if is_generic_root or child in GENERIC:
                        generic_names.append(entry)
                    else:
                        specific_names.append(entry)
            else:
                if is_generic_root:
                    generic_names.append(node["name"])
                else:
                    specific_names.append(node["name"])
        # Specific first, then generic last. Placeholder at index 0.
        display_names = ["⚠ 请手动选择…"] + specific_names + generic_names

        for i, doc_id in enumerate(doc_ids):
            self.status_label.setText(f"正在分析 {i+1}/{total}…")
            result = await classify.classify_single(doc_id)
            self._results.append(result)

            doc = doc_map.get(doc_id)
            title = doc.title if doc else doc_id[:8]

            row = self.table.rowCount()
            self.table.insertRow(row)

            # 标题 (只读)
            title_item = QTableWidgetItem(title[:70])
            title_item.setFlags(title_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, title_item)

            # 关键词 (可编辑)
            kw = ", ".join(result.keywords) if result.keywords else ""
            self.table.setItem(row, 1, QTableWidgetItem(kw))

            # 摘要 (可编辑)
            self.table.setItem(row, 2, QTableWidgetItem(result.abstract))

            # 目标库 (QComboBox，显示嵌套层级 + AI 建议新建)
            combo = QComboBox()
            combo.addItems(display_names)
            # Determine AI's suggested leaf in display format
            suggested_display = ""
            if result.suggested_parent and result.suggested_collection:
                suggested_display = f"{result.suggested_parent} → {result.suggested_collection}"
            elif result.suggested_collection:
                suggested_display = result.suggested_collection
            # If AI suggests a new sub or parent, append a "新建" entry
            new_name = result.new_collection or ""
            new_parent = result.new_parent or ""
            if new_parent and new_name:
                new_label = f"＋新建「{new_parent} → {new_name}」"
            elif new_name:
                new_label = f"＋新建「{new_name}」"
            else:
                new_label = ""
            if new_label:
                existing = [combo.itemText(j) for j in range(combo.count())]
                if new_label not in existing:
                    combo.addItem(new_label)
                    combo.setCurrentIndex(combo.count() - 1)
            elif suggested_display:
                idx = combo.findText(suggested_display)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
            self.table.setCellWidget(row, 3, combo)

            # 置信度 (只读)
            conf_item = QTableWidgetItem(f"{result.confidence:.0%}")
            conf_item.setFlags(conf_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 4, conf_item)

        self.status_label.setText(f"分析完成，共 {total} 篇。请逐行确认后保存。")
        self.save_btn.setEnabled(True)
        self.start_btn.setEnabled(True)

    # ---- Save ---------------------------------------------------------------

    def _on_save_all(self):
        if not self._results:
            return
        self.save_btn.setEnabled(False)
        self.status_label.setText("正在保存…")
        asyncio.ensure_future(self._save_all())

    async def _save_all(self):
        meta = self.ctx["meta_store"]
        total = self.table.rowCount()
        ok, fail = 0, 0

        for row in range(total):
            result = self._results[row]
            try:
                kw_item = self.table.item(row, 1)
                abs_item = self.table.item(row, 2)
                combo = self.table.cellWidget(row, 3)

                keywords = (kw_item.text() or "").strip() if kw_item else ""
                abstract = (abs_item.text() or "").strip() if abs_item else ""
                collection = combo.currentText() if combo else ""

                # Skip rows where user hasn't selected a real library
                if not collection or collection.startswith("⚠"):
                    fail += 1
                    continue

                # Parse "＋新建「父 → 子」" or "＋新建「name」" or "电催化 → 高熵"
                parent = None
                if collection and collection.startswith("＋新建「"):
                    inner = collection[4:-1]
                    if "→" in inner:
                        parts = [p.strip() for p in inner.split("→", 1)]
                        parent = parts[0]
                        collection = parts[1] if len(parts) > 1 else inner
                        await meta.create_collection(collection, parent=parent)
                    else:
                        collection = inner
                        await meta.create_collection(collection)
                elif "→" in collection:
                    # Existing nested: "电催化 → 高熵"
                    collection = collection.split("→")[-1].strip()

                await meta.update_document_metadata(
                    result.document_id,
                    keywords=keywords or None,
                    abstract=abstract or None,
                    collection=collection or None,
                )
                ok += 1
            except Exception as exc:
                fail += 1
                print(f"[Classifier] save error row={row}: {exc}")

        self._saved = True
        self.status_label.setText(f"保存完成：{ok} 成功，{fail} 失败。可关闭窗口。")
        self.save_btn.setEnabled(False)
