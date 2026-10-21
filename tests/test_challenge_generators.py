import random

from learning_helper.challenges.banks import load_bank
from learning_helper.challenges.colors import PRIMARY_COLOR_DATA, build_colors_challenge
from learning_helper.challenges.math import build_math_challenge
from learning_helper.challenges.questions import build_questions_challenge
from learning_helper.challenges.reading import build_reading_challenge
from learning_helper.challenges.registry import build_challenge


def test_colors_correct_is_among_choices() -> None:
    rng = random.Random(1)
    spec = build_colors_challenge(1, rng)
    ids = spec.choice_ids()
    assert spec.correct_id in ids
    assert spec.correct_id in PRIMARY_COLOR_DATA
    assert len(ids) == 3
    assert spec.prompt.startswith("Qual é o quadrado")


def test_colors_more_choices_at_higher_level() -> None:
    low = build_colors_challenge(1, random.Random(2))
    high = build_colors_challenge(4, random.Random(2))
    assert len(high.choices) > len(low.choices)


def test_math_result_matches_prompt() -> None:
    for level in range(1, 6):
        spec = build_math_challenge(level, random.Random(level + 10))
        a = spec.metadata["a"]
        b = spec.metadata["b"]
        op = spec.metadata["op"]
        expected = {"+": a + b, "-": a - b, "*": a * b}[op]
        assert spec.correct_id == str(expected)
        assert spec.correct_id in spec.choice_ids()
        assert expected >= 0
        assert len(spec.choices) == 4


def test_questions_answer_in_options() -> None:
    bank = load_bank("questions")
    assert bank
    spec = build_questions_challenge(2, random.Random(3))
    assert spec.correct_id in spec.choice_ids()
    assert spec.prompt


def test_reading_answer_in_options() -> None:
    bank = load_bank("reading")
    assert bank
    spec = build_reading_challenge(1, random.Random(4))
    assert spec.correct_id in spec.choice_ids()
    assert "____" in spec.prompt or "escrita certo" in spec.prompt


def test_registry_builds_all_modules() -> None:
    rng = random.Random(0)
    for module_id in ("colors", "math", "questions", "reading"):
        spec = build_challenge(module_id, 1, rng)
        assert spec.module_id == module_id
        assert spec.correct_id in spec.choice_ids()
