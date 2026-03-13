from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..models import AppConfig, AppState
from ..scheduler import history_rows, summary_cards, upcoming_items


class SummaryCard(QFrame):
    def __init__(self, title: str) -> None:
        super().__init__()
        self.setObjectName("summaryCard")

        self.title_label = QLabel(title)
        self.title_label.setObjectName("cardTitle")

        self.value_label = QLabel("--")
        self.value_label.setObjectName("cardValue")

        self.note_label = QLabel("")
        self.note_label.setObjectName("cardNote")

        layout = QVBoxLayout()
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(6)
        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.note_label)
        self.setLayout(layout)

    def set_data(self, value: str, note: str) -> None:
        self.value_label.setText(value)
        self.note_label.setText(note)


class UpcomingRow(QFrame):
    quick_action = Signal(str)

    def __init__(self, reminder_type: str, button_text: str) -> None:
        super().__init__()
        self.reminder_type = reminder_type
        self.setObjectName("upcomingRow")

        self.title_label = QLabel("")
        self.title_label.setObjectName("rowTitle")

        self.time_label = QLabel("")
        self.time_label.setObjectName("rowTime")
        self.time_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.detail_label = QLabel("")
        self.detail_label.setObjectName("rowDetail")

        self.action_button = QPushButton(button_text)
        self.action_button.setObjectName("ghostButton")
        self.action_button.clicked.connect(lambda: self.quick_action.emit(self.reminder_type))

        top_row = QHBoxLayout()
        top_row.addWidget(self.title_label)
        top_row.addStretch()
        top_row.addWidget(self.time_label)
        top_row.addWidget(self.action_button)

        layout = QVBoxLayout()
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)
        layout.addLayout(top_row)
        layout.addWidget(self.detail_label)
        self.setLayout(layout)

    def set_data(self, title: str, time_text: str, detail: str, enabled: bool) -> None:
        self.title_label.setText(title)
        self.time_label.setText(time_text)
        self.detail_label.setText(detail)
        self.action_button.setEnabled(enabled)


