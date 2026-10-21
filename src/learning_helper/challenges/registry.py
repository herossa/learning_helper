from __future__ import annotations

import random
from collections.abc import Callable

from learning_helper.adaptive.models import ChallengeSpec
from learning_helper.challenges.colors import build_colors_challenge
from learning_helper.challenges.math import build_math_challenge
from learning_helper.challenges.questions import build_questions_challenge
from learning_helper.challenges.reading import build_reading_challenge

Builder = Callable[[int, random.Random | None], ChallengeSpec]

BUILDERS: dict[str, Builder] = {
    "colors": build_colors_challenge,
    "math": build_math_challenge,
    "questions": build_questions_challenge,
    "reading": build_reading_challenge,
}


def build_challenge(
    module_id: str,
    level: int,
    rng: random.Random | None = None,
) -> ChallengeSpec:
    try:
        builder = BUILDERS[module_id]
    except KeyError as exc:
        raise ValueError(f"Módulo desconhecido: {module_id}") from exc
    return builder(level, rng)
