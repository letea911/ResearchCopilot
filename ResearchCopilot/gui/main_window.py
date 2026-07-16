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

        # 双击左侧文献 → 聊天区总结这篇
        self.library_panel.summarize_requested.connect(self.chat_panel.request_summary)
        # 「导入PDF…」选好文件 → 导入到目标库
        self.library_panel.import_requested.connect(self._on_import_requested)
        # 「AI 分类器」按钮 → 打开分类对话框
        self.library_panel.classify_requested.connect(self._on_classify_requested)
        # 聊天区「导出为分组」→ 创建 reading list
        self.chat_panel.export_to_list_requested.connect(self._on_export_to_list)

        self.setCentralWidget(central)

        asyncio.ensure_future(self._startup())

    def set_status(self, text: str) -> None:
        self.status_label.setText(text)

    async def _startup(self) -> None:
        loop = asyncio.get_event_loop()
        # build_context() is sync construction → run off UI thread
        ctx = await loop.run_in_executor(None, build_context)
        await initialize_stores(ctx)

        # Warm up the embedder in the background — don't block the UI.
        # The model loads off-thread (run_in_executor), so it won't freeze the
        # window, but waiting for it delays the "就绪" state. We fire-and-forget
        # here so the user can start browsing immediately; the first query will
        # be slightly slower if warmup hasn't finished yet.
        async def _warmup():
            try:
                await ctx["embedder"].embed(["warmup"])
            except Exception:
                pass

        self._warmup_task = asyncio.ensure_future(_warmup())

        self.ctx = ctx
        self.chat_panel.set_context(ctx)
        self.chat_panel.set_collections_provider(self.library_panel.selected_collections)
        self.library_panel.set_context(ctx)
        await self.library_panel.refresh(ctx)

        docs = await ctx["meta_store"].list_documents(limit=1000)
        try:
            count = await ctx["vector_store"].count()
        except Exception:
            count = 0
        self.set_status(f"就绪 · {len(docs)}篇文献 {count}向量（模型后台加载中）")

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
        collection = self.library_panel.target_collection()
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.lower().endswith(".pdf"):
                asyncio.ensure_future(self._ingest_file(path, collection))
        event.acceptProposedAction()

    def _on_import_requested(self, collection: str, paths: list) -> None:
        """「导入PDF…」按钮选好文件后逐个导入到目标库。"""
        if self.ctx is None:
            self.set_status("还在加载模型，请稍候")
            return
        for path in paths:
            if str(path).lower().endswith(".pdf"):
                asyncio.ensure_future(self._ingest_file(path, collection))

    def _on_classify_requested(self):
        """Open the AI classifier dialog."""
        if self.ctx is None:
            self.set_status("还在加载模型，请稍候")
            return
        from gui.classifier_dialog import ClassifierDialog
        dlg = ClassifierDialog(self.ctx, self.library_panel, self)
        dlg.exec_()
        if dlg.was_saved():
            asyncio.ensure_future(self.library_panel.refresh(self.ctx))

    def _on_export_to_list(self, name: str, doc_ids: list, existing_list_id: str = "") -> None:
        """聊天区导出勾选文献 → 创建/追加阅读清单。"""
        if self.ctx is None:
            return
        asyncio.ensure_future(self._do_export_to_list(name, doc_ids, existing_list_id))

    async def _do_export_to_list(self, name: str, doc_ids: list, existing_list_id: str = "") -> None:
        meta = self.ctx["meta_store"]
        if existing_list_id:
            # Add to existing reading list
            added = await meta.add_to_reading_list(existing_list_id, doc_ids)
            self.set_status(f"已添加 {added} 篇到「{name}」")
        else:
            # Create new reading list
            lid = await meta.create_reading_list(name)
            if lid:
                added = await meta.add_to_reading_list(lid, doc_ids)
                self.set_status(f"已创建阅读清单「{name}」({added}篇)")
            else:
                self.set_status("创建清单失败")
                return
        await self.library_panel.refresh(self.ctx)

    async def _ingest_file(self, path: str, collection: str = "默认库") -> None:
        if self.ctx is None:
            self.set_status("还在加载模型，请稍候")
            return
        name = Path(path).name
        self.set_status(f"正在导入 {name} → {collection}…")
        try:
            await self.ctx["pipeline"].ingest(Path(path), collection=collection)
            await self.library_panel.refresh(self.ctx)
            self.set_status(f"导入完成: {name} → {collection}")
        except Exception as exc:  # noqa: BLE001
            self.set_status(f"导入失败 {name}: {exc}")
