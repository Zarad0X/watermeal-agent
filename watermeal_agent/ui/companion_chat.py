from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class ChatBubble(QWidget):
    def __init__(self, sender: str, text: str, is_user: bool, max_width: int) -> None:
        super().__init__()
        self.is_user = is_user
        self.card = QFrame()
        self.card.setObjectName("userBubble" if is_user else "petBubble")

        self.sender_label = QLabel(sender)
        self.sender_label.setObjectName("senderLabel")
        self.message_label = QLabel(text)
        self.message_label.setWordWrap(True)
        self.message_label.setObjectName("messageLabel")
        self.message_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(10, 8, 10, 10)
        card_layout.setSpacing(4)
        card_layout.addWidget(self.sender_label)
        card_layout.addWidget(self.message_label)
        self.card.setLayout(card_layout)

        self.card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        root = QHBoxLayout()
        root.setContentsMargins(2, 2, 2, 2)
        if is_user:
            root.addStretch()
            root.addWidget(self.card, 0, Qt.AlignRight)
        else:
            root.addWidget(self.card, 0, Qt.AlignLeft)
            root.addStretch()
        self.setLayout(root)
        self.set_max_width(max_width)

    def set_max_width(self, max_width: int) -> None:
        self.message_label.setMaximumWidth(max(120, max_width))
        self.card.adjustSize()
        self.adjustSize()


class CompanionChatWindow(QWidget):
    message_submitted = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("猫猫聊天")
        self.resize(380, 480)
        self.setStyleSheet(_chat_stylesheet())

        self.message_list = QListWidget()
        self.message_list.setSelectionMode(QListWidget.NoSelection)
        self.message_list.setFocusPolicy(Qt.NoFocus)
        self.message_list.setWordWrap(True)
        self.message_list.setSpacing(6)
        self.message_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.message_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.message_list.setFrameShape(QListWidget.NoFrame)

        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("和猫猫说点什么...")
        self.input_line.returnPressed.connect(self._submit)

        send_button = QPushButton("发送")
        send_button.clicked.connect(self._submit)

        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        input_row.addWidget(self.input_line, 1)
        input_row.addWidget(send_button)

        root = QVBoxLayout()
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(10)
        root.addWidget(self.message_list, 1)
        root.addLayout(input_row)
        self.setLayout(root)

    def add_user_message(self, text: str) -> None:
        self._add_message(sender="你", text=text, is_user=True)

    def add_pet_message(self, text: str) -> None:
        self._add_message(sender="猫猫", text=text, is_user=False)

    def _submit(self) -> None:
        message = self.input_line.text().strip()
        if not message:
            return
        self.input_line.clear()
        self.message_submitted.emit(message)

    def _add_message(self, sender: str, text: str, is_user: bool) -> None:
        bubble = ChatBubble(
            sender=sender,
            text=text,
            is_user=is_user,
            max_width=self._bubble_max_width(),
        )
        item = QListWidgetItem()
        item.setSizeHint(bubble.sizeHint())
        self.message_list.addItem(item)
        self.message_list.setItemWidget(item, bubble)
        self.message_list.scrollToBottom()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh_bubble_widths()

    def _refresh_bubble_widths(self) -> None:
        width = self._bubble_max_width()
        for i in range(self.message_list.count()):
            item = self.message_list.item(i)
            widget = self.message_list.itemWidget(item)
            if isinstance(widget, ChatBubble):
                widget.set_max_width(width)
                item.setSizeHint(widget.sizeHint())

    def _bubble_max_width(self) -> int:
        return self.message_list.viewport().width() - 90


def _chat_stylesheet() -> str:
    return """
    QWidget {
        background: #f8f2e8;
        color: #2a2420;
        font-family: ".AppleSystemUIFont";
    }
    QListWidget {
        border: 1px solid #e6d8c3;
        border-radius: 16px;
        background: #fffdf9;
        padding: 8px;
    }
    QFrame#userBubble, QFrame#petBubble {
        border-radius: 12px;
    }
    QFrame#userBubble {
        background: #f1dfca;
        border: 1px solid #e2c8ab;
    }
    QFrame#petBubble {
        background: #ffffff;
        border: 1px solid #e8dccb;
    }
    QLabel#senderLabel {
        color: #7e6b57;
        font-size: 11px;
        font-weight: 600;
    }
    QLabel#messageLabel {
        color: #2a2420;
        font-size: 17px;
        font-weight: 500;
        line-height: 1.35;
    }
    QLineEdit {
        border: 1px solid #dec9ad;
        border-radius: 14px;
        background: white;
        padding: 10px 12px;
    }
    QPushButton {
        border: none;
        border-radius: 14px;
        background: #cb7843;
        color: white;
        padding: 10px 16px;
        font-weight: 600;
    }
    QPushButton:hover {
        background: #b96736;
    }
    QScrollBar:vertical {
        width: 8px;
        background: transparent;
        margin: 8px 2px 8px 0px;
    }
    QScrollBar::handle:vertical {
        background: #d4bda0;
        border-radius: 4px;
        min-height: 24px;
    }
    QScrollBar::handle:vertical:hover {
        background: #c4a585;
    }
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {
        height: 0px;
        background: transparent;
    }
    QScrollBar:horizontal {
        height: 0px;
    }
    """
