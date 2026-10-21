from pathlib import Path

import pytest

from learning_helper.adaptive.engine import AdaptiveEngine
from learning_helper.persistence.db import Store


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path / "learning_helper.db")


@pytest.fixture
def engine(store: Store) -> AdaptiveEngine:
    return AdaptiveEngine(store)
