import random

from learning_helper.challenges.banks import load_bank
from learning_helper.challenges.colors import PRIMARY_COLOR_DATA, build_colors_challenge
from learning_helper.challenges.comparison import build_comparison_challenge
from learning_helper.challenges.math import build_math_challenge
from learning_helper.challenges.problems import NAMES, build_problems_challenge
from learning_helper.challenges.questions import build_questions_challenge
from learning_helper.challenges.reading import build_reading_challenge
from learning_helper.challenges.registry import build_challenge
from learning_helper.config import MODULE_ORDER


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


def test_problems_result_matches_prompt() -> None:
    rng = random.Random(7)
    for level in range(1, 6):
        for _ in range(200):
            spec = build_problems_challenge(level, rng)
            a = spec.metadata["a"]
            b = spec.metadata["b"]
            op = spec.metadata["op"]
            expected = {"+": a + b, "-": a - b, "*": a * b}[op]
            assert spec.correct_id == str(expected)
            assert expected >= 0
            assert spec.correct_id in spec.choice_ids()
            assert len(spec.choices) == 4
            assert len(spec.choice_ids()) == 4
            assert all(int(choice.id) >= 0 for choice in spec.choices)
            if op == "-":
                assert a >= b
            assert spec.prompt.endswith("?")
            assert "{" not in spec.prompt and "}" not in spec.prompt
            assert spec.module_id == "problems"


def test_problems_uses_story_text() -> None:
    spec = build_problems_challenge(1, random.Random(11))
    assert any(name in spec.prompt for name in NAMES)
    assert spec.metadata["scenario"]
    assert spec.metadata["item"]


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


def test_comparison_asks_for_larger_or_smaller_number() -> None:
    rng = random.Random(5)
    for level in range(1, 6):
        for _ in range(100):
            spec = build_comparison_challenge(level, rng)
            a = spec.metadata["a"]
            b = spec.metadata["b"]
            comparison = spec.metadata["comparison"]
            expected = max(a, b) if comparison == "maior" else min(a, b)

            assert spec.module_id == "compare"
            assert a != b
            assert comparison in ("maior", "menor")
            assert f"é {comparison}?" in spec.prompt
            assert str(a) in spec.prompt
            assert str(b) in spec.prompt
            assert spec.correct_id == str(expected)
            assert spec.correct_id == str(spec.metadata["answer"])
            assert spec.input_mode == "text"
            assert spec.choices == ()


def test_comparison_accepts_whitespace_and_leading_zero() -> None:
    spec = build_comparison_challenge(1, random.Random(1))
    answer = spec.correct_id
    wrong = spec.metadata["b"] if answer == str(spec.metadata["a"]) else spec.metadata["a"]

    assert spec.is_correct(answer)
    assert spec.is_correct(f" {answer} ")
    assert spec.is_correct(f"0{answer}")
    assert not spec.is_correct(str(wrong))


def test_registry_builds_all_modules() -> None:
    rng = random.Random(0)
    for module_id in MODULE_ORDER:
        spec = build_challenge(module_id, 1, rng)
        assert spec.module_id == module_id
        if spec.input_mode == "text":
            assert spec.choices == ()
        else:
            assert spec.correct_id in spec.choice_ids()
