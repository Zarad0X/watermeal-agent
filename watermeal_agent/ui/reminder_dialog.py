from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class ReminderDialog(QDialog):
    action_selected = Signal(str)

    def __init__(self, reminder_type: str, snooze_minutes: int, parent=None) -> None:
        super().__init__(parent)
        self.reminder_type = reminder_type
        self.snooze_minutes = snooze_minutes
        self.setWindowTitle(self._title())
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.setModal(False)
        self.resize(320, 150)

        message = QLabel(self._message())
        message.setWordWrap(True)

        buttons = QDialogButtonBox()
        done_button = QPushButton(self._done_label())
        snooze_button = QPushButton(f"{self.snooze_minutes} 分钟后提醒")
        skip_button = QPushButton("今天跳过")

        buttons.addButton(done_button, QDialogButtonBox.AcceptRole)
        buttons.addButton(snooze_button, QDialogButtonBox.ActionRole)
        buttons.addButton(skip_button, QDialogButtonBox.DestructiveRole)

        done_button.clicked.connect(lambda: self._select("done"))
        snooze_button.clicked.connect(lambda: self._select("snooze"))
        skip_button.clicked.connect(lambda: self._select("skip"))

        layout = QVBoxLayout()
        layout.addWidget(message)
        layout.addStretch()
        layout.addWidget(buttons)
        self.setLayout(layout)

    def _select(self, action: str) -> None:
        self.action_selected.emit(action)
        self.close()

    def _title(self) -> str:
        if self.reminder_type == "water":
            return "喝水提醒"
        if self.reminder_type == "lunch":
            return "午饭提醒"
        return "晚饭提醒"

    def _message(self) -> str:
        if self.reminder_type == "water":
            return "该喝水了。现在补充一点水分。"
        if self.reminder_type == "lunch":
            return "到午饭时间了。记得按时吃饭。"
        return "到晚饭时间了。记得按时吃饭。"

    def _done_label(self) -> str:
        return "我喝了" if self.reminder_type == "water" else "我吃了"
