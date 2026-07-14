"""LibraryPanel — browse the ingested literature library."""
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem


class LibraryPanel(QWidget):
    # 双击某篇 → 请求总结这篇（doc_id, title）
    summarize_requested = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ctx = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("文献库")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        self.list_widget = QListWidget()
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.list_widget, stretch=1)

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #666;")
        layout.addWidget(self.stats_label)

    def set_context(self, ctx: dict) -> None:
        self.ctx = ctx

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        doc_id = item.data(Qt.UserRole)
        if not doc_id:
            return
        # tooltip 首行是完整标题；退回列表显示文本。
        title = (item.toolTip() or item.text()).split("\n", 1)[0]
        self.summarize_requested.emit(doc_id, title)

    async def refresh(self, ctx: dict | None = None) -> None:
        """Reload the document list and stats from the stores."""
        if ctx is not None:
            self.ctx = ctx
        if self.ctx is None:
            return

        docs = await self.ctx["meta_store"].list_documents(limit=1000)
        self.list_widget.clear()
        for doc in docs:
            title = doc.title or "（无标题）"
            year = doc.year if doc.year is not None else "—"
            item = QListWidgetItem(f"{title[:40]}  ({year})")
            item.setToolTip(f"{title}\n{doc.authors or ''}\n（双击可总结这篇）")
            item.setData(Qt.UserRole, doc.id)
            self.list_widget.addItem(item)

        try:
            count = await self.ctx["vector_store"].count()
        except Exception:
            count = 0
        self.stats_label.setText(f"{len(docs)} 篇 · {count} 向量")
