"""MainWindow — top-level window wiring the library + chat panels."""
import asyncio
from pathlib import Path

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QLabel, QSplitter
)
from PyQt5.QtCore import Qt

from core.context import build_context, initialize_stores
from gui.library_panel import LibraryPanel
from gui.chat_panel import ChatPanel


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ctx = None
        self.setWindowTitle("ResearchCopilot")
        self.resize(1000, 680)
        self.setAcceptDrops(True)

        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)

        self.status_label = QLabel("模型加载中，请稍候…")
        self.status_label.setStyleSheet(
            "padding: 6px 10px; background: #f0f0f0; border-bottom: 1px solid #ddd;"
        )
        outer.addWidget(self.status_label)

        splitter = QSplitter(Qt.Horizontal)
        self.library_panel = LibraryPanel()
        self.library_panel.setMinimumWidth(240)
        self.library_panel.setMaximumWidth(320)
        self.chat_panel = ChatPanel()

        splitter.addWidget(self.library_panel)
        splitter.addWidget(self.chat_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([280, 720])
        outer.addWidget(splitter, stretch=1)

        self.setCentralWidget(central)

        asyncio.ensure_future(self._startup())

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    async def _startup(self) -> None:
        loop = asyncio.get_event_loop()
        # build_context() is sync + slow (model construction) → run off the UI thread.
        ctx = await loop.run_in_executor(None, build_context)
        await initialize_stores(ctx)

        # Warm up the embedder so the sentence-transformers model loads off the
        # UI thread (first embed can take tens of seconds).
        try:
            await ctx["embedder"].embed(["warmup"])
        except Exception:
            pass

        self.ctx = ctx
        self.chat_panel.set_context(ctx)
        self.library_panel.set_context(ctx)
        await self.library_panel.refresh(ctx)

        docs = await ctx["meta_store"].list_documents(limit=1000)
        try:
            count = await ctx["vector_store"].count()
        except Exception:
            count = 0
        self.set_status(f"就绪 · {len(docs)}篇文献 {count}向量")

    # ---- Drag & drop ingest -------------------------------------------------

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(".pdf"):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        if self.ctx is None:
            self.set_status("还在加载模型，请稍候")
            event.ignore()
            return
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".pdf"):
                asyncio.ensure_future(self._ingest_file(path))
        event.acceptProposedAction()

    async def _ingest_file(self, path: str) -> None:
        if self.ctx is None:
            self.set_status("还在加载模型，请稍候")
            return
        name = Path(path).name
        self.set_status(f"正在导入 {name}…")
        try:
            await self.ctx["pipeline"].ingest(Path(path))
            await self.library_panel.refresh(self.ctx)
            self.set_status(f"导入完成: {name}")
        except Exception as exc:  # noqa: BLE001
            self.set_status(f"导入失败 {name}: {exc}")
