from __future__ import annotations

from dataclasses import dataclass

MODULE_ORDER = ("colors", "math", "problems", "questions", "reading")
DEFAULT_UNLOCKED = ("colors",)
MAX_LEVEL = 5
ACCURACY_WINDOW = 10
UNLOCK_THRESHOLD = 0.8
LEVEL_UP_THRESHOLD = 0.8
LEVEL_DOWN_THRESHOLD = 0.4

MIN_INTERVAL_SECONDS = 60
MAX_INTERVAL_SECONDS = 5 * 60
INITIAL_INTERVAL_SECONDS = 3 * 60
INTERVAL_STEP_SECONDS = 30
MIN_PAUSE_AFTER_ANSWER_SECONDS = 60
ADULT_PAUSE_SECONDS = 30 * 60
DEBUG_INTERVAL_SECONDS = 10
FEEDBACK_MS = 1000

ADULT_SHORTCUT = "<Control-Alt-Shift-p>"
ADULT_SHORTCUT_LABEL = "Control+Alt+Shift+P"


@dataclass(frozen=True)
class RuntimeConfig:
    debug: bool = False
    adult_pause_seconds: int = ADULT_PAUSE_SECONDS

    def delay_ms(self, adaptive_seconds: int) -> int:
        if self.debug:
            return DEBUG_INTERVAL_SECONDS * 1000
        bounded = max(MIN_INTERVAL_SECONDS, min(MAX_INTERVAL_SECONDS, adaptive_seconds))
        return bounded * 1000
