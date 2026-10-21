import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from learning_helper.adaptive.models import Profile
from learning_helper.persistence.db import Store
from learning_helper.settings import Settings
from learning_helper.stats import data


@pytest.fixture
def populated(tmp_path: Path) -> Path:
    db_path = tmp_path / "stats.db"
    store = Store(db_path)
    try:
        records = [
            ("colors", 1, True, datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)),
            ("colors", 1, False, datetime(2026, 10, 20, 13, 0, tzinfo=timezone.utc)),
            ("math", 2, True, datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)),
            ("math", 3, True, datetime(2026, 10, 21, 14, 0, tzinfo=timezone.utc)),
        ]
        for module, level, correct, created in records:
            store.insert_attempt(
                module_id=module,
                level=level,
                prompt=f"{module}-{level}",
                choices=["a", "b"],
                correct_answer="a",
                given_answer="a" if correct else "b",
                is_correct=correct,
                created_at=created,
            )
        store.save_profile(
            Profile(
                unlocked_modules=["colors", "math"],
                levels={"colors": 2, "math": 3, "problems": 1},
            )
        )
        store.save_settings(
            Settings(
                enabled_modules=("colors", "math", "problems"),
                bathroom_reminder_enabled=False,
            )
        )
    finally:
        store.close()
    return db_path


def test_load_attempts_and_filters(populated: Path) -> None:
    records = data.load_attempts(populated)
    assert len(records) == 4
    assert records[0].created_at.tzinfo is timezone.utc

    colors = data.load_attempts(populated, module_ids=("colors",))
    assert [record.module_id for record in colors] == ["colors", "colors"]

    since = datetime(2026, 10, 21, tzinfo=timezone.utc)
    recent = data.load_attempts(populated, since=since)
    assert len(recent) == 2
    assert data.load_attempts(populated, module_ids=()) == []


def test_kpis(populated: Path) -> None:
    totals = data.kpis(data.load_attempts(populated))
    assert totals.attempts == 4
    assert totals.correct == 3
    assert totals.accuracy == pytest.approx(0.75)
    assert totals.active_days == 2


def test_by_module(populated: Path) -> None:
    summaries = {item.module_id: item for item in data.by_module(data.load_attempts(populated))}
    assert summaries["colors"].attempts == 2
    assert summaries["colors"].accuracy == pytest.approx(0.5)
    assert summaries["colors"].last_level == 1
    assert summaries["math"].attempts == 2
    assert summaries["math"].accuracy == pytest.approx(1.0)
    assert summaries["math"].last_level == 3


def test_by_day_uses_local_dates(populated: Path) -> None:
    daily = data.by_day(data.load_attempts(populated))
    assert len(daily) == 2
    assert daily[0].day < daily[1].day
    assert sum(item.attempts for item in daily) == 4


def test_by_level(populated: Path) -> None:
    levels = data.by_level(data.load_attempts(populated))
    assert [(item.module_id, item.level, item.attempts) for item in levels] == [
        ("colors", 1, 2),
        ("math", 2, 1),
        ("math", 3, 1),
    ]


def test_recent_is_newest_first(populated: Path) -> None:
    records = data.recent(data.load_attempts(populated), limit=2)
    assert [record.prompt for record in records] == ["math-3", "math-2"]
    assert records[0].created_at > records[1].created_at


def test_load_profile(populated: Path) -> None:
    profile = data.load_profile(populated)
    assert profile is not None
    assert profile.levels["colors"] == 2
    assert profile.levels["math"] == 3
    assert profile.unlocked == ("colors", "math")
    assert profile.enabled_modules == ("colors", "math", "problems")


def test_missing_database_raises() -> None:
    with pytest.raises(data.StatsDataError):
        data.load_attempts(Path("/nonexistent/learning_helper.db"))


def test_database_without_tables_raises(tmp_path: Path) -> None:
    path = tmp_path / "empty.db"
    sqlite3.connect(path).close()
    with pytest.raises(data.StatsDataError):
        data.load_attempts(path)


def test_connection_is_read_only(populated: Path) -> None:
    with data._readonly_connection(populated) as connection:
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("DELETE FROM attempts")
