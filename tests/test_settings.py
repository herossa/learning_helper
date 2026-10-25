import json

import pytest

from learning_helper.config import (
    ACCURACY_WINDOW,
    ADULT_PAUSE_SECONDS,
    BATHROOM_DURATION_SECONDS,
    BATHROOM_INTERVAL_SECONDS,
    DAILY_USAGE_LIMIT_SECONDS,
    FEEDBACK_MS,
    INITIAL_INTERVAL_SECONDS,
    INTERVAL_STEP_SECONDS,
    LEVEL_DOWN_THRESHOLD,
    LEVEL_UP_THRESHOLD,
    MAX_INTERVAL_SECONDS,
    MAX_LEVEL,
    MIN_INTERVAL_SECONDS,
    MODULE_ORDER,
    UNLOCK_THRESHOLD,
    WRONG_ANSWER_WAIT_SECONDS,
)
from learning_helper.security import hash_password
from learning_helper.settings import MAX_PASSWORD_HASH_LENGTH, Settings


def test_defaults_match_config_constants() -> None:
    settings = Settings()
    assert settings.initial_interval_seconds == INITIAL_INTERVAL_SECONDS
    assert settings.min_interval_seconds == MIN_INTERVAL_SECONDS
    assert settings.max_interval_seconds == MAX_INTERVAL_SECONDS
    assert settings.interval_step_seconds == INTERVAL_STEP_SECONDS
    assert settings.accuracy_window == ACCURACY_WINDOW
    assert settings.unlock_threshold == UNLOCK_THRESHOLD
    assert settings.level_up_threshold == LEVEL_UP_THRESHOLD
    assert settings.level_down_threshold == LEVEL_DOWN_THRESHOLD
    assert settings.max_level == MAX_LEVEL
    assert settings.feedback_ms == FEEDBACK_MS
    assert settings.wrong_answer_wait_seconds == WRONG_ANSWER_WAIT_SECONDS
    assert settings.daily_usage_limit_seconds == DAILY_USAGE_LIMIT_SECONDS
    assert settings.extension_password_hash == ""
    assert settings.adult_pause_seconds == ADULT_PAUSE_SECONDS
    assert settings.bathroom_interval_seconds == BATHROOM_INTERVAL_SECONDS
    assert settings.bathroom_duration_seconds == BATHROOM_DURATION_SECONDS
    assert settings.enabled_modules == MODULE_ORDER


def test_json_roundtrip() -> None:
    settings = Settings(
        initial_interval_seconds=120,
        max_interval_seconds=600,
        enabled_modules=("colors", "reading"),
        level_up_threshold=0.9,
    )
    loaded = Settings.from_json(settings.to_json())
    assert loaded == settings


def test_from_json_handles_garbage() -> None:
    assert Settings.from_json(None) == Settings()
    assert Settings.from_json("") == Settings()
    assert Settings.from_json("{") == Settings()
    assert Settings.from_json("[]") == Settings()


def test_from_dict_ignores_unknown_fields_and_casts() -> None:
    loaded = Settings.from_dict(
        {
            "initial_interval_seconds": "240",
            "unlock_threshold": "0.5",
            "enabled_modules": ["reading", "math", "reading"],
            "future_option": True,
        }
    )
    assert loaded.initial_interval_seconds == 240
    assert loaded.unlock_threshold == 0.5
    assert loaded.enabled_modules == ("math", "reading")


def test_normalized_clamps_out_of_range_values() -> None:
    loaded = Settings(
        initial_interval_seconds=1,
        min_interval_seconds=1,
        max_interval_seconds=99_999,
        interval_step_seconds=1,
        accuracy_window=100,
        unlock_threshold=2.0,
        level_up_threshold=1.5,
        level_down_threshold=-1.0,
        max_level=99,
        feedback_ms=1,
        wrong_answer_wait_seconds=1,
        adult_pause_seconds=1,
        bathroom_interval_seconds=1,
        bathroom_duration_seconds=10_000,
        enabled_modules=(),
    ).normalized()
    assert loaded.min_interval_seconds == 60
    assert loaded.max_interval_seconds == 3600
    assert loaded.initial_interval_seconds == 60
    assert loaded.interval_step_seconds == 5
    assert loaded.accuracy_window == 50
    assert loaded.unlock_threshold == 1.0
    assert loaded.level_up_threshold == 1.0
    assert loaded.level_down_threshold == 0.0
    assert loaded.max_level == MAX_LEVEL
    assert loaded.feedback_ms == 500
    assert loaded.wrong_answer_wait_seconds == 10
    assert loaded.adult_pause_seconds == 60
    assert loaded.bathroom_interval_seconds == 5 * 60
    assert loaded.bathroom_duration_seconds == 300
    assert loaded.enabled_modules == MODULE_ORDER


