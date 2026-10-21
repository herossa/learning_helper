from __future__ import annotations

__all__ = ["ChallengePanel", "OverlayApp"]


def __getattr__(name: str):
    """Imports tardios: importar `overlay.geometry` não carrega Tk."""
    if name == "ChallengePanel":
        from learning_helper.overlay.host import ChallengePanel

        return ChallengePanel
    if name == "OverlayApp":
        from learning_helper.overlay.main_window import OverlayApp

        return OverlayApp
    raise AttributeError(name)
