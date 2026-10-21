import sqlite3
from datetime import datetime, timezone

from learning_helper.adaptive.models import Profile
from learning_helper.config import INITIAL_INTERVAL_SECONDS
from learning_helper.persistence.db import Store
from learning_helper.settings import Settings


def test_schema_and_profile_defaults(store: Store) -> None:
    profile = store.get_profile()
    assert profile.unlocked_modules == ["colors"]
    assert profile.levels["colors"] == 1
    assert profile.interval_seconds == INITIAL_INTERVAL_SECONDS
    assert store.count_attempts() == 0


def test_insert_attempt_roundtrip(store: Store) -> None:
    created = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)
    attempt = store.insert_attempt(
        module_id="colors",
        level=1,
        prompt="Qual é o quadrado Azul?",
        choices=["blue", "red", "green"],
        correct_answer="blue",
        given_answer="red",
        is_correct=False,
        spec_json={"kind": "color_square"},
        created_at=created,
    )
    assert attempt.id == 1
    assert store.count_attempts("colors") == 1
    recent = store.recent_attempts("colors", 10)
    assert len(recent) == 1
    saved = recent[0]
    assert saved.prompt == "Qual é o quadrado Azul?"
    assert saved.choices == ["blue", "red", "green"]
    assert saved.correct_answer == "blue"
    assert saved.given_answer == "red"
    assert saved.is_correct is False
    assert saved.spec_json == {"kind": "color_square"}


def test_profile_roundtrip(store: Store) -> None:
    profile = Profile(
        unlocked_modules=["colors", "math"],
        levels={"colors": 2, "math": 1, "questions": 1, "reading": 1},
        interval_seconds=240,
    )
    store.save_profile(profile)
    loaded = store.get_profile()
    assert loaded.unlocked_modules == ["colors", "math"]
    assert loaded.levels["colors"] == 2
    assert loaded.interval_seconds == 240


def test_bathroom_defaults(store: Store) -> None:
    settings = store.get_settings()
    assert settings.bathroom_reminder_enabled is True
    assert store.get_profile().last_bathroom_reminder_at is None


def test_bathroom_fields_roundtrip(store: Store) -> None:
    reminded_at = datetime(2026, 10, 21, 12, 0, tzinfo=timezone.utc)
    profile = store.get_profile()
    profile.last_bathroom_reminder_at = reminded_at
    store.save_profile(profile)
    settings = store.get_settings()
    store.save_settings(
        Settings(bathroom_reminder_enabled=False)
    )

    loaded = store.get_profile()
    assert loaded.last_bathroom_reminder_at == reminded_at
    assert store.get_settings().bathroom_reminder_enabled is False
    assert settings.bathroom_reminder_enabled is True


def test_migration_adds_problems_after_math(store: Store) -> None:
    profile = store.get_profile()
    profile.unlocked_modules = ["colors", "math", "questions", "reading"]
    store.save_profile(profile)

    reopened = Store(store.db_path)
    loaded = reopened.get_profile()
    assert loaded.unlocked_modules == ["colors", "math", "problems", "questions", "reading"]
    assert loaded.levels["problems"] == 1


def test_migration_does_not_duplicate_problems(store: Store) -> None:
    profile = store.get_profile()
    profile.unlocked_modules = ["colors", "math", "problems"]
    store.save_profile(profile)

    reopened = Store(store.db_path)
    assert reopened.get_profile().unlocked_modules == ["colors", "math", "problems"]


def test_migrates_profile_without_interval_column(tmp_path) -> None:
    db_path = tmp_path / "old.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            unlocked_modules_json TEXT NOT NULL,
            levels_json TEXT NOT NULL,
            last_interrupt_at TEXT,
            adult_pause_until TEXT
        );
        INSERT INTO profile (id, unlocked_modules_json, levels_json)
        VALUES (1, '["colors", "math"]', '{"colors": 2, "math": 1}');
        """
    )
    conn.commit()
    conn.close()

    store = Store(db_path)
    profile = store.get_profile()
    assert profile.interval_seconds == INITIAL_INTERVAL_SECONDS
    assert profile.unlocked_modules == ["colors", "math", "problems"]
    assert profile.levels["colors"] == 2
    assert profile.last_bathroom_reminder_at is None
    assert store.get_settings().bathroom_reminder_enabled is True
    assert store.onboarding_completed() is True


def test_recent_attempts_are_oldest_first_in_window(store: Store) -> None:
    for index in range(3):
        store.insert_attempt(
            module_id="math",
            level=1,
            prompt=f"{index}+1",
            choices=["1", "2", "3"],
            correct_answer="2",
            given_answer="2" if index else "1",
            is_correct=bool(index),
        )
    recent = store.recent_attempts("math", 3)
    assert [item.prompt for item in recent] == ["0+1", "1+1", "2+1"]


def test_new_database_starts_onboarding_incomplete(store: Store) -> None:
    assert store.onboarding_completed() is False
    store.complete_onboarding()
    assert store.onboarding_completed() is True


def test_existing_database_is_treated_as_onboarded(tmp_path) -> None:
    db_path = tmp_path / "legacy.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(
        """
        CREATE TABLE profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            unlocked_modules_json TEXT NOT NULL,
            levels_json TEXT NOT NULL,
            last_interrupt_at TEXT,
            adult_pause_until TEXT,
            interval_seconds INTEGER NOT NULL DEFAULT 180,
            last_bathroom_reminder_at TEXT,
            bathroom_reminder_enabled INTEGER NOT NULL DEFAULT 1
        );
        INSERT INTO profile (
            id, unlocked_modules_json, levels_json, bathroom_reminder_enabled
        ) VALUES (1, '["colors"]', '{"colors": 1}', 0);
        """
    )
    conn.commit()
    conn.close()

    store = Store(db_path)
    try:
        assert store.onboarding_completed() is True
        assert store.get_settings().bathroom_reminder_enabled is False
    finally:
        store.close()


def test_settings_roundtrip_and_validation(store: Store) -> None:
    settings = Settings(
        initial_interval_seconds=120,
        min_interval_seconds=60,
        max_interval_seconds=600,
        enabled_modules=("colors", "reading"),
    )
    saved = store.save_settings(settings)
    assert saved.initial_interval_seconds == 120
    loaded = store.get_settings()
    assert loaded.enabled_modules == ("colors", "reading")
    assert loaded.initial_interval_seconds == 120

    import pytest

    with pytest.raises(ValueError):
        store.save_settings(
            Settings(
                min_interval_seconds=600,
                max_interval_seconds=60,
                initial_interval_seconds=120,
            )
        )


def test_settings_survive_unknown_json_fields(store: Store) -> None:
    import json

    conn = sqlite3.connect(store.db_path)
    conn.execute(
        "UPDATE settings SET values_json = ? WHERE id = 1",
        (json.dumps({"initial_interval_seconds": 240, "future_option": True}),),
    )
    conn.commit()
    conn.close()

    reopened = Store(store.db_path)
    try:
        assert reopened.get_settings().initial_interval_seconds == 240
    finally:
        reopened.close()
