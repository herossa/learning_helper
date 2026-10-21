from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path


def _banks_dir() -> Path:
    return Path(__file__).parent / "banks"


@lru_cache(maxsize=None)
def load_bank(name: str) -> list[dict]:
    path = _banks_dir() / f"{name}.json"
    return json.loads(path.read_text(encoding="utf-8"))
