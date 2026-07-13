"""LibraryPanel — browse the ingested literature library."""
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem


class LibraryPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ctx = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        title = QLabel("文献库")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget, stretch=1)

        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("color: #666;")
        layout.addWidget(self.stats_label)

    def set_context(self, ctx: dict) -> None:
        self.ctx = ctx

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
            item.setToolTip(f"{title}\n{doc.authors or ''}")
            item.setData(Qt.UserRole, doc.id)
            self.list_widget.addItem(item)

        try:
            count = await self.ctx["vector_store"].count()
        except Exception:
            count = 0
        self.stats_label.setText(f"{len(docs)} 篇 · {count} 向量")
