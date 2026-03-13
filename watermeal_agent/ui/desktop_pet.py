from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class PetReminderBubble(QWidget):
    action_selected = Signal(str, str)
    dismissed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.current_reminder: str | None = None
        self.action_taken = False

        self.card = QFrame()
        self.card.setObjectName("bubbleCard")

        self.title_label = QLabel("")
        self.title_label.setObjectName("bubbleTitle")
        self.message_label = QLabel("")
        self.message_label.setWordWrap(True)

        self.done_button = QPushButton("完成")
        self.snooze_button = QPushButton("稍后提醒")
        self.skip_button = QPushButton("今天跳过")

        self.done_button.clicked.connect(lambda: self._emit_action("done"))
        self.snooze_button.clicked.connect(lambda: self._emit_action("snooze"))
        self.skip_button.clicked.connect(lambda: self._emit_action("skip"))

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        button_row.addWidget(self.done_button)
        button_row.addWidget(self.snooze_button)
        button_row.addWidget(self.skip_button)

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(14, 12, 14, 12)
        card_layout.setSpacing(8)
        card_layout.addWidget(self.title_label)
        card_layout.addWidget(self.message_label)
        card_layout.addLayout(button_row)
        self.card.setLayout(card_layout)

        root = QVBoxLayout()
        root.setContentsMargins(8, 8, 8, 8)
        root.addWidget(self.card)
        self.setLayout(root)
        self.setStyleSheet(_bubble_stylesheet())

    def show_reminder(self, reminder_type: str, snooze_minutes: int, anchor: QRect) -> None:
        self.current_reminder = reminder_type
        self.action_taken = False
        self.title_label.setText(_title_for(reminder_type))
        self.message_label.setText(_message_for(reminder_type, snooze_minutes))
        self.done_button.setText("我喝了" if reminder_type == "water" else "我吃了")
        self.snooze_button.setText(f"{snooze_minutes} 分钟后")
        self.adjustSize()
        self.reposition(anchor)
        self.show()
        self.raise_()

    def has_active_reminder(self) -> bool:
        return bool(self.current_reminder and self.isVisible())

    def active_reminder(self) -> str | None:
        return self.current_reminder

    def dismiss(self) -> None:
        if self.isVisible():
            self.close()

    def reposition(self, anchor: QRect) -> None:
        margin = 10
        x = anchor.left() - self.width() - margin
        y = anchor.top()
        if x < 0:
            x = anchor.right() + margin
        if y < 0:
            y = margin
        self.move(x, y)

    def closeEvent(self, event) -> None:
        reminder = self.current_reminder
        should_emit = bool(reminder and not self.action_taken)
        self.current_reminder = None
        self.action_taken = False
        super().closeEvent(event)
        if should_emit and reminder:
            self.dismissed.emit(reminder)

    def _emit_action(self, action: str) -> None:
        if not self.current_reminder:
            return
        self.action_taken = True
        self.action_selected.emit(self.current_reminder, action)
        self.close()


