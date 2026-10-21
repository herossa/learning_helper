"""Verificação em background e aplicação da atualização."""

from __future__ import annotations

import logging
import shutil
import threading
from pathlib import Path

from learning_helper.updates.client import download_asset, fetch_manifest
from learning_helper.updates.install import (
    PendingUpdate,
    apply_pending,
    asset_key,
    select_asset,
)
from learning_helper.updates.manifest import Release, UpdateError, is_newer
from learning_helper.updates.state import (
    MAX_ATTEMPTS,
    block_version,
    is_blocked,
    load_state,
    prune_state,
    record_attempt,
    record_pending,
    save_state,
)

LOGGER = logging.getLogger(__name__)
MANUAL_REQUEST_NAME = "manual.request"


def manual_request_path(base: Path) -> Path:
    return Path(base) / "updates" / MANUAL_REQUEST_NAME


def request_manual_update(base: Path, version: str) -> None:
    """Marca que o download manual está pronto para o overlay aplicar."""
    path = manual_request_path(base)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(version, encoding="utf-8")


def clear_manual_request(base: Path) -> None:
    try:
        manual_request_path(base).unlink()
    except OSError:
        pass


def _download_path(base: Path, release: Release, name: str) -> Path:
    safe_name = Path(name).name
    return Path(base) / "updates" / release.version / safe_name


def _cleanup_old_downloads(base: Path, keep_version: str) -> None:
    updates_dir = Path(base) / "updates"
    if not updates_dir.is_dir():
        return
    for child in updates_dir.iterdir():
        if not child.is_dir():
            continue
        if child.name == keep_version:
            continue
        if child.name.startswith("extract-"):
            shutil.rmtree(child, ignore_errors=True)
        elif child.name[0].isdigit():
            shutil.rmtree(child, ignore_errors=True)


def prepare_update(
    release: Release,
    current_version: str,
    base: Path,
    *,
    force: bool = False,
) -> PendingUpdate | None:
    """Baixa o asset adequado e devolve a atualização pronta para aplicar."""
    state = prune_state(base, current_version)
    if not is_newer(release.version, current_version):
        return None
    if not force and is_blocked(state, release.version):
        return None
    if (
        not force
        and state.pending_version == release.version
        and state.attempts >= MAX_ATTEMPTS
    ):
        block_version(state, release.version)
        save_state(base, state)
        LOGGER.warning(
            "Atualização %s bloqueada após %s tentativas.",
            release.version,
            MAX_ATTEMPTS,
        )
        return None

    selection = select_asset(release)
    if selection is None:
        return None
    key, asset = selection

    if force:
        state.attempts = 0
        state.blocked_version = None
        state.blocked_until = None

    destination = _download_path(base, release, asset.name)
    path = download_asset(asset, destination)
    record_pending(state, release.version, path)
    save_state(base, state)
    _cleanup_old_downloads(base, release.version)
    return PendingUpdate(version=release.version, asset_key=key, path=path)


def check_and_download(
    current_version: str,
    base: Path,
    *,
    manifest_url: str | None = None,
    force: bool = False,
) -> PendingUpdate | None:
    release = fetch_manifest(manifest_url)
    return prepare_update(
        release,
        current_version,
        base,
        force=force,
    )


class UpdateService:
    """Consulta o manifesto uma vez e deixa o update pronto para aplicar."""

    def __init__(
        self,
        current_version: str,
        base: Path,
        *,
        manifest_url: str | None = None,
    ) -> None:
        self.current_version = current_version
        self.base = Path(base)
        self.manifest_url = manifest_url
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._pending: PendingUpdate | None = None
        self._error: str | None = None
        self._started = False

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
        self._thread = threading.Thread(
            target=self._worker,
            name="learning-helper-update",
            daemon=True,
        )
        self._thread.start()

    def _worker(self) -> None:
        try:
            pending = check_and_download(
                self.current_version,
                self.base,
                manifest_url=self.manifest_url,
            )
        except Exception as exc:
            LOGGER.warning("Não foi possível verificar atualizações: %s", exc)
            with self._lock:
                self._error = str(exc)
            return
        with self._lock:
            self._pending = pending

    def wait(self, timeout: float | None = None) -> None:
        thread = self._thread
        if thread is not None:
            thread.join(timeout)

    @property
    def pending(self) -> PendingUpdate | None:
        with self._lock:
            return self._pending

    @property
    def error(self) -> str | None:
        with self._lock:
            return self._error

    def accept_manual_request(self) -> PendingUpdate | None:
        """Carrega um download feito pelas Configurações, se ainda for válido."""
        with self._lock:
            if self._pending is not None:
                return self._pending

        marker = manual_request_path(self.base)
        try:
            version = marker.read_text(encoding="utf-8").strip()
        except (FileNotFoundError, OSError):
            return None

        state = prune_state(self.base, self.current_version)
        try:
            newer = bool(version) and is_newer(version, self.current_version)
        except UpdateError:
            newer = False
        valid = (
            newer
            and state.pending_version == version
            and state.pending_path is not None
            and state.attempts < MAX_ATTEMPTS
            and not is_blocked(state, version)
        )
        if not valid:
            clear_manual_request(self.base)
            return None
        key = asset_key()
        path = Path(state.pending_path)
        if key is None or not path.is_file():
            clear_manual_request(self.base)
            return None

        pending = PendingUpdate(version=version, asset_key=key, path=path)
        with self._lock:
            if self._pending is None:
                self._pending = pending
            return self._pending

    def apply(self) -> bool:
        with self._lock:
            pending = self._pending
        if pending is None:
            return False

        state = load_state(self.base)
        record_attempt(state, pending.version, pending.path)
        save_state(self.base, state)
        try:
            apply_pending(pending, self.base)
        except Exception as exc:
            clear_manual_request(self.base)
            with self._lock:
                self._pending = None
                self._error = str(exc)
            raise UpdateError(str(exc)) from exc
        clear_manual_request(self.base)
        with self._lock:
            self._pending = None
        return True
