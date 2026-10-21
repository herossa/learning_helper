from __future__ import annotations

from dataclasses import dataclass

MODULE_ORDER = ("colors", "math", "questions", "reading")
DEFAULT_UNLOCKED = ("colors",)
MAX_LEVEL = 5
ACCURACY_WINDOW = 10
UNLOCK_THRESHOLD = 0.8
LEVEL_UP_THRESHOLD = 0.8
LEVEL_DOWN_THRESHOLD = 0.4

INTERVAL_SECONDS = 15 * 60
MIN_PAUSE_AFTER_ANSWER_SECONDS = 60
ADULT_PAUSE_SECONDS = 30 * 60
DEBUG_INTERVAL_SECONDS = 10
FEEDBACK_MS = 1000

ADULT_SHORTCUT = "<Control-Alt-Shift-p>"
ADULT_SHORTCUT_LABEL = "Control+Alt+Shift+P"


@dataclass(frozen=True)
class RuntimeConfig:
    debug: bool = False
    interval_seconds: int = INTERVAL_SECONDS
    adult_pause_seconds: int = ADULT_PAUSE_SECONDS

    @property
    def interval_ms(self) -> int:
        if self.debug:
            return DEBUG_INTERVAL_SECONDS * 1000
        return self.interval_seconds * 1000