class DesktopPetWindow(QWidget):
    pet_clicked = Signal()
    position_committed = Signal(int, int)
    reminder_action_selected = Signal(str, str)
    reminder_dismissed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setFixedSize(120, 120)

        self._pressed = False
        self._dragging = False
        self._press_global = QPoint()
        self._window_origin = QPoint()
        self._state = "idle"

        self.bubble = PetReminderBubble()
        self.bubble.action_selected.connect(self.reminder_action_selected.emit)
        self.bubble.dismissed.connect(self._on_bubble_dismissed)

    def set_pet_state(self, state: str) -> None:
        self._state = state
        self.update()

    def show_reminder(self, reminder_type: str, snooze_minutes: int) -> bool:
        self.set_pet_state("alert")
        self.bubble.show_reminder(reminder_type, snooze_minutes, self.frameGeometry())
        return True

    def has_active_reminder(self) -> bool:
        return self.bubble.has_active_reminder()

    def active_reminder(self) -> str | None:
        return self.bubble.active_reminder()

    def dismiss_reminder(self) -> None:
        self.bubble.dismiss()
        if not self.has_active_reminder():
            self.set_pet_state("idle")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._pressed = True
            self._dragging = False
            self._press_global = event.globalPosition().toPoint()
            self._window_origin = self.pos()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if not self._pressed:
            super().mouseMoveEvent(event)
            return
        offset = event.globalPosition().toPoint() - self._press_global
        if offset.manhattanLength() > 4:
            self._dragging = True
        if self._dragging:
            self.move(self._window_origin + offset)
            if self.has_active_reminder():
                self.bubble.reposition(self.frameGeometry())
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton and self._pressed:
            self._pressed = False
            if self._dragging:
                self.position_committed.emit(self.x(), self.y())
            else:
                self.pet_clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = QRectF(self.rect().adjusted(6, 6, -6, -6))

        fur_color = QColor("#e8b26b") if self._state != "alert" else QColor("#df9352")
        fur_dark = QColor("#cf8444")
        stripe_color = QColor("#b86c32")
        outline = QColor("#8f5c34")
        eye_color = QColor("#1f1a18")
        muzzle_color = QColor("#f7eddc")
        shadow_color = QColor(44, 30, 20, 38)

        head_rect = QRectF(rect.left() + 12, rect.top() + 8, rect.width() - 24, 66)
        body_rect = QRectF(rect.left() + 18, rect.top() + 52, rect.width() - 28, 56)
        muzzle_rect = QRectF(head_rect.center().x() - 20, head_rect.top() + 36, 40, 22)

        shadow = QPainterPath()
        shadow.addEllipse(
            QRectF(body_rect.left() + 6, body_rect.bottom() - 10, body_rect.width() - 10, 12)
        )
        painter.fillPath(shadow, shadow_color)

        tail_pen = QPen(fur_dark)
        tail_pen.setWidth(10)
        tail_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(tail_pen)
        tail = QPainterPath(QPointF(body_rect.right() - 10, body_rect.center().y() + 8))
        tail.cubicTo(
            QPointF(body_rect.right() + 20, body_rect.bottom() + 8),
            QPointF(body_rect.right() + 10, body_rect.top() + 6),
            QPointF(body_rect.right() - 4, body_rect.top() + 14),
        )
        painter.drawPath(tail)

        painter.setPen(QPen(outline, 2))
        painter.setBrush(fur_dark)
        painter.drawEllipse(body_rect)
        painter.setBrush(fur_color)
        painter.drawEllipse(head_rect)

        left_ear = QPolygonF(
            [
                QPointF(head_rect.left() + 12, head_rect.top() + 12),
                QPointF(head_rect.left() + 26, head_rect.top() - 10),
                QPointF(head_rect.left() + 38, head_rect.top() + 14),
            ]
        )
        right_ear = QPolygonF(
            [
                QPointF(head_rect.right() - 12, head_rect.top() + 12),
                QPointF(head_rect.right() - 26, head_rect.top() - 10),
                QPointF(head_rect.right() - 38, head_rect.top() + 14),
            ]
        )
        painter.setBrush(fur_color)
        painter.drawPolygon(left_ear)
        painter.drawPolygon(right_ear)

        painter.setBrush(muzzle_color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(muzzle_rect)

        painter.setBrush(QColor("#f2c49a"))
        painter.drawEllipse(QRectF(muzzle_rect.center().x() - 4, muzzle_rect.top() + 4, 8, 6))

        painter.setPen(QPen(outline, 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(
            int(muzzle_rect.center().x() - 12),
            int(muzzle_rect.top() + 8),
            12,
            12,
            200 * 16,
            120 * 16,
        )
        painter.drawArc(
            int(muzzle_rect.center().x()),
            int(muzzle_rect.top() + 8),
            12,
            12,
            220 * 16,
            120 * 16,
        )

        eye_w = 16 if self._state != "alert" else 18
        eye_h = 18 if self._state != "alert" else 19
        left_eye = QRectF(head_rect.center().x() - 26, head_rect.top() + 20, eye_w, eye_h)
        right_eye = QRectF(head_rect.center().x() + 10, head_rect.top() + 20, eye_w, eye_h)
        painter.setPen(Qt.NoPen)
        painter.setBrush(eye_color)
        painter.drawEllipse(left_eye)
        painter.drawEllipse(right_eye)

        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(QRectF(left_eye.left() + 3, left_eye.top() + 3, 4, 4))
        painter.drawEllipse(QRectF(right_eye.left() + 3, right_eye.top() + 3, 4, 4))

        painter.setPen(QPen(stripe_color, 3, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(
            QPointF(head_rect.center().x(), head_rect.top() + 8),
            QPointF(head_rect.center().x(), head_rect.top() + 18),
        )
        painter.drawLine(
            QPointF(head_rect.center().x() - 10, head_rect.top() + 10),
            QPointF(head_rect.center().x() - 14, head_rect.top() + 18),
        )
        painter.drawLine(
            QPointF(head_rect.center().x() + 10, head_rect.top() + 10),
            QPointF(head_rect.center().x() + 14, head_rect.top() + 18),
        )
        painter.drawLine(
            QPointF(body_rect.left() + 14, body_rect.top() + 18),
            QPointF(body_rect.left() + 24, body_rect.top() + 24),
        )
        painter.drawLine(
            QPointF(body_rect.left() + 28, body_rect.top() + 14),
            QPointF(body_rect.left() + 38, body_rect.top() + 20),
        )

        whisker_pen = QPen(QColor("#d7c8b3"))
        whisker_pen.setWidth(2)
        whisker_pen.setCapStyle(Qt.RoundCap)
        painter.setPen(whisker_pen)
        self._draw_whiskers(painter, muzzle_rect)

    def _draw_whiskers(self, painter: QPainter, muzzle_rect: QRectF) -> None:
        y = muzzle_rect.top() + 8
        left_x = muzzle_rect.left() + 2
        right_x = muzzle_rect.right() - 2

        painter.drawLine(QPointF(left_x, y), QPointF(left_x - 18, y - 4))
        painter.drawLine(QPointF(left_x, y + 5), QPointF(left_x - 20, y + 6))
        painter.drawLine(QPointF(left_x, y + 10), QPointF(left_x - 18, y + 16))

        painter.drawLine(QPointF(right_x, y), QPointF(right_x + 18, y - 4))
        painter.drawLine(QPointF(right_x, y + 5), QPointF(right_x + 20, y + 6))
        painter.drawLine(QPointF(right_x, y + 10), QPointF(right_x + 18, y + 16))

    def _on_bubble_dismissed(self, reminder_type: str) -> None:
        self.set_pet_state("idle")
        self.reminder_dismissed.emit(reminder_type)


def _title_for(reminder_type: str) -> str:
    if reminder_type == "water":
        return "喝水提醒"
    if reminder_type == "lunch":
        return "午饭提醒"
    if reminder_type == "dinner":
        return "晚饭提醒"
    return "提醒"


def _message_for(reminder_type: str, snooze_minutes: int) -> str:
    if reminder_type == "water":
        return f"该喝水了，要不要先喝一杯？也可以 {snooze_minutes} 分钟后再提醒。"
    if reminder_type == "lunch":
        return f"到午饭时间了，记得按时吃饭。可 {snooze_minutes} 分钟后再提醒。"
    if reminder_type == "dinner":
        return f"到晚饭时间了，记得按时吃饭。可 {snooze_minutes} 分钟后再提醒。"
    return "你有新的提醒。"


def _bubble_stylesheet() -> str:
    return """
    QFrame#bubbleCard {
        background: #fff9f0;
        border: 1px solid #e5d5bf;
        border-radius: 14px;
    }
    QLabel#bubbleTitle {
        font-size: 14px;
        font-weight: 700;
        color: #2a2420;
    }
    QLabel {
        color: #4d4238;
    }
    QPushButton {
        border: none;
        border-radius: 10px;
        padding: 7px 10px;
        background: #efe1cf;
        color: #2a2420;
        font-weight: 600;
    }
    QPushButton:hover {
        background: #e7d6bf;
    }
    """
