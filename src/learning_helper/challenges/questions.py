from __future__ import annotations

import random

from learning_helper.adaptive.models import ChallengeChoice, ChallengeSpec
from learning_helper.challenges.banks import load_bank


def build_questions_challenge(level: int, rng: random.Random | None = None) -> ChallengeSpec:
    rng = rng or random.Random()
    bank = load_bank("questions")
    max_difficulty = min(max(level, 1), 5)
    pool = [item for item in bank if int(item["difficulty"]) <= max_difficulty]
    if not pool:
        pool = bank
    item = rng.choice(pool)
    options = list(item["options"])
    rng.shuffle(options)
    choices = tuple(ChallengeChoice(id=option, label=option) for option in options)
    return ChallengeSpec(
        module_id="questions",
        level=max_difficulty,
        prompt=item["prompt"],
        choices=choices,
        correct_id=item["answer"],
        metadata={"id": item["id"], "topic": item.get("topic")},
    )
