import os
import random

import pytest

if os.environ.get("RUN_GUI_TESTS") != "1":
    pytest.skip(
        "defina RUN_GUI_TESTS=1 para testar a interface (precisa de desktop)",
        allow_module_level=True,
    )

tkinter = pytest.importorskip("tkinter")
pytest.importorskip("customtkinter")

from learning_helper.adaptive.engine import AdaptiveEngine
from learning_helper.config import RuntimeConfig
from learning_helper.overlay.main_window import OverlayApp
from learning_helper.persistence.db import Store


def test_overlay_builds_and_destroys(tmp_path) -> None:
    store = Store(tmp_path / "learning_helper.db")
    engine = AdaptiveEngine(store, rng=random.Random(0))
    try:
        try:
            app = OverlayApp(engine, RuntimeConfig(debug=True))
        except tkinter.TclError:
            pytest.skip("sem display disponível")
        app.update()
        assert app.winfo_exists()
        app.destroy()
    finally:
        store.close()
