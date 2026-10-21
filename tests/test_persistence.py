from datetime import datetime, timezone

from learning_helper.adaptive.models import Profile
from learning_helper.persistence.db import Store


def test_schema_and_profile_defaults(store: Store) -> None:
    profile = store.get_profile()
    assert profile.unlocked_modules == ["colors"]
    assert profile.levels["colors"] == 1
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
    )
    store.save_profile(profile)
    loaded = store.get_profile()
    assert loaded.unlocked_modules == ["colors", "math"]
    assert loaded.levels["colors"] == 2


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
