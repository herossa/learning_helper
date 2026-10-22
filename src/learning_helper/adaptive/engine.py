from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from learning_helper.adaptive.models import Attempt, ChallengeSpec, Profile
from learning_helper.config import MODULE_ORDER
from learning_helper.persistence.db import Store
from learning_helper.settings import Settings


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

    def settings(self) -> Settings:
        return self.store.get_settings()

    def pick_module(self) -> str:
        profile = self.profile()
        settings = self.settings()
        enabled = set(settings.enabled_modules)
        unlocked = [
            module
            for module in MODULE_ORDER
            if module in profile.unlocked_modules and module in enabled
        ]
        if not unlocked:
            # Nenhum módulo ativo desbloqueado: libera o primeiro ativo para
            # não deixar a criança sem desafio.
            fallback = next(
                (module for module in MODULE_ORDER if module in enabled),
                MODULE_ORDER[0],
            )
            if fallback not in profile.unlocked_modules:
                profile.unlocked_modules.append(fallback)
                profile.unlocked_modules = [
                    module
                    for module in MODULE_ORDER
                    if module in profile.unlocked_modules
                ]
                self.store.save_profile(profile)
            unlocked = [fallback]

        weights: list[float] = []
        for index, module in enumerate(unlocked):
            recency_bonus = index + 1
            recent = self.store.recent_attempts(module, settings.accuracy_window)
            acc = accuracy_of(recent)
            weakness = 1.0 - acc if acc is not None else 0.5
            weights.append(recency_bonus * (0.5 + weakness))
        return self.rng.choices(unlocked, weights=weights, k=1)[0]

    def current_level(self, module_id: str) -> int:
        return int(self.profile().levels.get(module_id, 1))

    def next_interval_seconds(self) -> int:
        """Intervalo até o próximo desafio, ajustado pelas respostas."""
        settings = self.settings()
        current = self.profile().interval_seconds
        return max(
            settings.min_interval_seconds,
            min(settings.max_interval_seconds, current),
        )

    def record_attempt(self, spec: ChallengeSpec, given_answer: str) -> Attempt:
        is_correct = spec.is_correct(given_answer)
        spec_json = {
            "prompt": spec.prompt,
            "choices": [
                {"id": choice.id, "label": choice.label, "rgb": choice.rgb}
                for choice in spec.choices
            ],
            "correct_id": spec.correct_id,
            "metadata": spec.metadata,
        }
        if spec.correct_ids is not None:
            spec_json["correct_ids"] = list(spec.correct_ids)
        if spec.correct_summary is not None:
            spec_json["correct_summary"] = spec.correct_summary
        attempt = self.store.insert_attempt(
            module_id=spec.module_id,
            level=spec.level,
            prompt=spec.prompt,
            choices=spec.choice_ids(),
            correct_answer=spec.answer_text,
            given_answer=given_answer.strip(),
            is_correct=is_correct,
            spec_json=spec_json,
        )
        profile = self.profile()
        settings = self.settings()
        self._adapt(profile, settings)
        self._adjust_interval(profile, is_correct, settings)
        profile.last_interrupt_at = datetime.now(timezone.utc)
        self.store.save_profile(profile)
        return attempt

    def pause_for_adult(self, seconds: int | None = None) -> None:
        duration = self.settings().adult_pause_seconds if seconds is None else seconds
        profile = self.profile()
        profile.adult_pause_until = datetime.now(timezone.utc) + timedelta(
            seconds=duration
        )
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

    def _adjust_interval(
        self, profile: Profile, is_correct: bool, settings: Settings
    ) -> None:
        """Acerto espaça o próximo desafio; erro aproxima."""
        step = settings.interval_step_seconds if is_correct else -settings.interval_step_seconds
        profile.interval_seconds = max(
            settings.min_interval_seconds,
            min(settings.max_interval_seconds, profile.interval_seconds + step),
        )

    def _adapt(self, profile: Profile, settings: Settings) -> None:
        enabled = set(settings.enabled_modules)
        for module in list(profile.unlocked_modules):
            if module not in enabled or module not in MODULE_ORDER:
                continue
            count = self.store.count_attempts(module)
            if (
                count < settings.accuracy_window
                or count % settings.accuracy_window != 0
            ):
                continue
            recent = self.store.recent_attempts(module, settings.accuracy_window)
            acc = accuracy_of(recent)
            if acc is None:
                continue
            current = profile.levels.get(module, 1)
            if acc >= settings.level_up_threshold:
                if current < settings.max_level:
                    profile.levels[module] = current + 1
            elif acc <= settings.level_down_threshold:
                profile.levels[module] = max(1, current - 1)

        unlocked = [
            module
            for module in MODULE_ORDER
            if module in profile.unlocked_modules and module in enabled
        ]
        if not unlocked:
            return
        last = unlocked[-1]
        last_index = MODULE_ORDER.index(last)
        next_module = next(
            (
                module
                for module in MODULE_ORDER[last_index + 1 :]
                if module in enabled
            ),
            None,
        )
        if next_module is None:
            return
        count = self.store.count_attempts(last)
        if count < settings.accuracy_window:
            return
        acc = accuracy_of(
            self.store.recent_attempts(last, settings.accuracy_window)
        )
        if (
            acc is not None
            and acc >= settings.unlock_threshold
            and next_module not in profile.unlocked_modules
        ):
            profile.unlocked_modules.append(next_module)
            profile.unlocked_modules = [
                module
                for module in MODULE_ORDER
                if module in profile.unlocked_modules
            ]
