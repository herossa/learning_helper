from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from learning_helper.adaptive.models import Attempt, ChallengeSpec, Profile
from learning_helper.config import (
    ACCURACY_WINDOW,
    ADULT_PAUSE_SECONDS,
    INTERVAL_STEP_SECONDS,
    LEVEL_DOWN_THRESHOLD,
    LEVEL_UP_THRESHOLD,
    MAX_INTERVAL_SECONDS,
    MAX_LEVEL,
    MIN_INTERVAL_SECONDS,
    MODULE_ORDER,
    UNLOCK_THRESHOLD,
)
from learning_helper.persistence.db import Store


def accuracy_of(attempts: list[Attempt]) -> float | None:
    if not attempts:
        return None
    return sum(1 for attempt in attempts if attempt.is_correct) / len(attempts)


class AdaptiveEngine:
    def __init__(self, store: Store, rng: random.Random | None = None) -> None:
        self.store = store
        self.rng = rng or random.Random()

    def profile(self) -> Profile:
        return self.store.get_profile()

    def pick_module(self) -> str:
        profile = self.profile()
        unlocked = [module for module in MODULE_ORDER if module in profile.unlocked_modules]
        if not unlocked:
            return MODULE_ORDER[0]

        weights: list[float] = []
        for index, module in enumerate(unlocked):
            recency_bonus = index + 1
            recent = self.store.recent_attempts(module, ACCURACY_WINDOW)
            acc = accuracy_of(recent)
            weakness = 1.0 - acc if acc is not None else 0.5
            weights.append(recency_bonus * (0.5 + weakness))
        return self.rng.choices(unlocked, weights=weights, k=1)[0]

    def current_level(self, module_id: str) -> int:
        return int(self.profile().levels.get(module_id, 1))

    def next_interval_seconds(self) -> int:
        """Intervalo até o próximo desafio, ajustado pelas respostas."""
        current = self.profile().interval_seconds
        return max(MIN_INTERVAL_SECONDS, min(MAX_INTERVAL_SECONDS, current))

    def record_attempt(self, spec: ChallengeSpec, given_answer: str) -> Attempt:
        is_correct = given_answer == spec.correct_id
        attempt = self.store.insert_attempt(
            module_id=spec.module_id,
            level=spec.level,
            prompt=spec.prompt,
            choices=spec.choice_ids(),
            correct_answer=spec.correct_id,
            given_answer=given_answer,
            is_correct=is_correct,
            spec_json={
                "prompt": spec.prompt,
                "choices": [
                    {"id": choice.id, "label": choice.label, "rgb": choice.rgb}
                    for choice in spec.choices
                ],
                "correct_id": spec.correct_id,
                "metadata": spec.metadata,
            },
        )
        profile = self.profile()
        self._adapt(profile)
        self._adjust_interval(profile, is_correct)
        profile.last_interrupt_at = datetime.now(timezone.utc)
        self.store.save_profile(profile)
        return attempt

    def pause_for_adult(self, seconds: int = ADULT_PAUSE_SECONDS) -> None:
        profile = self.profile()
        profile.adult_pause_until = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        self.store.save_profile(profile)

    def record_bathroom_reminder(self, now: datetime | None = None) -> None:
        """Marca que o lembrete de banheiro apareceu agora."""
        profile = self.profile()
        profile.last_bathroom_reminder_at = now or datetime.now(timezone.utc)
        self.store.save_profile(profile)

    def is_paused(self, now: datetime | None = None) -> bool:
        profile = self.profile()
        if profile.adult_pause_until is None:
            return False
        moment = now or datetime.now(timezone.utc)
        return moment < profile.adult_pause_until

    def _adjust_interval(self, profile: Profile, is_correct: bool) -> None:
        """Acerto espaça o próximo desafio; erro aproxima."""
        step = INTERVAL_STEP_SECONDS if is_correct else -INTERVAL_STEP_SECONDS
        profile.interval_seconds = max(
            MIN_INTERVAL_SECONDS,
            min(MAX_INTERVAL_SECONDS, profile.interval_seconds + step),
        )

    def _adapt(self, profile: Profile) -> None:
        for module in list(profile.unlocked_modules):
            count = self.store.count_attempts(module)
            if count < ACCURACY_WINDOW or count % ACCURACY_WINDOW != 0:
                continue
            recent = self.store.recent_attempts(module, ACCURACY_WINDOW)
            acc = accuracy_of(recent)
            if acc is None:
                continue
            current = profile.levels.get(module, 1)
            if acc >= LEVEL_UP_THRESHOLD:
                profile.levels[module] = min(MAX_LEVEL, current + 1)
            elif acc <= LEVEL_DOWN_THRESHOLD:
                profile.levels[module] = max(1, current - 1)

        unlocked = [module for module in MODULE_ORDER if module in profile.unlocked_modules]
        last = unlocked[-1]
        last_index = MODULE_ORDER.index(last)
        if last_index + 1 < len(MODULE_ORDER):
            count = self.store.count_attempts(last)
            if count >= ACCURACY_WINDOW:
                acc = accuracy_of(self.store.recent_attempts(last, ACCURACY_WINDOW))
                nxt = MODULE_ORDER[last_index + 1]
                if acc is not None and acc >= UNLOCK_THRESHOLD and nxt not in profile.unlocked_modules:
                    profile.unlocked_modules.append(nxt)