def test_wrong_answer_wait_is_clamped() -> None:
    assert (
        Settings(wrong_answer_wait_seconds=1).normalized()
        .wrong_answer_wait_seconds
        == 10
    )
    assert (
        Settings(wrong_answer_wait_seconds=10_000).normalized()
        .wrong_answer_wait_seconds
        == 300
    )


def test_daily_limit_is_clamped() -> None:
    assert (
        Settings(daily_usage_limit_seconds=1).normalized()
        .daily_usage_limit_seconds
        == 15 * 60
    )
    assert (
        Settings(daily_usage_limit_seconds=99_999).normalized()
        .daily_usage_limit_seconds
        == 24 * 60 * 60
    )


def test_daily_limit_and_password_roundtrip() -> None:
    password_hash = hash_password("abcd")
    settings = Settings(
        daily_usage_limit_seconds=90 * 60,
        extension_password_hash=password_hash,
    )

    loaded = Settings.from_json(settings.to_json())

    assert loaded.daily_usage_limit_seconds == 90 * 60
    assert loaded.extension_password_hash == password_hash


def test_from_dict_keeps_password_hash_as_text() -> None:
    loaded = Settings.from_dict(
        {
            "daily_usage_limit_seconds": "5400",
            "extension_password_hash": "hash-qualquer",
        }
    )

    assert loaded.daily_usage_limit_seconds == 5400
    assert loaded.extension_password_hash == "hash-qualquer"


def test_password_hash_is_truncated_to_a_safe_length() -> None:
    loaded = Settings(
        extension_password_hash="x" * (MAX_PASSWORD_HASH_LENGTH + 20)
    ).normalized()

    assert len(loaded.extension_password_hash) == MAX_PASSWORD_HASH_LENGTH


def test_validate_rejects_bad_daily_limit() -> None:
    errors = Settings(daily_usage_limit_seconds=60).validate()

    assert any("limite de uso diário" in error for error in errors)


def test_normalized_keeps_minimum_below_maximum() -> None:
    loaded = Settings(
        min_interval_seconds=900,
        max_interval_seconds=120,
        initial_interval_seconds=180,
    ).normalized()
    assert loaded.min_interval_seconds == 900
    assert loaded.max_interval_seconds == 900
    assert loaded.initial_interval_seconds == 900


def test_validate_accepts_defaults() -> None:
    assert Settings().validate() == []


def test_validate_rejects_bad_interval() -> None:
    errors = Settings(
        min_interval_seconds=600,
        max_interval_seconds=60,
    ).validate()
    assert any("máximo" in error for error in errors)


def test_validate_rejects_bad_thresholds() -> None:
    errors = Settings(level_down_threshold=0.95, level_up_threshold=0.9).validate()
    assert any("descer de nível" in error for error in errors)


def test_validate_rejects_empty_and_unknown_modules() -> None:
    assert any("pelo menos um" in error for error in Settings(enabled_modules=()).validate())
    assert any(
        "desconhecido" in error
        for error in Settings(enabled_modules=("colors", "nope")).validate()
    )


def test_validate_reports_each_invalid_field() -> None:
    errors = Settings(
        initial_interval_seconds=10,
        min_interval_seconds=10,
        max_interval_seconds=10,
        interval_step_seconds=1,
        accuracy_window=1,
        max_level=0,
        feedback_ms=1,
        wrong_answer_wait_seconds=1,
        adult_pause_seconds=1,
        bathroom_interval_seconds=1,
        bathroom_duration_seconds=1,
    ).validate()
    assert len(errors) >= 10


def test_from_json_unknown_keeps_defaults() -> None:
    loaded = Settings.from_json(json.dumps({"bathroom_reminder_enabled": False}))
    assert loaded.bathroom_reminder_enabled is False
    assert loaded == Settings(bathroom_reminder_enabled=False)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(True, True), (False, False), (0, False), (1, True)],
)
def test_bathroom_boolean_coercion(value: object, expected: bool) -> None:
    loaded = Settings.from_dict({"bathroom_reminder_enabled": value})
    assert loaded.bathroom_reminder_enabled is expected


def test_update_check_is_enabled_by_default() -> None:
    assert Settings().update_check_on_startup is True


@pytest.mark.parametrize(
    ("value", "expected"),
    [(True, True), (False, False), (0, False), (1, True)],
)
def test_update_check_boolean_coercion(value: object, expected: bool) -> None:
    loaded = Settings.from_dict({"update_check_on_startup": value})
    assert loaded.update_check_on_startup is expected
