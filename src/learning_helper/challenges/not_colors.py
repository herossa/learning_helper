from __future__ import annotations

import random

from learning_helper.adaptive.models import ChallengeChoice, ChallengeSpec
from learning_helper.challenges.colors import PRIMARY_COLOR_DATA, SIMILAR_GROUPS
from learning_helper.config import MAX_LEVEL

# Menos opções nos níveis altos: com apenas uma cor errada, o desafio fica
# mais difícil quando há poucas alternativas e elas são parecidas.
CHOICE_COUNTS = {
    1: 5,
    2: 4,
    3: 4,
    4: 3,
    5: 3,
}


def _distractors(
    target: str,
    count: int,
    level: int,
    keys: list[str],
    rng: random.Random,
) -> list[str]:
    chosen: list[str] = []
    if level >= 4:
        for group in SIMILAR_GROUPS:
            if target in group:
                similar = [key for key in group if key != target]
                if len(similar) >= count:
                    return rng.sample(similar, k=count)
                chosen = similar
                break

    rest = [key for key in keys if key != target and key not in chosen]
    chosen.extend(rng.sample(rest, k=count - len(chosen)))
    return chosen


def build_not_colors_challenge(
    level: int, rng: random.Random | None = None
) -> ChallengeSpec:
    """Mostra cores e pede uma que não seja a cor citada no enunciado."""
    rng = rng or random.Random()
    clamped = max(1, min(level, MAX_LEVEL))
    count = CHOICE_COUNTS[clamped]
    keys = list(PRIMARY_COLOR_DATA)
    target = rng.choice(keys)

    selected = [
        target,
        *_distractors(target, count - 1, clamped, keys, rng),
    ]
    rng.shuffle(selected)

    name = PRIMARY_COLOR_DATA[target]["name"]
    correct_ids = tuple(key for key in selected if key != target)
    choices = tuple(
        ChallengeChoice(
            id=key,
            label=PRIMARY_COLOR_DATA[key]["name"],
            rgb=tuple(PRIMARY_COLOR_DATA[key]["rgb_code"]),
        )
        for key in selected
    )
    return ChallengeSpec(
        module_id="not_colors",
        level=clamped,
        prompt=f"Clique na cor que não é o {name.lower()}.",
        choices=choices,
        correct_id=correct_ids[0],
        correct_ids=correct_ids,
        correct_summary=f"qualquer cor diferente de {name}",
        metadata={
            "kind": "color_exception",
            "target": target,
            "target_name": name,
        },
    )
