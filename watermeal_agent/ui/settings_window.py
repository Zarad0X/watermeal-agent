from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ..models import AppConfig, AppState


class SettingsWindow(QWidget):
    config_saved = Signal(AppConfig)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Water Meal Agent 设置")
        self.resize(380, 280)
        self.setStyleSheet(_settings_stylesheet())

        self.water_interval_input = QSpinBox()
        self.water_interval_input.setRange(15, 240)
        self.water_interval_input.setSuffix(" 分钟")

        self.snooze_input = QSpinBox()
        self.snooze_input.setRange(5, 60)
        self.snooze_input.setSuffix(" 分钟")

        self.lunch_time_input = QLineEdit()
        self.lunch_time_input.setPlaceholderText("12:00")

        self.dinner_time_input = QLineEdit()
        self.dinner_time_input.setPlaceholderText("18:30")

        self.native_notifications_input = QCheckBox("启用 macOS 原生通知")
        self.launch_at_login_input = QCheckBox("登录时自动启动")
        self.desktop_pet_input = QCheckBox("启用桌面宠物")

        self.status_label = QLabel("")

        save_button = QPushButton("保存设置")
        save_button.clicked.connect(self._save)

        form = QFormLayout()
        form.addRow("喝水间隔", self.water_interval_input)
        form.addRow("稍后提醒", self.snooze_input)
        form.addRow("午饭时间", self.lunch_time_input)
        form.addRow("晚饭时间", self.dinner_time_input)
        form.addRow("", self.desktop_pet_input)
        form.addRow("", self.native_notifications_input)
        form.addRow("", self.launch_at_login_input)

        button_row = QHBoxLayout()
        button_row.addStretch()
        button_row.addWidget(save_button)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.status_label)
        layout.addStretch()
        layout.addLayout(button_row)
        self.setLayout(layout)

    def set_data(self, config: AppConfig, state: AppState) -> None:
        self.water_interval_input.setValue(config.water_interval_minutes)
        self.snooze_input.setValue(config.reminder_snooze_minutes)
        self.lunch_time_input.setText(config.lunch_time)
        self.dinner_time_input.setText(config.dinner_time)
        self.desktop_pet_input.setChecked(config.desktop_pet_enabled)
        self.native_notifications_input.setChecked(config.native_notifications_enabled)
        self.launch_at_login_input.setChecked(config.launch_at_login)

        lunch = "已完成" if state.stats.lunch_done else "未完成"
        dinner = "已完成" if state.stats.dinner_done else "未完成"
        self.status_label.setText(
            f"今日统计：喝水 {state.stats.water_count} 次，午饭 {lunch}，晚饭 {dinner}"
        )

    def _save(self) -> None:
        lunch_time = self.lunch_time_input.text().strip() or "12:00"
        dinner_time = self.dinner_time_input.text().strip() or "18:30"
        if not self._is_valid_clock(lunch_time) or not self._is_valid_clock(dinner_time):
            QMessageBox.warning(self, "时间格式错误", "请输入 HH:MM 格式的时间，例如 12:00")
            return

        config = AppConfig(
            water_interval_minutes=self.water_interval_input.value(),
            lunch_time=lunch_time,
            dinner_time=dinner_time,
            reminder_snooze_minutes=self.snooze_input.value(),
            native_notifications_enabled=self.native_notifications_input.isChecked(),
            launch_at_login=self.launch_at_login_input.isChecked(),
            desktop_pet_enabled=self.desktop_pet_input.isChecked(),
        )
        self.config_saved.emit(config)
        self.close()

    def _is_valid_clock(self, value: str) -> bool:
        parts = value.split(":")
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            return False
        hour, minute = int(parts[0]), int(parts[1])
        return 0 <= hour <= 23 and 0 <= minute <= 59


def _settings_stylesheet() -> str:
    return """
    QWidget {
        background: #fbf7f1;
        color: #211c18;
        font-family: ".AppleSystemUIFont";
    }
    QLabel {
        font-size: 13px;
    }
    QLineEdit, QSpinBox {
        background: white;
        border: 1px solid #dfd2c2;
        border-radius: 10px;
        padding: 8px 10px;
        min-height: 18px;
    }
    QSpinBox {
        padding-right: 34px;
    }
    QSpinBox::up-button {
        subcontrol-origin: border;
        subcontrol-position: top right;
        width: 24px;
        background: #f2e8dc;
        border-left: 1px solid #dfd2c2;
        border-top-right-radius: 10px;
    }
    QSpinBox::down-button {
        subcontrol-origin: border;
        subcontrol-position: bottom right;
        width: 24px;
        background: #f2e8dc;
        border-left: 1px solid #dfd2c2;
        border-top: 1px solid #dfd2c2;
        border-bottom-right-radius: 10px;
    }
    QSpinBox::up-button:hover,
    QSpinBox::down-button:hover {
        background: #eadac5;
    }
    QSpinBox::up-button:pressed,
    QSpinBox::down-button:pressed {
        background: #dec7ab;
    }
    QPushButton {
        background: #c96f3c;
        color: white;
        border: none;
        border-radius: 12px;
        padding: 10px 16px;
        font-weight: 600;
    }
    """
