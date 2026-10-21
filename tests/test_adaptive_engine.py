import random

from learning_helper.adaptive.engine import AdaptiveEngine
from learning_helper.adaptive.models import ChallengeChoice, ChallengeSpec
from learning_helper.config import (
    ACCURACY_WINDOW,
    INITIAL_INTERVAL_SECONDS,
    INTERVAL_STEP_SECONDS,
    MAX_INTERVAL_SECONDS,
    MAX_LEVEL,
    MIN_INTERVAL_SECONDS,
    MODULE_ORDER,
    RuntimeConfig,
)
from learning_helper.persistence.db import Store
from learning_helper.settings import Settings


def _spec(module_id: str = "colors", level: int = 1, correct: str = "a") -> ChallengeSpec:
    return ChallengeSpec(
        module_id=module_id,
        level=level,
        prompt="pergunta",
        choices=(
            ChallengeChoice(id="a", label="A"),
            ChallengeChoice(id="b", label="B"),
        ),
        correct_id=correct,
    )


def _fill(engine: AdaptiveEngine, module_id: str, correct_count: int, total: int = ACCURACY_WINDOW) -> None:
    for index in range(total):
        given = "a" if index < correct_count else "b"
        engine.record_attempt(_spec(module_id=module_id), given)


def test_starts_only_with_colors(engine: AdaptiveEngine) -> None:
    assert engine.profile().unlocked_modules == ["colors"]
    assert engine.pick_module() == "colors"


def test_pick_module_only_unlocked(store: Store) -> None:
    engine = AdaptiveEngine(store, rng=random.Random(0))
    _fill(engine, "colors", ACCURACY_WINDOW)
    assert "math" in engine.profile().unlocked_modules
    picks = {engine.pick_module() for _ in range(40)}
    assert picks <= {"colors", "math"}
    assert "questions" not in picks


def test_unlocks_next_module_after_high_accuracy(engine: AdaptiveEngine) -> None:
    _fill(engine, "colors", 9)
    profile = engine.profile()
    assert "math" in profile.unlocked_modules
    assert profile.levels["colors"] >= 2


def test_does_not_unlock_when_accuracy_is_low(engine: AdaptiveEngine) -> None:
    _fill(engine, "colors", 3)
    assert engine.profile().unlocked_modules == ["colors"]


def test_level_down_on_low_accuracy(engine: AdaptiveEngine) -> None:
    profile = engine.profile()
    profile.levels["colors"] = 3
    engine.store.save_profile(profile)
    _fill(engine, "colors", 2)
    assert engine.profile().levels["colors"] == 2


def test_level_does_not_go_below_one(engine: AdaptiveEngine) -> None:
    _fill(engine, "colors", 1)
    assert engine.profile().levels["colors"] == 1


def test_level_does_not_exceed_max(engine: AdaptiveEngine) -> None:
    profile = engine.profile()
    profile.levels["colors"] = MAX_LEVEL
    engine.store.save_profile(profile)
    _fill(engine, "colors", ACCURACY_WINDOW)
    assert engine.profile().levels["colors"] == MAX_LEVEL


def test_unlock_order_follows_module_order(engine: AdaptiveEngine) -> None:
    _fill(engine, "colors", ACCURACY_WINDOW)
    assert engine.profile().unlocked_modules[-1] == "math"
    _fill(engine, "math", ACCURACY_WINDOW)
    assert engine.profile().unlocked_modules[-1] == "problems"
    _fill(engine, "problems", ACCURACY_WINDOW)
    assert engine.profile().unlocked_modules[-1] == "questions"
    _fill(engine, "questions", ACCURACY_WINDOW)
    assert engine.profile().unlocked_modules == list(MODULE_ORDER)


def test_adult_pause_does_not_insert_attempt(engine: AdaptiveEngine) -> None:
    engine.pause_for_adult(seconds=60)
    assert engine.is_paused()
    assert engine.store.count_attempts() == 0


def test_interval_starts_at_initial_value(engine: AdaptiveEngine) -> None:
    assert engine.next_interval_seconds() == INITIAL_INTERVAL_SECONDS


def test_correct_answer_increases_interval(engine: AdaptiveEngine) -> None:
    engine.record_attempt(_spec(), "a")
    assert engine.next_interval_seconds() == INITIAL_INTERVAL_SECONDS + INTERVAL_STEP_SECONDS


def test_wrong_answer_decreases_interval(engine: AdaptiveEngine) -> None:
    engine.record_attempt(_spec(), "b")
    assert engine.next_interval_seconds() == INITIAL_INTERVAL_SECONDS - INTERVAL_STEP_SECONDS


