"""ChatPanel — conversational Q&A over the literature library."""
import html
import asyncio

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextBrowser, QLineEdit, QPushButton
)

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
        self.browser.setOpenExternalLinks(True)
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

    async def _ask(self, question: str) -> None:
        self.set_input_enabled(False)
        self.browser.append("<i>思考中…</i>")
        try:
            result = await self.ctx["chat"].ask(
                question,
                conversation_history=self.history[-6:],
                top_k=10,
            )

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

            # Maintain in-memory conversation history, trimmed to last 6 messages.
            self.history.append(ChatMessage(role=Role.USER, content=question))
            self.history.append(ChatMessage(role=Role.ASSISTANT, content=result.answer))
            self.history = self.history[-6:]
        except Exception as exc:  # noqa: BLE001
            self.browser.append(
                f"<span style='color:red;'>出错了：{html.escape(str(exc))}</span>"
            )
        finally:
            self.set_input_enabled(True)
            self.input.setFocus()
