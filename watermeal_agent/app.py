from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from logging.handlers import RotatingFileHandler

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QAction, QGuiApplication, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon

from .companion import EmotionalCompanion
from .icons import app_icon, tray_icon
from .llm_companion import LLMCompanion
from .macos import (
    install_launch_agent,
    is_launch_agent_installed,
    remove_launch_agent,
    send_native_notification,
)
from .models import AppConfig, AppState
from .scheduler import (
    REMINDER_DINNER,
    REMINDER_LUNCH,
    REMINDER_WATER,
    ensure_today,
    initialize_schedule,
    mark_done,
    mark_reminder_shown,
    next_due_reminder,
    reset_water_schedule,
    skip_today,
    snooze_reminder,
    status_text,
    sync_meal_schedule,
)
from .storage import APP_DIR, LOG_PATH, JsonStore
from .ui.dashboard_window import DashboardWindow
from .ui.companion_chat import CompanionChatWindow
from .ui.desktop_pet import DesktopPetWindow
from .ui.reminder_dialog import ReminderDialog
from .ui.settings_window import SettingsWindow


LOGGER = logging.getLogger(__name__)
TICK_INTERVAL_MS = 30_000
WAKE_GAP_SECONDS = 90
REMINDER_COOLDOWN_MINUTES = 5


class LLMReplyWorkerSignals(QObject):
    finished = Signal(int, str, str)


class LLMReplyWorker(QRunnable):
    def __init__(self, request_id: int, model: str, history: list[dict[str, str]]) -> None:
        super().__init__()
        self.request_id = request_id
        self.model = model
        self.history = history
        self.signals = LLMReplyWorkerSignals()

    def run(self) -> None:
        try:
            client = LLMCompanion(self.model)
            reply = client.reply(self.history)
            if reply is None:
                self.signals.finished.emit(
                    self.request_id,
                    "",
                    client.last_error or "未知错误",
                )
                return
            self.signals.finished.emit(self.request_id, reply, "")
        except Exception:
            LOGGER.exception("LLM worker crashed")
            self.signals.finished.emit(self.request_id, "", "LLM 线程异常")