class DashboardWindow(QWidget):
    open_settings_requested = Signal()
    quick_mark_done_requested = Signal(str)
    quick_snooze_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Water Meal Agent")
        self.resize(520, 520)

        self.header_label = QLabel("今天也要按时补水和吃饭")
        self.header_label.setObjectName("headerLabel")

        self.subheader_label = QLabel("")
        self.subheader_label.setObjectName("subheaderLabel")

        self.water_card = SummaryCard("今日喝水")
        self.lunch_card = SummaryCard("午饭状态")
        self.dinner_card = SummaryCard("晚饭状态")

        card_grid = QGridLayout()
        card_grid.setSpacing(12)
        card_grid.addWidget(self.water_card, 0, 0)
        card_grid.addWidget(self.lunch_card, 0, 1)
        card_grid.addWidget(self.dinner_card, 0, 2)

        quick_title = QLabel("接下来")
        quick_title.setObjectName("sectionTitle")

        self.water_row = UpcomingRow("water", "记一杯")
        self.lunch_row = UpcomingRow("lunch", "记完成")
        self.dinner_row = UpcomingRow("dinner", "记完成")

        for row in (self.water_row, self.lunch_row, self.dinner_row):
            row.quick_action.connect(self.quick_mark_done_requested.emit)

        action_title = QLabel("快捷操作")
        action_title.setObjectName("sectionTitle")

        self.snooze_water_button = QPushButton("喝水延后 10 分钟")
        self.snooze_water_button.clicked.connect(
            lambda: self.quick_snooze_requested.emit("water")
        )

        open_settings_button = QPushButton("打开设置")
        open_settings_button.setObjectName("primaryButton")
        open_settings_button.clicked.connect(lambda: self.open_settings_requested.emit())

        action_row = QHBoxLayout()
        action_row.setSpacing(12)
        action_row.addWidget(self.snooze_water_button)
        action_row.addStretch()
        action_row.addWidget(open_settings_button)

        history_title = QLabel("最近记录")
        history_title.setObjectName("sectionTitle")

        self.history_list = QListWidget()
        self.history_list.setObjectName("historyList")
        self.history_list.setAlternatingRowColors(False)
        self.history_list.setSpacing(6)

        root = QVBoxLayout()
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(16)
        root.addWidget(self.header_label)
        root.addWidget(self.subheader_label)
        root.addLayout(card_grid)
        root.addSpacing(8)
        root.addWidget(quick_title)
        root.addWidget(self.water_row)
        root.addWidget(self.lunch_row)
        root.addWidget(self.dinner_row)
        root.addSpacing(8)
        root.addWidget(action_title)
        root.addLayout(action_row)
        root.addSpacing(8)
        root.addWidget(history_title)
        root.addWidget(self.history_list, 1)
        self.setLayout(root)
        self.setStyleSheet(_dashboard_stylesheet())

    def set_data(self, config: AppConfig, state: AppState) -> None:
        self.subheader_label.setText(
            f"喝水间隔 {config.water_interval_minutes} 分钟  ·  午饭 {config.lunch_time}  ·  晚饭 {config.dinner_time}"
        )
        self.snooze_water_button.setText(f"喝水延后 {config.reminder_snooze_minutes} 分钟")

        cards = summary_cards(state)
        self.water_card.set_data(cards[0]["value"], cards[0]["note"])
        self.lunch_card.set_data(cards[1]["value"], cards[1]["note"])
        self.dinner_card.set_data(cards[2]["value"], cards[2]["note"])

        upcoming = upcoming_items(state)
        self.water_row.set_data(
            upcoming[0]["title"],
            upcoming[0]["time"],
            upcoming[0]["detail"],
            enabled=upcoming[0]["time"] != "今日不再提醒",
        )
        self.lunch_row.set_data(
            upcoming[1]["title"],
            upcoming[1]["time"],
            upcoming[1]["detail"],
            enabled=upcoming[1]["time"] != "今日不再提醒",
        )
        self.dinner_row.set_data(
            upcoming[2]["title"],
            upcoming[2]["time"],
            upcoming[2]["detail"],
            enabled=upcoming[2]["time"] != "今日不再提醒",
        )

        self.history_list.clear()
        history = history_rows(state)
        if not history:
            placeholder = QListWidgetItem("还没有历史记录，明天会在这里看到今天的结果。")
            self.history_list.addItem(placeholder)
        else:
            for item in history:
                self.history_list.addItem(
                    QListWidgetItem(
                        f"{item['day']}  ·  喝水 {item['water']}  ·  午饭 {item['lunch']}  ·  晚饭 {item['dinner']}"
                    )
                )


def _dashboard_stylesheet() -> str:
    return """
    QWidget {
        background: #f6f1e8;
        color: #1f1a17;
        font-family: ".AppleSystemUIFont";
    }
    QLabel#headerLabel {
        font-size: 24px;
        font-weight: 700;
    }
    QLabel#subheaderLabel {
        color: #6c6258;
        font-size: 13px;
    }
    QLabel#sectionTitle {
        font-size: 16px;
        font-weight: 700;
        margin-top: 4px;
    }
    QFrame#summaryCard, QFrame#upcomingRow {
        background: #fffaf3;
        border: 1px solid #e6d8c4;
        border-radius: 16px;
    }
    QListWidget#historyList {
        background: #fffaf3;
        border: 1px solid #e6d8c4;
        border-radius: 16px;
        padding: 8px;
    }
    QListWidget#historyList::item {
        border-bottom: 1px solid #efe2d0;
        padding: 10px 8px;
    }
    QLabel#cardTitle {
        color: #7c6d60;
        font-size: 12px;
        font-weight: 600;
    }
    QLabel#cardValue {
        font-size: 28px;
        font-weight: 700;
    }
    QLabel#cardNote, QLabel#rowDetail {
        color: #7c6d60;
        font-size: 12px;
    }
    QLabel#rowTitle {
        font-size: 15px;
        font-weight: 600;
    }
    QLabel#rowTime {
        font-size: 15px;
        font-weight: 700;
        color: #b05d2b;
        min-width: 56px;
    }
    QPushButton {
        background: #efe1cf;
        border: none;
        border-radius: 12px;
        padding: 10px 14px;
        font-weight: 600;
    }
    QPushButton#primaryButton {
        background: #c96f3c;
        color: white;
    }
    QPushButton#ghostButton {
        background: #f2e7d8;
        min-width: 72px;
    }
    QPushButton:disabled {
        color: #9f9488;
        background: #eee5db;
    }
    """
