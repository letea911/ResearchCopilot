"""ChatPanel — conversational Q&A over the literature library."""
import html
import asyncio

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QLineEdit, QPushButton,
    QInputDialog,
)
from PyQt5.QtGui import QDesktopServices, QTextCursor
from PyQt5.QtCore import QUrl, pyqtSignal

from models.message import ChatMessage, Role


class ChatPanel(QWidget):
    # (name, list_of_doc_ids) — emitted when user wants to export citations
    export_to_list_requested = pyqtSignal(str, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ctx = None
        self.history: list[ChatMessage] = []
        self._collections_provider = None  # callable -> list[str] | None

        # Citation export tracking — per-question selection state
        self._export_citations: list[dict] = []   # [{doc_id, title, file_path}]
        self._export_selected: set = set()         # indices selected

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        self.browser = QTextBrowser()
        self.browser.setReadOnly(True)
        # 不让 QTextBrowser 自己加载链接（否则会把 PDF 二进制塞进窗口显示成乱码）。
        # 改为拦截点击，用系统默认程序在外部打开。
        self.browser.setOpenLinks(False)
        self.browser.setOpenExternalLinks(False)
        self.browser.anchorClicked.connect(self._on_link_clicked)
        layout.addWidget(self.browser, stretch=1)

        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("输入问题，回车发送…")
        self.input.returnPressed.connect(self._on_send)
        input_row.addWidget(self.input, stretch=1)

        self.send_btn = QPushButton("发送")
        self.send_btn.clicked.connect(self._on_send)
        input_row.addWidget(self.send_btn)

        layout.addLayout(input_row)

        # Export row — appears after citations
        self.export_btn = QPushButton("📂 导出勾选的 0 篇为分组")
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._on_export_clicked)
        self.export_btn.setVisible(False)
        layout.addWidget(self.export_btn)

        # Disabled until the context is ready.
        self.set_input_enabled(False)

    def set_input_enabled(self, enabled: bool) -> None:
        self.input.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)

    def _on_link_clicked(self, url: QUrl) -> None:
        """Handle custom anchor clicks: file:// → open PDF, select:/deselect: → toggle export."""
        scheme = url.scheme()
        if scheme == "file":
            QDesktopServices.openUrl(url)
        elif scheme in ("select", "deselect"):
            # Custom URLs like select:0 or deselect:2 — QUrl puts the index
            # in path(), not host(). Parse the numeric suffix directly.
            raw = url.toString()
            try:
                idx = int(raw.split(":", 1)[1]) if ":" in raw else -1
            except (ValueError, IndexError):
                return
            if 0 <= idx < len(self._export_citations):
                if scheme == "select":
                    self._export_selected.add(idx)
                else:
                    self._export_selected.discard(idx)
                self._refresh_export_html()

    def set_context(self, ctx: dict) -> None:
        self.ctx = ctx
        self.set_input_enabled(True)

    def set_collections_provider(self, provider) -> None:
        """Register a callback returning the currently-selected libraries
        (list[str] or None = all) so questions can be scoped to them."""
        self._collections_provider = provider

    def _current_collections(self):
        if self._collections_provider is None:
            return None
        try:
            return self._collections_provider()
        except Exception:
            return None

    def _on_send(self) -> None:
        if self.ctx is None:
            return
        question = self.input.text().strip()
        if not question:
            return
        self.input.clear()
        self.browser.append(f"<b>你：</b> {html.escape(question)}")
        asyncio.ensure_future(self._ask(question))

    def _scroll_to_bottom(self) -> None:
        bar = self.browser.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _remove_thinking(self) -> None:
        """删掉对话末尾的“思考中…”占位块（答完后调用）。"""
        cursor = self.browser.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.BlockUnderCursor)
        cursor.removeSelectedText()
        cursor.deleteChar()  # 清掉残留的空行

    def _render_result(self, result) -> None:
        """渲染一次回答：助手正文 + 参考文献（提问/总结共用）。"""
        answer_html = html.escape(result.answer).replace("\n", "<br>")
        self.browser.append(f"<b>助手：</b> {answer_html}")

        # Reset export state for new answer
        self._export_citations.clear()
        self._export_selected.clear()

        if result.citations:
            self.browser.append("<b>参考文献：</b>")
            for i, c in enumerate(result.citations, start=1):
                # Store for export
                self._export_citations.append({
                    "doc_id": c.doc_id if hasattr(c, "doc_id") and c.doc_id else "",
                    "title": c.title or "Unknown",
                    "file_path": c.file_path or "",
                })
                idx = i - 1

                line = f"[{i}] {html.escape(c.title or 'Unknown')}"
                extras = []
                if c.section:
                    extras.append(html.escape(str(c.section)))
                if c.page_number is not None:
                    extras.append(f"p.{c.page_number}")
                if extras:
                    line += " — " + ", ".join(extras)
                if c.file_path:
                    url = "file:///" + str(c.file_path).replace("\\", "/")
                    line += f'  <a href="{url}">📄 打开PDF</a>'
                # Toggle link for export selection — use ASCII-safe markers
                # so _refresh_export_html() replacements survive Qt's HTML encoding.
                line += (
                    f'  <a href="select:{idx}" style="color:#888; '
                    f'text-decoration:none;">[ ] 标记导出</a>'
                )
                self.browser.append(line)
        self._update_export_btn()
        self._scroll_to_bottom()

    def _refresh_export_html(self) -> None:
        """Rewrite citation toggle links to reflect current selection state."""
        html_text = self.browser.toHtml()
        for i in range(len(self._export_citations)):
            selected = i in self._export_selected
            if selected:
                html_text = html_text.replace(
                    f'href="select:{i}"',
                    f'href="deselect:{i}"',
                )
                html_text = html_text.replace(
                    f'>[ ] 标记导出</a>',
                    f'>[x] 已选</a>',
                )
            else:
                html_text = html_text.replace(
                    f'href="deselect:{i}"',
                    f'href="select:{i}"',
                )
                html_text = html_text.replace(
                    f'>[x] 已选</a>',
                    f'>[ ] 标记导出</a>',
                )
        self.browser.setHtml(html_text)
        self._update_export_btn()

    def _update_export_btn(self) -> None:
        n = len(self._export_selected)
        if n > 0:
            self.export_btn.setText(f"📂 导出勾选的 {n} 篇为分组")
            self.export_btn.setEnabled(True)
            self.export_btn.setVisible(True)
        elif self._export_citations:
            self.export_btn.setText("📂 导出勾选的 0 篇为分组")
            self.export_btn.setEnabled(False)
            self.export_btn.setVisible(True)
        else:
            self.export_btn.setVisible(False)

    def _on_export_clicked(self) -> None:
        if not self._export_selected or self.ctx is None:
            return
        name, ok = QInputDialog.getText(
            self, "导出为分组", "新分组名称："
        )
        name = (name or "").strip()
        if not ok or not name:
            return
        doc_ids = [
            self._export_citations[i]["doc_id"]
            for i in sorted(self._export_selected)
            if self._export_citations[i].get("doc_id")
        ]
        if doc_ids:
            self.export_to_list_requested.emit(name, doc_ids)
            self.export_btn.setText("✅ 已导出")
            self.export_btn.setEnabled(False)

    async def _ask(self, question: str) -> None:
        self.set_input_enabled(False)
        collections = self._current_collections()
        if collections:
            self.browser.append(
                f"<span style='color:#888;'>（检索范围：{html.escape('、'.join(collections))}）</span>"
            )
        self.browser.append("<i>思考中…</i>")
        self._scroll_to_bottom()
        try:
            result = await self.ctx["chat"].ask(
                question,
                conversation_history=self.history[-6:],
                top_k=10,
                collections=collections,
            )
            self._remove_thinking()
            self._render_result(result)

            # Maintain in-memory conversation history, trimmed to last 6 messages.
            self.history.append(ChatMessage(role=Role.USER, content=question))
            self.history.append(ChatMessage(role=Role.ASSISTANT, content=result.answer))
            self.history = self.history[-6:]
        except Exception as exc:  # noqa: BLE001
            self._remove_thinking()
            self.browser.append(
                f"<span style='color:red;'>出错了：{html.escape(str(exc))}</span>"
            )
            self._scroll_to_bottom()
        finally:
            self.set_input_enabled(True)
            self.input.setFocus()

    # ---- Summarize one paper (triggered by double-clicking the library) -----

    def request_summary(self, doc_id: str, title: str) -> None:
        """槽：库面板双击某篇 → 在聊天区总结这篇。"""
        if self.ctx is None:
            return
        self.browser.append(f"<b>你：</b> 总结这篇 —— {html.escape(title or '')}")
        self.browser.append("<i>思考中…</i>")
        self._scroll_to_bottom()
        asyncio.ensure_future(self._summarize(doc_id))

    async def _summarize(self, doc_id: str) -> None:
        self.set_input_enabled(False)
        try:
            result = await self.ctx["summarize"].summarize(doc_id)
            self._remove_thinking()
            self._render_result(result)
        except Exception as exc:  # noqa: BLE001
            self._remove_thinking()
            self.browser.append(
                f"<span style='color:red;'>总结失败：{html.escape(str(exc))}</span>"
            )
            self._scroll_to_bottom()
        finally:
            self.set_input_enabled(True)
            self.input.setFocus()
