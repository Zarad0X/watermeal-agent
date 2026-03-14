from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date


@dataclass
class AppConfig:
    water_interval_minutes: int = 45
    lunch_time: str = "12:00"
    dinner_time: str = "18:30"
    reminder_snooze_minutes: int = 10
    native_notifications_enabled: bool = True
    launch_at_login: bool = False
    desktop_pet_enabled: bool = True
    llm_chat_enabled: bool = False
    llm_model: str = "gpt-4o-mini"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict | None) -> "AppConfig":
        raw = raw or {}
        return cls(
            water_interval_minutes=int(raw.get("water_interval_minutes", 45)),
            lunch_time=str(raw.get("lunch_time", "12:00")),
            dinner_time=str(raw.get("dinner_time", "18:30")),
            reminder_snooze_minutes=int(raw.get("reminder_snooze_minutes", 10)),
            native_notifications_enabled=bool(
                raw.get("native_notifications_enabled", True)
            ),
            launch_at_login=bool(raw.get("launch_at_login", False)),
            desktop_pet_enabled=bool(raw.get("desktop_pet_enabled", True)),
            llm_chat_enabled=bool(raw.get("llm_chat_enabled", False)),
            llm_model=str(raw.get("llm_model", "gpt-4o-mini")),
        )


@dataclass
class DayStats:
    day: str = field(default_factory=lambda: date.today().isoformat())
    water_count: int = 0
    lunch_done: bool = False
    dinner_done: bool = False
    skipped_water: bool = False
    skipped_lunch: bool = False
    skipped_dinner: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict | None) -> "DayStats":
        raw = raw or {}
        return cls(
            day=str(raw.get("day", date.today().isoformat())),
            water_count=int(raw.get("water_count", 0)),
            lunch_done=bool(raw.get("lunch_done", False)),
            dinner_done=bool(raw.get("dinner_done", False)),
            skipped_water=bool(raw.get("skipped_water", False)),
            skipped_lunch=bool(raw.get("skipped_lunch", False)),
            skipped_dinner=bool(raw.get("skipped_dinner", False)),
        )


@dataclass
class HistoryEntry:
    day: str
    water_count: int
    lunch_status: str
    dinner_status: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_day_stats(cls, stats: DayStats) -> "HistoryEntry":
        return cls(
            day=stats.day,
            water_count=stats.water_count,
            lunch_status=_meal_status(stats.lunch_done, stats.skipped_lunch),
            dinner_status=_meal_status(stats.dinner_done, stats.skipped_dinner),
        )

    @classmethod
    def from_dict(cls, raw: dict | None) -> "HistoryEntry | None":
        if not raw:
            return None
        return cls(
            day=str(raw.get("day", "")),
            water_count=int(raw.get("water_count", 0)),
            lunch_status=str(raw.get("lunch_status", "待完成")),
            dinner_status=str(raw.get("dinner_status", "待完成")),
        )


@dataclass
class AppState:
    stats: DayStats = field(default_factory=DayStats)
    history: list[HistoryEntry] = field(default_factory=list)
    next_water_due_at: str | None = None
    lunch_due_at: str | None = None
    dinner_due_at: str | None = None
    snoozed_until: dict[str, str | None] = field(
        default_factory=lambda: {"water": None, "lunch": None, "dinner": None}
    )
    reminder_cooldown_until: dict[str, str | None] = field(
        default_factory=lambda: {"water": None, "lunch": None, "dinner": None}
    )
    pet_x: int | None = None
    pet_y: int | None = None

    def to_dict(self) -> dict:
        return {
            "stats": self.stats.to_dict(),
            "history": [entry.to_dict() for entry in self.history],
            "next_water_due_at": self.next_water_due_at,
            "lunch_due_at": self.lunch_due_at,
            "dinner_due_at": self.dinner_due_at,
            "snoozed_until": dict(self.snoozed_until),
            "reminder_cooldown_until": dict(self.reminder_cooldown_until),
            "pet_x": self.pet_x,
            "pet_y": self.pet_y,
        }

    @classmethod
    def from_dict(cls, raw: dict | None) -> "AppState":
        raw = raw or {}
        history = [
            entry
            for entry in (
                HistoryEntry.from_dict(item) for item in raw.get("history", [])
            )
            if entry is not None
        ]
        return cls(
            stats=DayStats.from_dict(raw.get("stats")),
            history=history,
            next_water_due_at=raw.get("next_water_due_at"),
            lunch_due_at=raw.get("lunch_due_at"),
            dinner_due_at=raw.get("dinner_due_at"),
            snoozed_until={
                "water": (raw.get("snoozed_until") or {}).get("water"),
                "lunch": (raw.get("snoozed_until") or {}).get("lunch"),
                "dinner": (raw.get("snoozed_until") or {}).get("dinner"),
            },
            reminder_cooldown_until={
                "water": (raw.get("reminder_cooldown_until") or {}).get("water"),
                "lunch": (raw.get("reminder_cooldown_until") or {}).get("lunch"),
                "dinner": (raw.get("reminder_cooldown_until") or {}).get("dinner"),
            },
            pet_x=(int(raw["pet_x"]) if raw.get("pet_x") is not None else None),
            pet_y=(int(raw["pet_y"]) if raw.get("pet_y") is not None else None),
        )


def _meal_status(done: bool, skipped: bool) -> str:
    if done:
        return "已完成"
    if skipped:
        return "已跳过"
    return "待完成"
