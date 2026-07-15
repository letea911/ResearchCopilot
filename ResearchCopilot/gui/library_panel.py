"""LibraryPanel — browse libraries (collections) and their documents."""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTreeWidget, QTreeWidgetItem, QInputDialog, QFileDialog,
)


class LibraryPanel(QWidget):
    # 双击某篇 → 请求总结这篇（doc_id, title）
    summarize_requested = pyqtSignal(str, str)
    # 「导入PDF…」选好文件 → (目标库, 文件路径列表)
    import_requested = pyqtSignal(str, list)
    # 「AI 分类器」按钮被点击
    classify_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ctx = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("文献库")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        # 顶部工具行：导入目标库下拉 + 新建库 + 导入PDF
        tool_row = QHBoxLayout()
        tool_row.addWidget(QLabel("导入到:"))
        self.target_combo = QComboBox()
        self.target_combo.setMinimumWidth(90)
        tool_row.addWidget(self.target_combo, stretch=1)
        layout.addLayout(tool_row)

        btn_row = QHBoxLayout()
        self.new_btn = QPushButton("＋新建库")
        self.new_btn.clicked.connect(self._on_new_collection)
        btn_row.addWidget(self.new_btn)
        self.import_btn = QPushButton("导入PDF…")
        self.import_btn.clicked.connect(self._on_import_clicked)
        btn_row.addWidget(self.import_btn)
        self.classify_btn = QPushButton("AI 分类器")
        self.classify_btn.clicked.connect(self.classify_requested.emit)
        btn_row.addWidget(self.classify_btn)
        layout.addLayout(btn_row)

        # 库树：顶层=库（可勾选），子节点=文献
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree, stretch=1)

        hint = QLabel("勾选库限定检索范围（不勾=全部）")
        hint.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(hint)

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #666;")
        layout.addWidget(self.stats_label)

    def set_context(self, ctx: dict) -> None:
        self.ctx = ctx

    # ---- Public accessors used by the rest of the GUI ----------------------

    def target_collection(self) -> str:
        """The library new imports should go into."""
        return self.target_combo.currentText() or "默认库"

    def selected_collections(self) -> list[str] | None:
        """Checked libraries for search scope; None means all libraries."""
        checked = []
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            node = root.child(i)
            if node.checkState(0) == Qt.Checked:
                name = node.data(0, Qt.UserRole + 1)
                if name:
                    checked.append(name)
        return checked or None

    # ---- Actions -----------------------------------------------------------

    def _on_new_collection(self) -> None:
        if self.ctx is None:
            return
        name, ok = QInputDialog.getText(self, "新建文献库", "库名称：")
        name = (name or "").strip()
        if not ok or not name:
            return
        import asyncio
        asyncio.ensure_future(self._create_and_refresh(name))

    async def _create_and_refresh(self, name: str) -> None:
        await self.ctx["meta_store"].create_collection(name)
        await self.refresh()
        # 新建后把导入目标切到它，方便随即导入
        idx = self.target_combo.findText(name)
        if idx >= 0:
            self.target_combo.setCurrentIndex(idx)

    def _on_import_clicked(self) -> None:
        if self.ctx is None:
            return
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择PDF文件（可多选）", "", "PDF 文件 (*.pdf)"
        )
        if paths:
            self.import_requested.emit(self.target_collection(), list(paths))

    def get_selected_doc_ids(self) -> list[str]:
        """Return doc_ids currently selected (highlighted) in the tree."""
        ids = []
        for item in self.tree.selectedItems():
            did = item.data(0, Qt.UserRole)
            if did:
                ids.append(did)
        return ids

    def _on_item_double_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        doc_id = item.data(0, Qt.UserRole)
        if not doc_id:
            return  # a library node, not a document
        title = (item.toolTip(0) or item.text(0)).split("\n", 1)[0]
        self.summarize_requested.emit(doc_id, title)

    # ---- Refresh -----------------------------------------------------------

    async def refresh(self, ctx: dict | None = None) -> None:
        """Reload libraries + their documents into the tree."""
        if ctx is not None:
            self.ctx = ctx
        if self.ctx is None:
            return

        meta = self.ctx["meta_store"]
        names = await meta.list_collections()
        if not names:
            names = ["默认库"]

        # 记住当前勾选/展开/导入目标，刷新后尽量还原
        prev_checked = set(self.selected_collections() or [])
        prev_target = self.target_collection()

        self.tree.clear()
        total_docs = 0
        for name in names:
            docs = await meta.list_documents(collection=name, limit=100000)
            total_docs += len(docs)
            lib_node = QTreeWidgetItem(self.tree)
            lib_node.setText(0, f"{name}  ({len(docs)})")
            lib_node.setFlags(lib_node.flags() | Qt.ItemIsUserCheckable)
            lib_node.setCheckState(0, Qt.Checked if name in prev_checked else Qt.Unchecked)
            lib_node.setData(0, Qt.UserRole + 1, name)  # library name
            for doc in docs:
                d_title = doc.title or "（无标题）"
                year = doc.year if doc.year is not None else "—"
                child = QTreeWidgetItem(lib_node)
                child.setText(0, f"{d_title[:38]}  ({year})")
                child.setToolTip(0, f"{d_title}\n{doc.authors or ''}\n（双击可总结这篇）")
                child.setData(0, Qt.UserRole, doc.id)
            lib_node.setExpanded(True)

        # 刷新导入目标下拉
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        self.target_combo.addItems(names)
        idx = self.target_combo.findText(prev_target)
        self.target_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.target_combo.blockSignals(False)

        try:
            count = await self.ctx["vector_store"].count()
        except Exception:
            count = 0
        self.stats_label.setText(f"{len(names)} 个库 · {total_docs} 篇 · {count} 向量")
