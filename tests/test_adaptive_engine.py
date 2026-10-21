import random

from learning_helper.adaptive.engine import AdaptiveEngine
from learning_helper.adaptive.models import ChallengeChoice, ChallengeSpec
from learning_helper.config import ACCURACY_WINDOW, MAX_LEVEL
from learning_helper.persistence.db import Store


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


def test_unlock_order_colors_math_questions_reading(engine: AdaptiveEngine) -> None:
    _fill(engine, "colors", ACCURACY_WINDOW)
    _fill(engine, "math", ACCURACY_WINDOW)
    assert engine.profile().unlocked_modules[-1] == "questions"
    _fill(engine, "questions", ACCURACY_WINDOW)
    assert engine.profile().unlocked_modules == ["colors", "math", "questions", "reading"]


def test_adult_pause_does_not_insert_attempt(engine: AdaptiveEngine) -> None:
    engine.pause_for_adult(seconds=60)
    assert engine.is_paused()
    assert engine.store.count_attempts() == 0
