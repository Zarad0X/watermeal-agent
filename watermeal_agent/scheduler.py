from __future__ import annotations

from datetime import date, datetime, time, timedelta

from .models import AppConfig, AppState, DayStats, HistoryEntry


REMINDER_WATER = "water"
REMINDER_LUNCH = "lunch"
REMINDER_DINNER = "dinner"
REMINDER_ORDER = [REMINDER_LUNCH, REMINDER_DINNER, REMINDER_WATER]


def now_local() -> datetime:
    return datetime.now().astimezone()


def parse_clock(value: str, fallback: str = "12:00") -> time:
    parsed = _try_parse_clock(value)
    if parsed:
        return parsed
    parsed_fallback = _try_parse_clock(fallback)
    if parsed_fallback:
        return parsed_fallback
    return time(hour=12, minute=0)


def combine_today(clock_text: str, fallback: str = "12:00") -> datetime:
    current = now_local()
    clock = parse_clock(clock_text, fallback=fallback)
    return current.replace(
        hour=clock.hour,
        minute=clock.minute,
        second=0,
        microsecond=0,
    )


def serialize_dt(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def deserialize_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def ensure_today(state: AppState, config: AppConfig) -> bool:
    today = date.today().isoformat()
    if state.stats.day == today:
        return False
    archive_current_day(state)
    state.stats = DayStats(day=today)
    state.next_water_due_at = serialize_dt(
        now_local() + timedelta(minutes=config.water_interval_minutes)
    )
    state.lunch_due_at = serialize_dt(combine_today(config.lunch_time, fallback="12:00"))
    state.dinner_due_at = serialize_dt(combine_today(config.dinner_time, fallback="18:30"))
    state.snoozed_until = {"water": None, "lunch": None, "dinner": None}
    state.reminder_cooldown_until = {"water": None, "lunch": None, "dinner": None}
    return True


def initialize_schedule(state: AppState, config: AppConfig) -> bool:
    _normalize_state_maps(state)
    changed = False
    if not state.next_water_due_at:
        state.next_water_due_at = serialize_dt(
            now_local() + timedelta(minutes=config.water_interval_minutes)
        )
        changed = True
    if not state.lunch_due_at:
        state.lunch_due_at = serialize_dt(combine_today(config.lunch_time, fallback="12:00"))
        changed = True
    if not state.dinner_due_at:
        state.dinner_due_at = serialize_dt(combine_today(config.dinner_time, fallback="18:30"))
        changed = True
    return changed


def sync_meal_schedule(state: AppState, config: AppConfig) -> None:
    state.lunch_due_at = serialize_dt(combine_today(config.lunch_time, fallback="12:00"))
    state.dinner_due_at = serialize_dt(combine_today(config.dinner_time, fallback="18:30"))


def reset_water_schedule(state: AppState, config: AppConfig) -> None:
    state.next_water_due_at = serialize_dt(
        now_local() + timedelta(minutes=config.water_interval_minutes)
    )
    state.snoozed_until[REMINDER_WATER] = None


def due_reminders(state: AppState) -> list[str]:
    current = now_local()
    results: list[str] = []
    for reminder_type in REMINDER_ORDER:
        if _is_due(state, reminder_type, current):
            results.append(reminder_type)

    return results


def next_due_reminder(state: AppState) -> str | None:
    due = due_reminders(state)
    return due[0] if due else None


def mark_done(state: AppState, config: AppConfig, reminder_type: str) -> None:
    current = now_local()
    state.snoozed_until[reminder_type] = None
    state.reminder_cooldown_until[reminder_type] = None
    if reminder_type == REMINDER_WATER:
        state.stats.water_count += 1
        state.next_water_due_at = serialize_dt(
            current + timedelta(minutes=config.water_interval_minutes)
        )
    elif reminder_type == REMINDER_LUNCH:
        state.stats.lunch_done = True
    elif reminder_type == REMINDER_DINNER:
        state.stats.dinner_done = True


def snooze_reminder(state: AppState, config: AppConfig, reminder_type: str) -> None:
    state.reminder_cooldown_until[reminder_type] = None
    state.snoozed_until[reminder_type] = serialize_dt(
        now_local() + timedelta(minutes=config.reminder_snooze_minutes)
    )


def skip_today(state: AppState, reminder_type: str) -> None:
    state.snoozed_until[reminder_type] = None
    state.reminder_cooldown_until[reminder_type] = None
    if reminder_type == REMINDER_WATER:
        state.stats.skipped_water = True
    elif reminder_type == REMINDER_LUNCH:
        state.stats.skipped_lunch = True
    elif reminder_type == REMINDER_DINNER:
        state.stats.skipped_dinner = True


def status_text(state: AppState) -> str:
    lunch = "已完成" if state.stats.lunch_done else "未完成"
    dinner = "已完成" if state.stats.dinner_done else "未完成"
    return (
        f"喝水 {state.stats.water_count} 次 | "
        f"午饭 {lunch} | 晚饭 {dinner}"
    )


def reminder_title(reminder_type: str) -> str:
    if reminder_type == REMINDER_WATER:
        return "喝水"
    if reminder_type == REMINDER_LUNCH:
        return "午饭"
    if reminder_type == REMINDER_DINNER:
        return "晚饭"
    return "提醒"


def summary_cards(state: AppState) -> list[dict[str, str]]:
    return [
        {
            "title": "今日喝水",
            "value": str(state.stats.water_count),
            "note": "次",
        },
        {
            "title": "午饭状态",
            "value": _meal_state_text(state.stats.lunch_done, state.stats.skipped_lunch),
            "note": "今天",
        },
        {
            "title": "晚饭状态",
            "value": _meal_state_text(state.stats.dinner_done, state.stats.skipped_dinner),
            "note": "今天",
        },
    ]


def upcoming_items(state: AppState) -> list[dict[str, str]]:
    current = now_local()
    items = [
        _build_upcoming_item(
            REMINDER_WATER,
            deserialize_dt(state.next_water_due_at),
            state.snoozed_until.get(REMINDER_WATER),
            state.stats.skipped_water,
            current,
        ),
        _build_upcoming_item(
            REMINDER_LUNCH,
            deserialize_dt(state.lunch_due_at),
            state.snoozed_until.get(REMINDER_LUNCH),
            state.stats.skipped_lunch or state.stats.lunch_done,
            current,
        ),
        _build_upcoming_item(
            REMINDER_DINNER,
            deserialize_dt(state.dinner_due_at),
            state.snoozed_until.get(REMINDER_DINNER),
            state.stats.skipped_dinner or state.stats.dinner_done,
            current,
        ),
    ]
    return items


def history_rows(state: AppState, limit: int = 7) -> list[dict[str, str]]:
    rows = []
    for entry in reversed(state.history[-limit:]):
        rows.append(
            {
                "day": entry.day,
                "water": f"{entry.water_count} 次",
                "lunch": entry.lunch_status,
                "dinner": entry.dinner_status,
            }
        )
    return rows


def archive_current_day(state: AppState, history_limit: int = 14) -> None:
    if not state.stats.day:
        return
    existing_days = {item.day for item in state.history}
    if state.stats.day not in existing_days:
        state.history.append(HistoryEntry.from_day_stats(state.stats))
    state.history = state.history[-history_limit:]


def mark_reminder_shown(
    state: AppState, reminder_type: str, cooldown_minutes: int
) -> None:
    state.reminder_cooldown_until[reminder_type] = serialize_dt(
        now_local() + timedelta(minutes=cooldown_minutes)
    )


def _is_snoozed(state: AppState, reminder_type: str, current: datetime) -> bool:
    snooze_until = deserialize_dt(state.snoozed_until.get(reminder_type))
    return bool(snooze_until and current < snooze_until)


def _is_cooldown_active(state: AppState, reminder_type: str, current: datetime) -> bool:
    cooldown_until = deserialize_dt(state.reminder_cooldown_until.get(reminder_type))
    return bool(cooldown_until and current < cooldown_until)


def _is_due(state: AppState, reminder_type: str, current: datetime) -> bool:
    if _is_snoozed(state, reminder_type, current):
        return False
    if _is_cooldown_active(state, reminder_type, current):
        return False

    if reminder_type == REMINDER_WATER:
        water_due = deserialize_dt(state.next_water_due_at)
        return bool(water_due and current >= water_due and not state.stats.skipped_water)

    if reminder_type == REMINDER_LUNCH:
        lunch_due = deserialize_dt(state.lunch_due_at)
        return bool(
            lunch_due
            and current >= lunch_due
            and not state.stats.lunch_done
            and not state.stats.skipped_lunch
        )

    if reminder_type == REMINDER_DINNER:
        dinner_due = deserialize_dt(state.dinner_due_at)
        return bool(
            dinner_due
            and current >= dinner_due
            and not state.stats.dinner_done
            and not state.stats.skipped_dinner
        )

    return False


def _normalize_state_maps(state: AppState) -> None:
    for key in (REMINDER_WATER, REMINDER_LUNCH, REMINDER_DINNER):
        state.snoozed_until.setdefault(key, None)
        state.reminder_cooldown_until.setdefault(key, None)


def _try_parse_clock(value: str) -> time | None:
    try:
        hour_text, minute_text = str(value).split(":", maxsplit=1)
        hour = int(hour_text)
        minute = int(minute_text)
    except (ValueError, TypeError):
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return time(hour=hour, minute=minute)


def _meal_state_text(done: bool, skipped: bool) -> str:
    if done:
        return "已完成"
    if skipped:
        return "已跳过"
    return "待完成"


def _build_upcoming_item(
    reminder_type: str,
    due_at: datetime | None,
    snoozed_until_text: str | None,
    disabled: bool,
    current: datetime,
) -> dict[str, str]:
    if disabled:
        return {
            "title": reminder_title(reminder_type),
            "time": "今日不再提醒",
            "detail": "已完成或已跳过",
        }

    snoozed_until = deserialize_dt(snoozed_until_text)
    if snoozed_until and current < snoozed_until:
        return {
            "title": reminder_title(reminder_type),
            "time": snoozed_until.strftime("%H:%M"),
            "detail": "已延后提醒",
        }

    if not due_at:
        return {
            "title": reminder_title(reminder_type),
            "time": "--:--",
            "detail": "等待初始化",
        }

    if current >= due_at:
        return {
            "title": reminder_title(reminder_type),
            "time": "现在",
            "detail": "提醒已触发",
        }

    return {
        "title": reminder_title(reminder_type),
        "time": due_at.strftime("%H:%M"),
        "detail": _relative_text(due_at - current),
    }


def _relative_text(delta: timedelta) -> str:
    minutes = max(1, int(delta.total_seconds() // 60))
    if minutes < 60:
        return f"{minutes} 分钟后"
    hours, remain_minutes = divmod(minutes, 60)
    if remain_minutes == 0:
        return f"{hours} 小时后"
    return f"{hours} 小时 {remain_minutes} 分钟后"