class WaterMealApp:
    def __init__(self, qt_app: QApplication) -> None:
        self.qt_app = qt_app
        self.qt_app.setQuitOnLastWindowClosed(False)
        self.qt_app.applicationStateChanged.connect(self.on_application_state_changed)

        self.store = JsonStore()
        self.config: AppConfig = self.store.load_config()
        env_model = (os.getenv("WATERMEAL_LLM_MODEL") or "").strip()
        if env_model:
            self.config.llm_model = env_model
        self.state: AppState = self.store.load_state()
        if is_launch_agent_installed() != self.config.launch_at_login:
            self.config.launch_at_login = is_launch_agent_installed()

        initialize_schedule(self.state, self.config)
        ensure_today(self.state, self.config)
        self.store.save_config(self.config)
        self.store.save_state(self.state)

        self.dashboard_window = DashboardWindow()
        self.dashboard_window.open_settings_requested.connect(self.show_settings)
        self.dashboard_window.quick_mark_done_requested.connect(self.quick_mark_done)
        self.dashboard_window.quick_snooze_requested.connect(self.quick_snooze)

        self.companion = EmotionalCompanion()
        self.llm_companion = LLMCompanion(self.config.llm_model)
        self.config.llm_model = self.llm_companion.model
        self.thread_pool = QThreadPool.globalInstance()
        self.llm_request_inflight = False
        self.llm_request_seq = 0
        self.llm_workers: dict[int, LLMReplyWorker] = {}
        self.chat_history: list[dict[str, str]] = []
        self.chat_window = CompanionChatWindow()
        self.chat_window.message_submitted.connect(self.on_chat_message)
        opening = self.companion.opening_message()
        self.chat_window.add_pet_message(opening)
        self.chat_history.append({"role": "assistant", "content": opening})

        self.settings_window = SettingsWindow()
        self.settings_window.config_saved.connect(self.on_config_saved)
        self.open_dialogs: dict[str, ReminderDialog] = {}
        self.pet_window = DesktopPetWindow()
        self.pet_window.pet_clicked.connect(self.show_chat)
        self.pet_window.position_committed.connect(self.on_pet_position_committed)
        self.pet_window.reminder_action_selected.connect(self.handle_reminder_action)
        self.pet_window.reminder_dismissed.connect(self.on_pet_reminder_dismissed)

        self.tray = QSystemTrayIcon(self._icon(), self.qt_app)
        self.tray.setToolTip("Water Meal Agent")
        self.menu = QMenu()
        self.status_action = QAction("", self.menu)
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)
        self.menu.addSeparator()

        open_dashboard_action = QAction("打开面板", self.menu)
        open_dashboard_action.triggered.connect(self.show_dashboard)
        self.menu.addAction(open_dashboard_action)

        open_settings_action = QAction("打开设置", self.menu)
        open_settings_action.triggered.connect(self.show_settings)
        self.menu.addAction(open_settings_action)

        open_chat_action = QAction("打开聊天", self.menu)
        open_chat_action.triggered.connect(self.show_chat)
        self.menu.addAction(open_chat_action)

        self.toggle_pet_action = QAction("", self.menu)
        self.toggle_pet_action.triggered.connect(self.toggle_desktop_pet)
        self.menu.addAction(self.toggle_pet_action)

        quick_water_action = QAction("记一杯水", self.menu)
        quick_water_action.triggered.connect(lambda: self.quick_mark_done(REMINDER_WATER))
        self.menu.addAction(quick_water_action)

        self.menu.addSeparator()
        quit_action = QAction("退出", self.menu)
        quit_action.triggered.connect(self.qt_app.quit)
        self.menu.addAction(quit_action)

        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.timer.start(TICK_INTERVAL_MS)
        self.last_tick_monotonic = time.monotonic()

        self.refresh_ui()
        self.sync_desktop_pet_visibility()
        self.show_dashboard()
        self.tick()

    def _icon(self) -> QIcon:
        icon = tray_icon()
        if icon.isNull():
            icon = app_icon()
        if icon.isNull():
            icon = self.qt_app.style().standardIcon(QStyle.SP_TitleBarMenuButton)
        if icon.isNull():
            icon = QGuiApplication.windowIcon()
        return icon

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.Trigger,
            QSystemTrayIcon.DoubleClick,
            QSystemTrayIcon.MiddleClick,
        ):
            self.show_dashboard()

    def on_application_state_changed(self, state) -> None:
        if state != Qt.ApplicationActive:
            return
        if self.dashboard_window.isVisible() or self.settings_window.isVisible():
            return
        self.show_dashboard()

    def show_dashboard(self) -> None:
        self.dashboard_window.set_data(self.config, self.state)
        self.dashboard_window.show()
        self.dashboard_window.raise_()
        self.dashboard_window.activateWindow()

    def show_settings(self) -> None:
        self.settings_window.set_data(self.config, self.state)
        self.settings_window.show()
        self.settings_window.raise_()
        self.settings_window.activateWindow()

    def show_chat(self) -> None:
        self.chat_window.show()
        self.chat_window.raise_()
        self.chat_window.activateWindow()

    def on_config_saved(self, config: AppConfig) -> None:
        self.config = config
        sync_meal_schedule(self.state, self.config)
        reset_water_schedule(self.state, self.config)
        self.sync_desktop_pet_visibility()
        self.sync_launch_at_login()
        self.llm_companion.reconfigure(self.config.llm_model)
        self.config.llm_model = self.llm_companion.model
        self.store.save_config(self.config)
        self.store.save_state(self.state)
        self.refresh_ui()

    def on_chat_message(self, message: str) -> None:
        self.chat_window.add_user_message(message)
        self.chat_history.append({"role": "user", "content": message})
        self.chat_history = self.chat_history[-24:]

        if self.config.llm_chat_enabled:
            if self.llm_request_inflight:
                wait_text = "[LLM忙] 上一条还在生成，请稍等。"
                self.chat_window.add_pet_message(wait_text)
                return
            self.llm_request_inflight = True
            self.llm_request_seq += 1
            request_id = self.llm_request_seq
            LOGGER.info("LLM request start id=%s model=%s", request_id, self.config.llm_model)
            worker = LLMReplyWorker(
                request_id=request_id,
                model=self.config.llm_model,
                history=[dict(item) for item in self.chat_history[-12:]],
            )
            self.llm_workers[request_id] = worker
            worker.signals.finished.connect(
                self.on_llm_reply_finished,
                type=Qt.QueuedConnection,
            )
            self.thread_pool.start(worker)
            return

        reply = self.companion.reply(message)
        self.chat_window.add_pet_message(reply)
        self.chat_history.append({"role": "assistant", "content": reply})

    def on_llm_reply_finished(self, request_id: int, reply: str, error: str) -> None:
        self.llm_workers.pop(request_id, None)
        self.llm_request_inflight = False
        if error:
            LOGGER.warning("LLM request failed id=%s error=%s", request_id, error)
            error_text = f"[LLM错误] {error}"
            self.chat_window.add_pet_message(error_text)
            return
        LOGGER.info("LLM request success id=%s reply_len=%s", request_id, len(reply))
        self.chat_window.add_pet_message(reply)
        self.chat_history.append({"role": "assistant", "content": reply})
        self.chat_history = self.chat_history[-24:]

    def quick_mark_done(self, reminder_type: str) -> None:
        if self.pet_window.active_reminder() == reminder_type:
            self.pet_window.dismiss_reminder()
        mark_done(self.state, self.config, reminder_type)
        self.store.save_state(self.state)
        self.refresh_ui()

    def quick_snooze(self, reminder_type: str) -> None:
        if self.pet_window.active_reminder() == reminder_type:
            self.pet_window.dismiss_reminder()
        snooze_reminder(self.state, self.config, reminder_type)
        self.store.save_state(self.state)
        self.refresh_ui()

    def tick(self) -> None:
        self._handle_wake_gap()

        changed = ensure_today(self.state, self.config)
        if changed:
            sync_meal_schedule(self.state, self.config)

        if not self.open_dialogs and not self.pet_window.has_active_reminder():
            reminder_type = next_due_reminder(self.state)
            if reminder_type:
                self.show_reminder(reminder_type)

        self.store.save_state(self.state)
        self.refresh_ui()

    def show_reminder(self, reminder_type: str) -> None:
        mark_reminder_shown(self.state, reminder_type, REMINDER_COOLDOWN_MINUTES)
        if self.config.desktop_pet_enabled:
            self.pet_window.show_reminder(reminder_type, self.config.reminder_snooze_minutes)
            self._notify_reminder(reminder_type)
            return

        dialog = ReminderDialog(reminder_type, self.config.reminder_snooze_minutes)
        dialog.action_selected.connect(
            lambda action, rt=reminder_type: self.handle_reminder_action(rt, action)
        )
        dialog.destroyed.connect(lambda _=None, rt=reminder_type: self.open_dialogs.pop(rt, None))
        self.open_dialogs[reminder_type] = dialog
        dialog.show()
        self._notify_reminder(reminder_type)

    def handle_reminder_action(self, reminder_type: str, action: str) -> None:
        if action == "done":
            mark_done(self.state, self.config, reminder_type)
        elif action == "snooze":
            snooze_reminder(self.state, self.config, reminder_type)
        elif action == "skip":
            skip_today(self.state, reminder_type)

        self.pet_window.set_pet_state("idle")
        self.store.save_state(self.state)
        self.refresh_ui()

    def on_pet_position_committed(self, x: int, y: int) -> None:
        self.state.pet_x = x
        self.state.pet_y = y
        self.store.save_state(self.state)

    def on_pet_reminder_dismissed(self, _reminder_type: str) -> None:
        self.refresh_ui()

    def toggle_desktop_pet(self) -> None:
        self.config.desktop_pet_enabled = not self.config.desktop_pet_enabled
        self.sync_desktop_pet_visibility()
        self.store.save_config(self.config)
        self.store.save_state(self.state)
        self.refresh_ui()

    def sync_desktop_pet_visibility(self) -> None:
        if self.config.desktop_pet_enabled:
            if self.state.pet_x is None or self.state.pet_y is None:
                self._set_default_pet_position()
            self.pet_window.move(int(self.state.pet_x), int(self.state.pet_y))
            self.pet_window.show()
            self.pet_window.raise_()
        else:
            self.pet_window.dismiss_reminder()
            self.pet_window.hide()

    def _set_default_pet_position(self) -> None:
        screen = self.qt_app.primaryScreen()
        if not screen:
            self.state.pet_x = 40
            self.state.pet_y = 80
            return
        area = screen.availableGeometry()
        self.state.pet_x = max(0, area.right() - self.pet_window.width() - 24)
        self.state.pet_y = max(0, area.bottom() - self.pet_window.height() - 42)

    def _notify_reminder(self, reminder_type: str) -> None:
        if self.config.native_notifications_enabled:
            send_native_notification("Water Meal Agent", self._notification_text(reminder_type))
        self.tray.showMessage(
            "提醒",
            self._notification_text(reminder_type),
            QSystemTrayIcon.Information,
            5000,
        )

    def refresh_ui(self) -> None:
        self.status_action.setText(status_text(self.state))
        self.toggle_pet_action.setText(
            "隐藏桌宠" if self.config.desktop_pet_enabled else "显示桌宠"
        )
        if self.dashboard_window.isVisible():
            self.dashboard_window.set_data(self.config, self.state)
        if self.settings_window.isVisible():
            self.settings_window.set_data(self.config, self.state)

    def _notification_text(self, reminder_type: str) -> str:
        if reminder_type == REMINDER_WATER:
            return "该喝水了"
        if reminder_type == REMINDER_LUNCH:
            return "到午饭时间了"
        if reminder_type == REMINDER_DINNER:
            return "到晚饭时间了"
        return "你有新的提醒"

    def sync_launch_at_login(self) -> None:
        project_root = Path(__file__).resolve().parent.parent
        try:
            if self.config.launch_at_login:
                install_launch_agent(project_root)
            else:
                remove_launch_agent()
        except Exception:
            LOGGER.exception("Failed to sync launch-at-login setting")

    def _handle_wake_gap(self) -> None:
        current_mono = time.monotonic()
        gap = current_mono - self.last_tick_monotonic
        self.last_tick_monotonic = current_mono
        if gap >= WAKE_GAP_SECONDS:
            LOGGER.info("Detected wake/suspend gap: %.1f seconds", gap)


def main() -> None:
    load_env_file(Path(__file__).resolve().parent.parent / ".env")
    setup_logging()
    install_exception_hook()
    app = QApplication(sys.argv)
    app.setApplicationName("Water Meal Agent")
    app.setWindowIcon(app_icon())
    instance = WaterMealApp(app)
    sys.exit(app.exec())


def setup_logging() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    file_handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.handlers.clear()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)


def install_exception_hook() -> None:
    def _handle_exception(exc_type, exc_value, exc_traceback) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        LOGGER.exception(
            "Uncaught exception",
            exc_info=(exc_type, exc_value, exc_traceback),
        )

    sys.excepthook = _handle_exception


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        LOGGER.warning("Failed to read env file: %s", path)
        return

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
