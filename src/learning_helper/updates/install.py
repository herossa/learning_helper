"""Download, seleção e aplicação dos pacotes de atualização."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import tarfile
from dataclasses import dataclass
from pathlib import Path

from learning_helper.updates.manifest import Asset, Release, UpdateError

WINDOWS_SETUP = "windows_setup"
LINUX_APPIMAGE = "linux_appimage"
LINUX_TARBALL = "linux_tarball"


@dataclass(frozen=True)
class PendingUpdate:
    version: str
    asset_key: str
    path: Path


def asset_key() -> str | None:
    """Formato de pacote adequado a esta execução, ou None fora de build."""
    if not getattr(sys, "frozen", False):
        return None
    if sys.platform == "win32":
        return WINDOWS_SETUP
    if sys.platform.startswith("linux"):
        if os.environ.get("APPIMAGE"):
            return LINUX_APPIMAGE
        return LINUX_TARBALL
    return None


def select_asset(release: Release) -> tuple[str, Asset] | None:
    key = asset_key()
    if key is None:
        return None
    asset = release.assets.get(key)
    if asset is None:
        return None
    return key, asset


def linux_prefix() -> Path | None:
    """Prefixo de instalação por usuário a partir do executável congelado."""
    executable = Path(sys.executable).resolve()
    if executable.parent.name != "learning-helper":
        return None
    if executable.parent.parent.name != "opt":
        return None
    return executable.parent.parent.parent


def _log_file(base: Path) -> Path:
    path = Path(base) / "updates" / "apply.log"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _write_script(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _spawn_detached(command: list[str], *, log_path: Path) -> None:
    with log_path.open("a", encoding="utf-8") as log:
        subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            close_fds=True,
            start_new_session=True,
        )


def _windows_all_users() -> bool:
    """Detecta instalação em Program Files (feita com elevação)."""
    executable = os.path.normcase(str(Path(sys.executable).resolve()))
    for variable in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(variable)
        if not root:
            continue
        normalized = os.path.normcase(str(Path(root).resolve()))
        if executable == normalized or executable.startswith(normalized + os.sep):
            return True
    return False


def _apply_windows(pending: PendingUpdate, base: Path) -> None:
    log_path = _log_file(base)
    flags = 0
    flags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    scope = "/ALLUSERS" if _windows_all_users() else "/CURRENTUSER"
    install_dir = Path(sys.executable).resolve().parent
    subprocess.Popen(
        [
            str(pending.path),
            "/VERYSILENT",
            "/SUPPRESSMSGBOXES",
            "/NORESTART",
            "/CLOSEAPPLICATIONS",
            "/UPDATERESTART=1",
            scope,
            f'/DIR="{install_dir}"',
            f'/LOG="{log_path}"',
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=flags,
    )


def _safe_extract(archive: Path, destination: Path) -> None:
    destination = destination.resolve()
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        for member in members:
            target = (destination / member.name).resolve()
            if not target.is_relative_to(destination):
                raise UpdateError("Pacote de atualização com caminho inválido.")
            if member.isdev() or member.isfifo():
                raise UpdateError("Pacote de atualização com arquivo especial.")
            if member.issym():
                link = (target.parent / member.linkname).resolve()
                if not link.is_relative_to(destination):
                    raise UpdateError("Pacote de atualização com link inválido.")
            elif member.islnk():
                link = (destination / member.linkname).resolve()
                if not link.is_relative_to(destination):
                    raise UpdateError("Pacote de atualização com link inválido.")
        if hasattr(tarfile, "data_filter"):
            tar.extractall(destination, members=members, filter="data")
        else:
            _extract_without_links_first(tar, destination, members)


def _extract_without_links_first(
    tar: tarfile.TarFile,
    destination: Path,
    members: list[tarfile.TarInfo],
) -> None:
    """Fallback para Python 3.11 anterior ao filtro de segurança do tarfile."""
    order = {tarfile.DIRTYPE: 0, tarfile.REGTYPE: 1, tarfile.AREGTYPE: 1}
    ordered = sorted(
        members,
        key=lambda member: (
            order.get(member.type, 3 if member.islnk() else 4),
            member.name,
        ),
    )
    for member in ordered:
        tar.extract(member, destination)


def _package_dir(extract_dir: Path) -> Path:
    for candidate in sorted(extract_dir.iterdir()):
        if candidate.is_dir() and candidate.name.startswith("LearningHelper-"):
            return candidate
    raise UpdateError("Pacote de atualização sem diretório LearningHelper.")


def _apply_tarball(pending: PendingUpdate, base: Path) -> None:
    prefix = linux_prefix()
    if prefix is None:
        raise UpdateError(
            "Instalação Linux não está no layout esperado para atualização."
        )
    extract_dir = Path(base) / "updates" / f"extract-{pending.version}"
    shutil.rmtree(extract_dir, ignore_errors=True)
    extract_dir.mkdir(parents=True, exist_ok=True)
    _safe_extract(pending.path, extract_dir)
    package = _package_dir(extract_dir)
    installer = package / "install-user.sh"
    if not installer.is_file():
        raise UpdateError("Pacote de atualização sem install-user.sh.")

    log_path = _log_file(base)
    script = Path(base) / "updates" / "apply-update.sh"
    _write_script(
        script,
        "\n".join(
            [
                "#!/bin/sh",
                "set -eu",
                f"LOG={shlex.quote(str(log_path))}",
                'exec >>"$LOG" 2>&1',
                f'echo "[$(date -Is)] Aplicando atualização {pending.version}."',
                "i=0",
                (
                    f"while kill -0 {os.getpid()} 2>/dev/null "
                    '&& [ "$i" -lt 100 ]; do sleep 0.3; i=$((i + 1)); done'
                ),
                (
                    f"if {shlex.quote(str(installer))} "
                    f"--prefix {shlex.quote(str(prefix))}; then"
                ),
                '    echo "[$(date -Is)] Instalação concluída; reabrindo."',
                "else",
                '    echo "[$(date -Is)] Falha na instalação; reabrindo a versão atual."',
                "fi",
                (
                    f"nohup {shlex.quote(str(prefix / 'bin' / 'learning-helper'))} "
                    '>>"$LOG" 2>&1 &'
                ),
                "",
            ]
        ),
    )
    _spawn_detached(["/bin/sh", str(script)], log_path=log_path)


def _apply_appimage(pending: PendingUpdate, base: Path) -> None:
    raw = os.environ.get("APPIMAGE")
    if not raw:
        raise UpdateError("Caminho do AppImage não encontrado.")
    appimage = Path(raw).resolve()
    if not appimage.is_file():
        raise UpdateError("AppImage em execução não encontrado.")
    if not os.access(appimage, os.W_OK) or not os.access(appimage.parent, os.W_OK):
        raise UpdateError("Sem permissão para substituir o AppImage.")

    new_file = appimage.with_name(appimage.name + ".new")
    backup = appimage.with_name(appimage.name + ".old")
    shutil.copyfile(pending.path, new_file)
    new_file.chmod(0o755)

    log_path = _log_file(base)
    script = Path(base) / "updates" / "apply-appimage.sh"
    target = shlex.quote(str(appimage))
    new = shlex.quote(str(new_file))
    old = shlex.quote(str(backup))
    _write_script(
        script,
        "\n".join(
            [
                "#!/bin/sh",
                "set -eu",
                f"LOG={shlex.quote(str(log_path))}",
                'exec >>"$LOG" 2>&1',
                f'echo "[$(date -Is)] Aplicando AppImage {pending.version}."',
                "i=0",
                (
                    f"while kill -0 {os.getpid()} 2>/dev/null "
                    '&& [ "$i" -lt 100 ]; do sleep 0.3; i=$((i + 1)); done'
                ),
                "if command -v pkill >/dev/null 2>&1; then",
                "    pkill -TERM -f -- '(^|/)learning-helper( |$)' "
                "2>/dev/null || true",
                "    sleep 1",
                "    pkill -KILL -f -- '(^|/)learning-helper( |$)' "
                "2>/dev/null || true",
                "fi",
                f"if [ -f {target} ]; then cp -f {target} {old}; fi",
                f"if mv -f {new} {target}; then",
                f"    chmod +x {target}",
                '    echo "[$(date -Is)] AppImage substituído; reabrindo."',
                "else",
                f"    if [ -f {old} ]; then mv -f {old} {target}; fi",
                '    echo "[$(date -Is)] Falha ao substituir o AppImage."',
                "fi",
                f'nohup {target} >>"$LOG" 2>&1 &',
                "",
            ]
        ),
    )
    _spawn_detached(["/bin/sh", str(script)], log_path=log_path)


def apply_pending(pending: PendingUpdate, base: Path) -> None:
    """Inicia a instalação e retorna; o processo atual deve encerrar em seguida."""
    if sys.platform == "win32":
        _apply_windows(pending, base)
        return
    if sys.platform.startswith("linux"):
        if os.environ.get("APPIMAGE"):
            _apply_appimage(pending, base)
        else:
            _apply_tarball(pending, base)
        return
    raise UpdateError("Atualização automática não disponível nesta plataforma.")
