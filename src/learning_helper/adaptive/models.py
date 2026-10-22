from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from learning_helper.config import DEFAULT_UNLOCKED, INITIAL_INTERVAL_SECONDS, MODULE_ORDER


@dataclass(frozen=True)
class ChallengeChoice:
    id: str
    label: str
    rgb: tuple[int, int, int] | None = None


@dataclass(frozen=True)
class ChallengeSpec:
    module_id: str
    level: int
    prompt: str
    choices: tuple[ChallengeChoice, ...]
    correct_id: str
    metadata: dict = field(default_factory=dict)
    # "choice" usa os botões de alternativa; "text" usa campo + botão OK.
    input_mode: str = "choice"

    def choice_ids(self) -> list[str]:
        return [choice.id for choice in self.choices]

    def normalize_answer(self, answer: str) -> str:
        value = answer.strip()
        if self.input_mode == "text":
            try:
                return str(int(value))
            except ValueError:
                return value.casefold()
        return value

    def is_correct(self, answer: str) -> bool:
        return self.normalize_answer(answer) == self.normalize_answer(self.correct_id)


@dataclass(frozen=True)
class Attempt:
    id: int | None
    created_at: datetime
    module_id: str
    level: int
    prompt: str
    choices: list[str]
    correct_answer: str
    given_answer: str
    is_correct: bool
    spec_json: dict | None = None


@dataclass
class Profile:
    unlocked_modules: list[str]
    levels: dict[str, int]
    last_interrupt_at: datetime | None = None
    adult_pause_until: datetime | None = None
    interval_seconds: int = INITIAL_INTERVAL_SECONDS
    last_bathroom_reminder_at: datetime | None = None

    @classmethod
    def default(cls) -> Profile:
        return cls(
            unlocked_modules=list(DEFAULT_UNLOCKED),
            levels={module: 1 for module in MODULE_ORDER},
        )
