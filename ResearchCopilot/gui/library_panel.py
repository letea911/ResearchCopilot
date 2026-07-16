"""LibraryPanel — browse nested libraries (collections) and their documents."""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTreeWidget, QTreeWidgetItem, QInputDialog, QFileDialog, QMessageBox,
    QMenu, QAbstractItemView,
)
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl


class LibraryPanel(QWidget):
    summarize_requested = pyqtSignal(str, str)   # (doc_id, title)
    import_requested = pyqtSignal(str, list)      # (collection, file_paths)
    classify_requested = pyqtSignal()             # open classifier dialog

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ctx = None
        self._block_signals = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("文献库")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        # Top row: import target combo
        tool_row = QHBoxLayout()
        tool_row.addWidget(QLabel("导入到:"))
        self.target_combo = QComboBox()
        self.target_combo.setMinimumWidth(90)
        tool_row.addWidget(self.target_combo, stretch=1)
        layout.addLayout(tool_row)

        # Button row
        btn_row = QHBoxLayout()
        self.new_btn = QPushButton("＋新建父库")
        self.new_btn.clicked.connect(self._on_new_parent)
        btn_row.addWidget(self.new_btn)
        self.import_btn = QPushButton("导入PDF…")
        self.import_btn.clicked.connect(self._on_import_clicked)
        btn_row.addWidget(self.import_btn)
        self.classify_btn = QPushButton("AI 分类器")
        self.classify_btn.clicked.connect(self.classify_requested.emit)
        btn_row.addWidget(self.classify_btn)
        layout.addLayout(btn_row)

        # Tree: root libraries → sub-libraries → documents
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.itemChanged.connect(self._on_item_changed)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_context_menu)
        # Drag & drop: allow documents to be dragged between libraries
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDropIndicatorShown(True)
        self.tree.setDragDropMode(QAbstractItemView.InternalMove)
        layout.addWidget(self.tree, stretch=1)

        hint = QLabel("单击文献总结 · 双击改名 · 右键更多 · 拖动换库")
        hint.setStyleSheet("color: #999; font-size: 11px;")
        layout.addWidget(hint)

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #666;")
        layout.addWidget(self.stats_label)

    def set_context(self, ctx: dict) -> None:
        self.ctx = ctx

    # ---- Public accessors ---------------------------------------------------

    def target_collection(self) -> str:
        text = self.target_combo.currentText() or "默认库"
        # Strip arrow notation to get the leaf name
        if "→" in text:
            return text.split("→")[-1].strip()
        return text

    def selected_collections(self) -> list[str] | None:
        """Checked leaf library names; None = all."""
        checked = []
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            root_node = root.child(i)
            for j in range(root_node.childCount()):
                child = root_node.child(j)
                if child.data(0, Qt.UserRole + 1) and child.checkState(0) == Qt.Checked:
                    checked.append(child.data(0, Qt.UserRole + 1))
            # Root-level documents go in a pseudo child with name == root name
            for j in range(root_node.childCount()):
                child = root_node.child(j)
                if not child.data(0, Qt.UserRole + 1) and child.data(0, Qt.UserRole):
                    # This child is a document (has doc_id, no library name)
                    pass  # root-level docs only counted when root is checked
            if root_node.checkState(0) == Qt.Checked and not any(
                root_node.child(j).data(0, Qt.UserRole + 1)
                for j in range(root_node.childCount())
            ):
                checked.append(root_node.data(0, Qt.UserRole + 1))
        return checked or None

    def get_selected_doc_ids(self) -> list[str]:
        ids = []
        for item in self.tree.selectedItems():
            did = item.data(0, Qt.UserRole)
            if did:
                ids.append(did)
        return ids

    # ---- Actions ------------------------------------------------------------

    def _on_new_parent(self) -> None:
        """Create a new root-level (parent) library. No parent selection needed."""
        if self.ctx is None:
            return
        name, ok = QInputDialog.getText(self, "新建父库", "父库名称：")
        name = (name or "").strip()
        if not ok or not name:
            return
        import asyncio
        asyncio.ensure_future(self._create_and_refresh(name, parent=None))

    def _on_context_menu(self, pos) -> None:
        """Right-click context menu on tree items."""
        item = self.tree.itemAt(pos)
        if item is None or self.ctx is None:
            return

        lib_name = item.data(0, Qt.UserRole + 1)  # library name (or reading list name)
        doc_id = item.data(0, Qt.UserRole)          # doc_id if this is a document node
        list_id = item.data(0, Qt.UserRole + 2)     # reading_list id if applicable
        is_rl_header = list_id == "__reading_list_header__"

        if doc_id:
            # Document node — always show full context menu
            menu = QMenu(self)
            menu.addAction("📄 打开PDF")
            menu.addAction("✏ 重命名")
            if list_id and not is_rl_header:
                menu.addAction("从清单移除")
            menu.addSeparator()
            menu.addAction("🗑 删除文献")
            action = menu.exec_(self.tree.viewport().mapToGlobal(pos))
            if action is None:
                return
            import asyncio
            action_text = action.text()
            if action_text == "📄 打开PDF":
                self._open_doc_pdf(doc_id)
            elif action_text == "✏ 重命名":
                self._rename_document(item, doc_id)
            elif action_text == "从清单移除":
                asyncio.ensure_future(self._do_remove_from_list(list_id, doc_id))
            elif action_text == "🗑 删除文献":
                self._on_delete_document(item, doc_id)
            return

        if not lib_name or is_rl_header:
            return

        # Is this a reading list or a regular library?
        if list_id:
            # Reading list node
            menu = QMenu(self)
            rename_action = menu.addAction("重命名")
            delete_action = menu.addAction("删除清单")
            action = menu.exec_(self.tree.viewport().mapToGlobal(pos))
            if action == rename_action:
                self._rename_library(item)
            elif action == delete_action:
                self._on_delete_reading_list(list_id, lib_name)
            return

        # Regular library node
        menu = QMenu(self)

        # Determine if this is a root library
        parent = item.parent()
        is_root = parent is None or parent is self.tree.invisibleRootItem()

        if is_root:
            menu.addAction("＋新建子库")
        menu.addAction("重命名")
        menu.addSeparator()
        delete_action = menu.addAction("删除库")

        action = menu.exec_(self.tree.viewport().mapToGlobal(pos))
        if action is None:
            return

        import asyncio
        if is_root and action.text() == "＋新建子库":
            asyncio.ensure_future(self._async_new_sub(lib_name))
        elif action.text() == "重命名":
            self._rename_library(item)
        elif action == delete_action:
            self._on_delete_collection(lib_name, is_root)

    async def _async_new_sub(self, parent_name: str) -> None:
        """Create a sub-library under a parent library."""
        name, ok = QInputDialog.getText(
            self, "新建子库", f"在「{parent_name}」下新建子库："
        )
        name = (name or "").strip()
        if not ok or not name:
            return
        await self.ctx["meta_store"].create_collection(name, parent=parent_name)
        await self.refresh()

    def _on_delete_collection(self, lib_name: str, is_root: bool) -> None:
        """Confirm and delete a library. Documents are released to 默认库."""
        if self.ctx is None:
            return
        # Confirm
        level = "父库" if is_root else "子库"
        msg = f"删除{level}「{lib_name}」？\n\n库中的文献会自动移到「默认库」。\n此操作不可撤销。"
        reply = QMessageBox.question(
            self, "确认删除", msg,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        import asyncio
        asyncio.ensure_future(self._do_delete(lib_name))

    async def _do_delete(self, lib_name: str) -> None:
        meta = self.ctx["meta_store"]
        vec = self.ctx["vector_store"]
        moved = await meta.delete_collection(lib_name, reassign_to="默认库")
        # Update vector metadata for documents that were reassigned
        if moved > 0:
            try:
                await vec.update_metadata_by_filter(
                    where={"collection": lib_name},
                    updates={"collection": "默认库"},
                )
            except Exception:
                pass
        await self.refresh()

    # ---- Reading list actions ----------------------------------------------

    def _on_delete_reading_list(self, list_id: str, name: str) -> None:
        reply = QMessageBox.question(
            self, "确认删除", f"删除阅读清单「{name}」？\n\n清单中的文献不会被删除。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        import asyncio
        asyncio.ensure_future(self._do_delete_list(list_id))

    async def _do_delete_list(self, list_id: str) -> None:
        await self.ctx["meta_store"].delete_reading_list(list_id)
        await self.refresh()

    async def _do_remove_from_list(self, list_id: str, doc_id: str) -> None:
        await self.ctx["meta_store"].remove_from_reading_list(list_id, doc_id)
        await self.refresh()

    def _open_doc_pdf(self, doc_id: str) -> None:
        """Fetch document by ID and open its PDF with system viewer."""
        import asyncio
        asyncio.ensure_future(self._do_open_pdf(doc_id))

    async def _do_open_pdf(self, doc_id: str) -> None:
        doc = await self.ctx["meta_store"].get_document(doc_id)
        if doc and doc.file_path:
            from PyQt5.QtGui import QDesktopServices
            from PyQt5.QtCore import QUrl
            url = "file:///" + str(doc.file_path).replace("\\", "/")
            QDesktopServices.openUrl(QUrl(url))

    async def _create_and_refresh(self, name: str, parent: str | None) -> None:
        await self.ctx["meta_store"].create_collection(name, parent=parent)
        await self.refresh()
        idx = self.target_combo.findText(name)
        if idx >= 0:
            self.target_combo.setCurrentIndex(idx)

    # ---- Document actions --------------------------------------------------

    def _rename_document(self, item: QTreeWidgetItem, doc_id: str) -> None:
        """Double-click document → rename its title."""
        old_title = (item.toolTip(0) or item.text(0)).split("\n", 1)[0]
        new_title, ok = QInputDialog.getText(
            self, "重命名文献", "新标题：", text=old_title
        )
        new_title = (new_title or "").strip()
        if not ok or not new_title or new_title == old_title:
            return
        import asyncio
        asyncio.ensure_future(self._do_rename_doc(doc_id, new_title))

    async def _do_rename_doc(self, doc_id: str, new_title: str) -> None:
        meta = self.ctx["meta_store"]
        await meta.update_document_metadata(doc_id, title=new_title)
        await self.refresh()

    def _on_delete_document(self, item: QTreeWidgetItem, doc_id: str) -> None:
        """Right-click → delete document after confirmation."""
        title = (item.toolTip(0) or item.text(0)).split("\n", 1)[0]
        reply = QMessageBox.question(
            self, "确认删除",
            f"删除文献「{title[:60]}」？\n\n此操作不可撤销，文献将从库中移除。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        import asyncio
        asyncio.ensure_future(self._do_delete_doc(doc_id))

    async def _do_delete_doc(self, doc_id: str) -> None:
        meta = self.ctx["meta_store"]
        vec = self.ctx["vector_store"]
        # Get chunks to delete vectors
        chunks = await meta.get_chunks_by_document(doc_id)
        chroma_ids = [c.chroma_id for c in chunks if c.chroma_id]
        if chroma_ids:
            try:
                await vec.delete(chroma_ids)
            except Exception:
                pass
        await meta.delete_document(doc_id)
        await self.refresh()

    # ---- Drag & drop: move document between libraries ----------------------

    def dropEvent(self, event) -> None:
        """Handle document dragged onto a library node → move to that library."""
        target_item = self.tree.itemAt(event.pos())
        if target_item is None or self.ctx is None:
            event.ignore()
            return

        # Find the target collection name
        target_col = target_item.data(0, Qt.UserRole + 1)  # sub-library or root name
        if not target_col:
            # Maybe dropped on a document inside a library — use its parent's collection
            parent = target_item.parent()
            if parent:
                target_col = parent.data(0, Qt.UserRole + 1)

        if not target_col:
            event.ignore()
            return

        # Get dragged document IDs
        doc_ids = []
        for item in self.tree.selectedItems():
            did = item.data(0, Qt.UserRole)
            if did:
                doc_ids.append(did)

        if not doc_ids:
            event.ignore()
            return

        import asyncio
        asyncio.ensure_future(self._do_move_docs(doc_ids, target_col))
        event.accept()

    async def _do_move_docs(self, doc_ids: list[str], target_col: str) -> None:
        meta = self.ctx["meta_store"]
        vec = self.ctx["vector_store"]
        for did in doc_ids:
            await meta.update_document_metadata(did, collection=target_col)
            try:
                await vec.update_metadata_by_filter(
                    where={"document_id": did},
                    updates={"collection": target_col},
                )
            except Exception:
                pass
        await self.refresh()

    # ----------------------------------------------------------------------
        if self.ctx is None:
            return
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择PDF文件（可多选）", "", "PDF 文件 (*.pdf)"
        )
        if paths:
            self.import_requested.emit(self.target_collection(), list(paths))

    def _on_item_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        """Single click on a document → summarize in chat panel."""
        doc_id = item.data(0, Qt.UserRole)
        if not doc_id:
            return  # library node, ignore single click
        title = (item.toolTip(0) or item.text(0)).split("\n", 1)[0]
        self.summarize_requested.emit(doc_id, title)

    def _on_item_double_clicked(self, item: QTreeWidgetItem, _column: int) -> None:
        doc_id = item.data(0, Qt.UserRole)
        if doc_id:
            # Document node — rename title
            self._rename_document(item, doc_id)
            return
        # Library node — rename library
        self._rename_library(item)

    def _rename_library(self, item: QTreeWidgetItem) -> None:
        if self.ctx is None:
            return
        old_name = item.data(0, Qt.UserRole + 1)
        if not old_name:
            return
        list_id = item.data(0, Qt.UserRole + 2)
        title = "重命名阅读清单" if list_id else "重命名文献库"
        new_name, ok = QInputDialog.getText(
            self, title, "新名称：", text=old_name
        )
        new_name = (new_name or "").strip()
        if not ok or not new_name or new_name == old_name:
            return
        import asyncio
        asyncio.ensure_future(self._do_rename(old_name, new_name, list_id))

    async def _do_rename(self, old_name: str, new_name: str, list_id: str | None = None) -> None:
        meta = self.ctx["meta_store"]
        if list_id:
            await meta.rename_reading_list(list_id, new_name)
        else:
            vec = self.ctx["vector_store"]
            ok = await meta.rename_collection(old_name, new_name)
            if not ok:
                return
            try:
                await vec.update_metadata_by_filter(
                    where={"collection": old_name},
                    updates={"collection": new_name},
                )
            except Exception:
                pass
        await self.refresh()

    # ---- Checkbox propagation -----------------------------------------------

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        if self._block_signals:
            return
        self._block_signals = True
        try:
            # Propagate parent → children
            for i in range(item.childCount()):
                child = item.child(i)
                if child.data(0, Qt.UserRole + 1):  # sub-library node
                    child.setCheckState(0, item.checkState(0))
            # Update parent state based on children
            parent = item.parent()
            if parent and parent.data(0, Qt.UserRole + 1):
                self._update_parent_checkstate(parent)
        finally:
            self._block_signals = False

    def _update_parent_checkstate(self, parent: QTreeWidgetItem) -> None:
        checked = 0
        total = 0
        for i in range(parent.childCount()):
            child = parent.child(i)
            if child.data(0, Qt.UserRole + 1):  # only sub-libraries count
                total += 1
                if child.checkState(0) == Qt.Checked:
                    checked += 1
        if total == 0:
            return
        if checked == total:
            parent.setCheckState(0, Qt.Checked)
        elif checked == 0:
            parent.setCheckState(0, Qt.Unchecked)
        else:
            parent.setCheckState(0, Qt.PartiallyChecked)

    # ---- Refresh ------------------------------------------------------------

    async def refresh(self, ctx: dict | None = None) -> None:
        if ctx is not None:
            self.ctx = ctx
        if self.ctx is None:
            return

        meta = self.ctx["meta_store"]
        tree_data = await meta.get_collection_tree()

        self._block_signals = True
        try:
            prev_target = self.target_combo.currentText()
            self.tree.clear()
            total_docs = 0
            all_display_items = []  # (display_text, leaf_name) for combo

            for node in tree_data:
                root_name = node["name"]
                children = node.get("children", [])

                # Root library node
                root_item = QTreeWidgetItem(self.tree)
                root_item.setFlags(root_item.flags() | Qt.ItemIsUserCheckable)

                if children:
                    # Has sub-libraries — show them AND any docs belonging
                    # directly to the parent (so they don't vanish).
                    parent_docs = await meta.list_documents(
                        collection=root_name, limit=100000
                    )
                    total_docs += len(parent_docs)

                    for sub_name in children:
                        docs = await meta.list_documents(
                            collection=sub_name, limit=100000
                        )
                        sub_item = QTreeWidgetItem(root_item)
                        sub_item.setText(0, f"  {sub_name}  ({len(docs)})")
                        sub_item.setFlags(sub_item.flags() | Qt.ItemIsUserCheckable)
                        sub_item.setCheckState(0, Qt.Checked)
                        sub_item.setData(0, Qt.UserRole + 1, sub_name)
                        sub_item.setToolTip(0, f"「{root_name} → {sub_name}」\n右键可删除或重命名")
                        all_display_items.append(
                            (f"{root_name} → {sub_name}", sub_name)
                        )
                        total_docs += len(docs)
                        for doc in docs:
                            d_title = doc.title or "（无标题）"
                            year = doc.year if doc.year is not None else "—"
                            child = QTreeWidgetItem(sub_item)
                            child.setText(0, f"{d_title[:38]}  ({year})")
                            child.setToolTip(
                                0,
                                f"{d_title}\n{doc.authors or ''}\n（双击可总结这篇）",
                            )
                            child.setData(0, Qt.UserRole, doc.id)
                    # Show documents that belong directly to the parent
                    for doc in parent_docs:
                        d_title = doc.title or "（无标题）"
                        year = doc.year if doc.year is not None else "—"
                        child = QTreeWidgetItem(root_item)
                        child.setText(0, f"{d_title[:38]}  ({year})")
                        child.setToolTip(
                            0,
                            f"{d_title}\n{doc.authors or ''}\n（双击可总结这篇）",
                        )
                        child.setData(0, Qt.UserRole, doc.id)
                    # Parent display: sub_count + parent_docs
                    sub_count = len(children)
                    root_item.setText(
                        0,
                        f"{root_name}  ({sub_count}子库, {len(parent_docs)}篇)"
                    )
                    root_item.setCheckState(0, Qt.Checked if children else Qt.Unchecked)
                else:
                    # No sub-libraries — docs directly under root
                    docs = await meta.list_documents(
                        collection=root_name, limit=100000
                    )
                    total_docs += len(docs)
                    root_item.setCheckState(0, Qt.Checked)
                    all_display_items.append((root_name, root_name))
                    for doc in docs:
                        d_title = doc.title or "（无标题）"
                        year = doc.year if doc.year is not None else "—"
                        child = QTreeWidgetItem(root_item)
                        child.setText(0, f"{d_title[:38]}  ({year})")
                        child.setToolTip(
                            0,
                            f"{d_title}\n{doc.authors or ''}\n（双击可总结这篇）",
                        )
                        child.setData(0, Qt.UserRole, doc.id)

                root_item.setText(0, f"{root_name}  ({len(children) if children else len(docs)})")
                root_item.setData(0, Qt.UserRole + 1, root_name)
                root_item.setToolTip(0, f"「{root_name}」\n（双击可重命名）")
                root_item.setExpanded(True)

            # ---- Reading Lists (virtual groups) ----
            reading_lists = await meta.get_reading_lists()
            if reading_lists:
                # Section header
                rl_header = QTreeWidgetItem(self.tree)
                rl_header.setText(0, f"📋 阅读清单  ({len(reading_lists)})")
                rl_header.setFlags(rl_header.flags() & ~Qt.ItemIsUserCheckable)
                rl_header.setData(0, Qt.UserRole + 2, "__reading_list_header__")
                rl_header.setExpanded(True)

                for rl in reading_lists:
                    rl_item = QTreeWidgetItem(rl_header)
                    rl_item.setText(0, f"{rl['name']}  ({rl.get('doc_count', 0)}篇)")
                    rl_item.setFlags(rl_item.flags() & ~Qt.ItemIsUserCheckable)
                    rl_item.setData(0, Qt.UserRole + 2, rl["id"])  # list_id
                    rl_item.setData(0, Qt.UserRole + 1, rl["name"])  # for rename
                    rl_item.setToolTip(0, f"阅读清单：{rl['name']}\n右键可重命名或删除")

                    # Show documents in this list
                    rl_docs = await meta.get_reading_list_items(rl["id"])
                    total_docs += len(rl_docs)
                    for doc in rl_docs:
                        d_title = doc.title or "（无标题）"
                        year = doc.year if doc.year is not None else "—"
                        child = QTreeWidgetItem(rl_item)
                        child.setText(0, f"{d_title[:38]}  ({year})")
                        child.setToolTip(
                            0,
                            f"{d_title}\n{doc.authors or ''}\n（双击可总结这篇，右键跳转PDF）",
                        )
                        child.setData(0, Qt.UserRole, doc.id)
                        child.setData(0, Qt.UserRole + 2, rl["id"])  # parent list

            # Repopulate import target combo
            self.target_combo.blockSignals(True)
            self.target_combo.clear()
            for display, _leaf in all_display_items:
                self.target_combo.addItem(display)
            idx = self.target_combo.findText(prev_target)
            self.target_combo.setCurrentIndex(idx if idx >= 0 else 0)
            self.target_combo.blockSignals(False)

            try:
                count = await self.ctx["vector_store"].count()
            except Exception:
                count = 0
            self.stats_label.setText(
                f"{len(tree_data)} 个根库 · {total_docs} 篇 · {count} 向量"
            )
        finally:
            self._block_signals = False
