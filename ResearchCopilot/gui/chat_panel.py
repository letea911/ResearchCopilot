"""ChatPanel — conversational Q&A over the literature library."""
import html
import asyncio

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QLineEdit, QPushButton
)
from PyQt5.QtGui import QDesktopServices, QTextCursor
from PyQt5.QtCore import QUrl

from models.message import ChatMessage, Role


class ChatPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ctx = None
        self.history: list[ChatMessage] = []

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

        # Disabled until the context is ready.
        self.set_input_enabled(False)

    def set_input_enabled(self, enabled: bool) -> None:
        self.input.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)

    def _on_link_clicked(self, url: QUrl) -> None:
        """打开引用链接：用系统默认程序在外部打开（PDF 用系统阅读器）。"""
        QDesktopServices.openUrl(url)

    def set_context(self, ctx: dict) -> None:
        self.ctx = ctx
        self.set_input_enabled(True)

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

        if result.citations:
            self.browser.append("<b>参考文献：</b>")
            for i, c in enumerate(result.citations, start=1):
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
                self.browser.append(line)
        self._scroll_to_bottom()

    async def _ask(self, question: str) -> None:
        self.set_input_enabled(False)
        self.browser.append("<i>思考中…</i>")
        self._scroll_to_bottom()
        try:
            result = await self.ctx["chat"].ask(
                question,
                conversation_history=self.history[-6:],
                top_k=10,
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
