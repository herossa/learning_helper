from __future__ import annotations

import random

from learning_helper.adaptive.models import ChallengeSpec
from learning_helper.config import MAX_LEVEL

# Faixas crescentes: no nível 1 basta comparar unidades; no nível 5, centenas.
RANGES = {
    1: (1, 9),
    2: (1, 20),
    3: (10, 50),
    4: (10, 99),
    5: (100, 999),
}


def build_comparison_challenge(
    level: int, rng: random.Random | None = None
) -> ChallengeSpec:
    """Sorteia dois números e pede o maior ou o menor deles."""
    rng = rng or random.Random()
    clamped = max(1, min(level, MAX_LEVEL))
    low, high = RANGES[clamped]
    a, b = rng.sample(range(low, high + 1), 2)
    comparison = rng.choice(("maior", "menor"))
    correct = max(a, b) if comparison == "maior" else min(a, b)
    prompt = (
        f"Qual dos dois números a seguir é {comparison}?\n\n"
        f"{a}  ou  {b}"
    )
    return ChallengeSpec(
        module_id="compare",
        level=clamped,
        prompt=prompt,
        choices=(),
        correct_id=str(correct),
        input_mode="text",
        metadata={
            "a": a,
            "b": b,
            "comparison": comparison,
            "answer": correct,
        },
    )
