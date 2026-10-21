"""Estado local do atualizador, para não repetir tentativas falhas."""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from learning_helper.updates.manifest import UpdateError, is_newer

MAX_ATTEMPTS = 3
BLOCK_SECONDS = 7 * 24 * 60 * 60


def state_path(base: Path) -> Path:
    return Path(base) / "updates" / "state.json"


@dataclass
class UpdateState:
    pending_version: str | None = None
    pending_path: str | None = None
    attempts: int = 0
    last_attempt: float | None = None
    blocked_version: str | None = None
    blocked_until: float | None = None


def load_state(base: Path) -> UpdateState:
    path = state_path(base)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, ValueError, TypeError):
        return UpdateState()
    if not isinstance(payload, dict):
        return UpdateState()

    def _string(key: str) -> str | None:
        value = payload.get(key)
        return value if isinstance(value, str) else None

    def _number(key: str) -> float | None:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return float(value)

    attempts = payload.get("attempts")
    return UpdateState(
        pending_version=_string("pending_version"),
        pending_path=_string("pending_path"),
        attempts=(
            int(attempts)
            if isinstance(attempts, int) and not isinstance(attempts, bool)
            else 0
        ),
        last_attempt=_number("last_attempt"),
        blocked_version=_string("blocked_version"),
        blocked_until=_number("blocked_until"),
    )


def save_state(base: Path, state: UpdateState) -> None:
    path = state_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f"{path.name}.{os.getpid()}.{threading.get_ident()}.part"
    )
    temporary.write_text(
        json.dumps(asdict(state), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def prune_state(
    base: Path,
    current_version: str,
    *,
    now: float | None = None,
) -> UpdateState:
    """Limpa pendências concluídas ou bloqueios expirados."""
    state = load_state(base)
    instant = time.time() if now is None else now
    changed = False

    def _not_newer(version: str) -> bool:
        try:
            return not is_newer(version, current_version)
        except UpdateError:
            return True

    if state.pending_version is not None and _not_newer(state.pending_version):
        state.pending_version = None
        state.pending_path = None
        state.attempts = 0
        state.last_attempt = None
        changed = True
    if state.blocked_version is not None and (
        _not_newer(state.blocked_version)
        or (state.blocked_until is not None and state.blocked_until <= instant)
    ):
        state.blocked_version = None
        state.blocked_until = None
        changed = True
    if changed:
        save_state(base, state)
    return state


def is_blocked(
    state: UpdateState,
    version: str,
    *,
    now: float | None = None,
) -> bool:
    if state.blocked_version != version:
        return False
    instant = time.time() if now is None else now
    return state.blocked_until is not None and instant < state.blocked_until


def record_pending(state: UpdateState, version: str, path: Path) -> None:
    state.pending_version = version
    state.pending_path = str(path)


def record_attempt(
    state: UpdateState,
    version: str,
    path: Path,
    *,
    now: float | None = None,
) -> None:
    if state.pending_version != version:
        state.attempts = 0
    state.pending_version = version
    state.pending_path = str(path)
    state.attempts += 1
    state.last_attempt = time.time() if now is None else now


def block_version(
    state: UpdateState,
    version: str,
    *,
    now: float | None = None,
) -> None:
    instant = time.time() if now is None else now
    state.blocked_version = version
    state.blocked_until = instant + BLOCK_SECONDS
    state.pending_version = None
    state.pending_path = None
    state.attempts = 0
