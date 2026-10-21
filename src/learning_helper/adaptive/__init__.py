from __future__ import annotations

__all__ = [
    "AdaptiveEngine",
    "Attempt",
    "ChallengeChoice",
    "ChallengeSpec",
    "Profile",
]


def __getattr__(name: str):
    """Imports tardios para evitar ciclos com `persistence.db`."""
    if name == "AdaptiveEngine":
        from learning_helper.adaptive.engine import AdaptiveEngine

        return AdaptiveEngine
    if name in {"Attempt", "ChallengeChoice", "ChallengeSpec", "Profile"}:
        from learning_helper.adaptive import models

        return getattr(models, name)
    raise AttributeError(name)
