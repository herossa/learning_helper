from datetime import datetime, timedelta, timezone

from learning_helper import reminders

INTERVAL = 30 * 60
NOW = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)


def test_first_reminder_waits_a_full_interval() -> None:
    assert reminders.seconds_until_next(None, NOW, INTERVAL) == INTERVAL


def test_seconds_shrink_as_time_passes() -> None:
    last = NOW - timedelta(minutes=10)
    assert reminders.seconds_until_next(last, NOW, INTERVAL) == INTERVAL - 600


def test_overdue_reminder_is_due_now() -> None:
    last = NOW - timedelta(minutes=40)
    assert reminders.seconds_until_next(last, NOW, INTERVAL) == 0


def test_clock_skew_never_exceeds_one_interval() -> None:
    last = NOW + timedelta(hours=1)
    assert reminders.seconds_until_next(last, NOW, INTERVAL) == INTERVAL


def test_non_positive_interval_is_immediately_due() -> None:
    assert reminders.seconds_until_next(None, NOW, 0) == 0


def test_format_countdown() -> None:
    assert reminders.format_countdown(60) == "01:00"
    assert reminders.format_countdown(59) == "00:59"
    assert reminders.format_countdown(0) == "00:00"
    assert reminders.format_countdown(-5) == "00:00"
    assert reminders.format_countdown(3599) == "59:59"
