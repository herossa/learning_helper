from __future__ import annotations

import random

from learning_helper.adaptive.models import ChallengeChoice, ChallengeSpec

OPS = {
    1: ("+", 1, 10),
    2: ("+", 1, 20),
    3: ("-", 1, 20),
    4: ("mix", 1, 40),
    5: ("*", 1, 10),
}


def _pick_op(level: int, rng: random.Random) -> str:
    op, _, _ = OPS.get(level, OPS[5])
    if op == "mix":
        return rng.choice(["+", "-"])
    return op


def _operands(op: str, low: int, high: int, rng: random.Random) -> tuple[int, int, int]:
    if op == "-":
        a = rng.randint(low, high)
        b = rng.randint(low, a)
        return a, b, a - b
    a = rng.randint(low, high)
    b = rng.randint(low, high)
    if op == "*":
        return a, b, a * b
    return a, b, a + b


def _distractors(correct: int, rng: random.Random) -> list[int]:
    values = {correct}
    while len(values) < 4:
        delta = rng.choice([-10, -5, -2, -1, 1, 2, 5, 10])
        candidate = correct + delta
        if candidate >= 0 and candidate != correct:
            values.add(candidate)
    values.remove(correct)
    return list(values)


def build_math_challenge(level: int, rng: random.Random | None = None) -> ChallengeSpec:
    rng = rng or random.Random()
    clamped = max(1, min(level, 5))
    _, low, high = OPS[clamped]
    op = _pick_op(clamped, rng)
    a, b, result = _operands(op, low, high, rng)
    prompt = f"Quanto é {a} {op} {b}?"
    wrong = _distractors(result, rng)
    option_values = [result, *wrong]
    rng.shuffle(option_values)
    choices = tuple(
        ChallengeChoice(id=str(value), label=str(value)) for value in option_values
    )
    return ChallengeSpec(
        module_id="math",
        level=clamped,
        prompt=prompt,
        choices=choices,
        correct_id=str(result),
        metadata={"a": a, "b": b, "op": op, "result": result},
    )