def test_interval_never_exceeds_maximum(engine: AdaptiveEngine) -> None:
    for _ in range(10):
        engine.record_attempt(_spec(), "a")
    assert engine.next_interval_seconds() == MAX_INTERVAL_SECONDS


def test_interval_never_goes_below_minimum(engine: AdaptiveEngine) -> None:
    for _ in range(10):
        engine.record_attempt(_spec(), "b")
    assert engine.next_interval_seconds() == MIN_INTERVAL_SECONDS


def test_interval_persists_between_engines(store: Store) -> None:
    engine = AdaptiveEngine(store)
    engine.record_attempt(_spec(), "a")
    reloaded = AdaptiveEngine(store)
    assert reloaded.next_interval_seconds() == INITIAL_INTERVAL_SECONDS + INTERVAL_STEP_SECONDS


def test_debug_config_keeps_short_fixed_delay() -> None:
    config = RuntimeConfig(debug=True)
    assert (
        config.delay_ms(
            MAX_INTERVAL_SECONDS, MIN_INTERVAL_SECONDS, MAX_INTERVAL_SECONDS
        )
        == 10_000
    )


def test_config_clamps_adaptive_delay() -> None:
    config = RuntimeConfig()
    assert (
        config.delay_ms(0, MIN_INTERVAL_SECONDS, MAX_INTERVAL_SECONDS)
        == MIN_INTERVAL_SECONDS * 1000
    )
    assert (
        config.delay_ms(10_000, MIN_INTERVAL_SECONDS, MAX_INTERVAL_SECONDS)
        == MAX_INTERVAL_SECONDS * 1000
    )


def test_custom_interval_bounds_and_step(engine: AdaptiveEngine) -> None:
    engine.store.save_settings(
        Settings(
            initial_interval_seconds=120,
            min_interval_seconds=100,
            max_interval_seconds=140,
            interval_step_seconds=5,
        )
    )
    profile = engine.profile()
    profile.interval_seconds = 120
    engine.store.save_profile(profile)

    engine.record_attempt(_spec(), "a")
    assert engine.next_interval_seconds() == 125

    for _ in range(20):
        engine.record_attempt(_spec(), "a")
    assert engine.next_interval_seconds() == 140


def test_lower_unlock_threshold_unlocks_earlier(engine: AdaptiveEngine) -> None:
    engine.store.save_settings(Settings(unlock_threshold=0.5))
    _fill(engine, "colors", 5)
    assert "math" in engine.profile().unlocked_modules


def test_disabled_modules_are_skipped_when_unlocking(engine: AdaptiveEngine) -> None:
    engine.store.save_settings(
        Settings(enabled_modules=("colors", "problems"))
    )
    _fill(engine, "colors", ACCURACY_WINDOW)
    unlocked = engine.profile().unlocked_modules
    assert "problems" in unlocked
    assert "math" not in unlocked


def test_pick_module_falls_back_to_an_enabled_module(engine: AdaptiveEngine) -> None:
    engine.store.save_settings(Settings(enabled_modules=("reading",)))
    assert engine.pick_module() == "reading"
    assert "reading" in engine.profile().unlocked_modules


def test_custom_max_level_is_respected(engine: AdaptiveEngine) -> None:
    engine.store.save_settings(Settings(max_level=2))
    profile = engine.profile()
    profile.levels["colors"] = 2
    engine.store.save_profile(profile)
    _fill(engine, "colors", ACCURACY_WINDOW)
    assert engine.profile().levels["colors"] == 2


def test_disabled_module_levels_are_not_adapted(engine: AdaptiveEngine) -> None:
    engine.store.save_settings(
        Settings(enabled_modules=("math",), max_level=5)
    )
    profile = engine.profile()
    profile.unlocked_modules = ["colors", "math"]
    profile.levels["colors"] = 2
    profile.levels["math"] = 1
    engine.store.save_profile(profile)

    _fill(engine, "colors", ACCURACY_WINDOW)
    assert engine.profile().levels["colors"] == 2


def test_unlock_skips_disabled_modules_at_the_frontier(engine: AdaptiveEngine) -> None:
    engine.store.save_settings(
        Settings(enabled_modules=("colors", "problems"))
    )
    profile = engine.profile()
    profile.unlocked_modules = ["colors", "math"]
    profile.levels["math"] = 1
    profile.levels["problems"] = 1
    engine.store.save_profile(profile)

    _fill(engine, "colors", ACCURACY_WINDOW)
    unlocked = engine.profile().unlocked_modules
    assert "problems" in unlocked
    assert "math" in unlocked
