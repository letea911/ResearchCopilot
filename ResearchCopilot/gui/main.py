"""Entry point for the ResearchCopilot desktop GUI.

Run via:  PYTHONPATH=. python -m gui.main
"""
import sys
import asyncio

import qasync
from PyQt5.QtWidgets import QApplication

from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    main()
