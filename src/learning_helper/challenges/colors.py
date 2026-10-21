from __future__ import annotations

import random

from learning_helper.adaptive.models import ChallengeChoice, ChallengeSpec
from learning_helper.config import MAX_LEVEL

PRIMARY_COLOR_DATA = {
    "yellow": {"name": "Amarelo", "rgb_code": (255, 255, 0)},
    "blue": {"name": "Azul", "rgb_code": (0, 0, 255)},
    "green": {"name": "Verde", "rgb_code": (0, 255, 0)},
    "red": {"name": "Vermelho", "rgb_code": (255, 0, 0)},
    "brown": {"name": "Marron", "rgb_code": (150, 75, 0)},
    "black": {"name": "Preto", "rgb_code": (0, 0, 0)},
    "gray": {"name": "Cinza", "rgb_code": (128, 128, 128)},
    "orange": {"name": "Laranja", "rgb_code": (255, 165, 0)},
    "pink": {"name": "Rosa", "rgb_code": (255, 105, 180)},
    "purple": {"name": "Roxo", "rgb_code": (148, 0, 211)},
    "white": {"name": "Branco", "rgb_code": (255, 255, 255)},
}

SIMILAR_GROUPS = (
    ("red", "orange", "pink", "brown"),
    ("blue", "purple", "gray"),
    ("yellow", "orange", "green"),
    ("black", "gray", "brown"),
    ("green", "blue", "yellow"),
)


def _choice_count(level: int) -> int:
    clamped = max(1, min(level, MAX_LEVEL))
    return min(3 + clamped - 1, len(PRIMARY_COLOR_DATA))


def build_colors_challenge(level: int, rng: random.Random | None = None) -> ChallengeSpec:
    rng = rng or random.Random()
    n = _choice_count(level)
    keys = list(PRIMARY_COLOR_DATA)

    if level >= 4:
        group = rng.choice(SIMILAR_GROUPS)
        pool = list(dict.fromkeys(list(group) + keys))
        selected = rng.sample(pool, k=min(n, len(pool)))
        if len(selected) < n:
            extra = [key for key in keys if key not in selected]
            selected.extend(rng.sample(extra, k=n - len(selected)))
    else:
        selected = rng.sample(keys, k=n)

    correct = rng.choice(selected)
    choices = tuple(
        ChallengeChoice(
            id=key,
            label=PRIMARY_COLOR_DATA[key]["name"],
            rgb=tuple(PRIMARY_COLOR_DATA[key]["rgb_code"]),
        )
        for key in selected
    )
    name = PRIMARY_COLOR_DATA[correct]["name"]
    return ChallengeSpec(
        module_id="colors",
        level=level,
        prompt=f"Qual é o quadrado {name}?",
        choices=choices,
        correct_id=correct,
        metadata={"kind": "color_square"},
    )
