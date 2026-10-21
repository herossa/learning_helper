import hashlib
import io
import json
import sys
import tarfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from learning_helper.updates import client, install, service
from learning_helper.updates.client import download_asset
from learning_helper.updates.manifest import (
    Asset,
    Release,
    UpdateError,
    is_newer,
    parse_manifest,
    parse_version,
)
from learning_helper.updates.state import (
    UpdateState,
    block_version,
    is_blocked,
    load_state,
    record_attempt,
    save_state,
    state_path,
)


@pytest.mark.parametrize(
    ("candidate", "current", "expected"),
    [
        ("0.5.0", "0.4.0", True),
        ("0.10.0", "0.9.9", True),
        ("v0.5.0", "0.5.0", False),
        ("0.4.0", "0.5.0", False),
        ("0.5", "0.5.0", False),
    ],
)
def test_is_newer(candidate, current, expected) -> None:
    assert is_newer(candidate, current) is expected


def test_parse_version_rejects_garbage() -> None:
    with pytest.raises(UpdateError):
        parse_version("abc")


def _release(version: str = "0.5.0") -> Release:
    return Release(
        version=version,
        assets={
            "linux_tarball": Asset(
                name=f"LearningHelper-{version}-linux-x86_64.tar.gz",
                url=f"https://example.invalid/{version}.tar.gz",
                sha256="0" * 64,
            ),
            "windows_setup": Asset(
                name=f"LearningHelper-{version}-Setup.exe",
                url=f"https://example.invalid/{version}.exe",
                sha256="1" * 64,
            ),
        },
    )


def test_parse_manifest_accepts_valid_payload() -> None:
    release = parse_manifest(
        {
            "version": "v0.5.0",
            "assets": {
                "windows_setup": {
                    "name": "setup.exe",
                    "url": "https://example.invalid/setup.exe",
                    "sha256": "a" * 64,
                }
            },
        }
    )
    assert release.version == "0.5.0"
    assert release.assets["windows_setup"].sha256 == "a" * 64


@pytest.mark.parametrize(
    "payload",
    [
        None,
        {},
        {"version": "0.5.0"},
        {"version": "0.5.0", "assets": {}},
        {
            "version": "0.5.0",
            "assets": {"x": {"name": "x", "url": "x", "sha256": "nope"}},
        },
    ],
)
def test_parse_manifest_rejects_invalid_payload(payload) -> None:
    with pytest.raises(UpdateError):
        parse_manifest(payload)


def test_asset_key_selects_platform(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    assert install.asset_key() == "windows_setup"

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("APPIMAGE", raising=False)
    assert install.asset_key() == "linux_tarball"

    monkeypatch.setenv("APPIMAGE", "/tmp/LearningHelper.AppImage")
    assert install.asset_key() == "linux_appimage"


def test_asset_key_is_none_in_development(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert install.asset_key() is None


def _make_tar(path, entries) -> None:
    with tarfile.open(path, "w:gz") as tar:
        for name, data, kind in entries:
            info = tarfile.TarInfo(name)
            if kind == "dir":
                info.type = tarfile.DIRTYPE
                info.mode = 0o755
                tar.addfile(info)
            elif kind == "symlink":
                info.type = tarfile.SYMTYPE
                info.linkname = data.decode()
                tar.addfile(info)
            elif kind == "hardlink":
                info.type = tarfile.LNKTYPE
                info.linkname = data.decode()
                tar.addfile(info)
            else:
                info.size = len(data)
                info.mode = 0o755
                tar.addfile(info, io.BytesIO(data))


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="criar symlinks no Windows exige privilégio especial",
)
def test_safe_extract_accepts_links_inside(tmp_path) -> None:
    archive = tmp_path / "ok.tar.gz"
    _make_tar(
        archive,
        [
            ("pkg/", b"", "dir"),
            ("pkg/target.txt", b"hello", "file"),
            ("pkg/link", b"target.txt", "symlink"),
        ],
    )
    destination = tmp_path / "out"
    destination.mkdir()

    install._safe_extract(archive, destination)

    assert (destination / "pkg" / "target.txt").read_bytes() == b"hello"
    assert (destination / "pkg" / "link").is_symlink()


@pytest.mark.parametrize(
    "entry",
    [
        ("../evil.txt", b"x", "file"),
        ("pkg/link", b"../../etc/passwd", "symlink"),
        ("pkg/link", b"../../etc/passwd", "hardlink"),
    ],
)
def test_safe_extract_rejects_paths_outside(tmp_path, entry) -> None:
    archive = tmp_path / "bad.tar.gz"
    _make_tar(archive, [entry])
    destination = tmp_path / "out"
    destination.mkdir()

    with pytest.raises(UpdateError):
        install._safe_extract(archive, destination)

    assert not (tmp_path / "evil.txt").exists()


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="layout e symlink são específicos do Linux",
)
def test_linux_prefix_follows_installed_symlink(tmp_path, monkeypatch) -> None:
    executable = tmp_path / "opt" / "learning-helper" / "learning-helper"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    symlink = bin_dir / "learning-helper"
    symlink.symlink_to(executable)

    monkeypatch.setattr(sys, "executable", str(symlink))
    assert install.linux_prefix() == tmp_path


def test_apply_tarball_writes_script(tmp_path, monkeypatch) -> None:
    archive = tmp_path / "pkg.tar.gz"
    _make_tar(
        archive,
        [
            ("LearningHelper-0.5.0/", b"", "dir"),
            ("LearningHelper-0.5.0/install-user.sh", b"#!/bin/sh\n", "file"),
            ("LearningHelper-0.5.0/learning-helper", b"bin", "file"),
        ],
    )
    prefix = tmp_path / "prefix"
    pending = install.PendingUpdate("0.5.0", "linux_tarball", archive)
    base = tmp_path / "data"
    spawned = []
    monkeypatch.setattr(install, "linux_prefix", lambda: prefix)
    monkeypatch.setattr(
        install,
        "_spawn_detached",
        lambda command, *, log_path: spawned.append((command, log_path)),
    )

    install._apply_tarball(pending, base)

    script = base / "updates" / "apply-update.sh"
    content = script.read_text(encoding="utf-8")
    assert script.is_file()
    assert "install-user.sh" in content
    assert "--prefix " in content
    assert str(prefix) in content
    assert "while kill -0" in content
    assert spawned and spawned[0][0] == ["/bin/sh", str(script)]
    assert (base / "updates" / "extract-0.5.0" / "LearningHelper-0.5.0").is_dir()


def test_apply_appimage_replaces_file_from_script(tmp_path, monkeypatch) -> None:
    appimage = tmp_path / "LearningHelper.AppImage"
    appimage.write_bytes(b"old")
    appimage.chmod(0o755)
    package = tmp_path / "pkg"
    package.write_bytes(b"new")
    pending = install.PendingUpdate("0.5.0", "linux_appimage", package)
    base = tmp_path / "data"
    spawned = []
    monkeypatch.setenv("APPIMAGE", str(appimage))
    monkeypatch.setattr(
        install,
        "_spawn_detached",
        lambda command, *, log_path: spawned.append((command, log_path)),
    )

    install._apply_appimage(pending, base)

    new_file = appimage.with_name(appimage.name + ".new")
    script = base / "updates" / "apply-appimage.sh"
    assert new_file.read_bytes() == b"new"
    assert "mv -f" in script.read_text(encoding="utf-8")
    assert spawned and spawned[0][0] == ["/bin/sh", str(script)]


def test_apply_windows_builds_silent_arguments(tmp_path, monkeypatch) -> None:
    pending = install.PendingUpdate(
        "0.5.0", "windows_setup", tmp_path / "Setup.exe"
    )
    base = tmp_path / "data"
    executable = tmp_path / "Programs" / "LearningHelper" / "learning-helper.exe"
    calls = []
    monkeypatch.setattr(sys, "executable", str(executable))
    monkeypatch.setattr(install, "_windows_all_users", lambda: False)
    monkeypatch.setattr(
        install.subprocess,
        "Popen",
        lambda command, **kwargs: calls.append((command, kwargs)),
    )

    install._apply_windows(pending, base)

    command, kwargs = calls[0]
    assert "/VERYSILENT" in command
    assert "/UPDATERESTART=1" in command
    assert "/CURRENTUSER" in command
    assert f'/DIR="{executable.parent}"' in command
    assert f'/LOG="{base / "updates" / "apply.log"}"' in command
    assert kwargs["stdin"] == install.subprocess.DEVNULL

    calls.clear()
    monkeypatch.setattr(install, "_windows_all_users", lambda: True)
    install._apply_windows(pending, base)
    assert "/ALLUSERS" in calls[0][0]


class _Handler(BaseHTTPRequestHandler):
    payload = b"update-bytes"

    def do_GET(self) -> None:  # noqa: N802 - nome exigido pelo http.server
        self.send_response(200)
        self.send_header("Content-Length", str(len(self.payload)))
        self.end_headers()
        self.wfile.write(self.payload)

    def log_message(self, *_args) -> None:
        return


@pytest.fixture
def payload_server():
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_address[1]}/asset"
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_download_asset_verifies_sha256(tmp_path, payload_server) -> None:
    digest = hashlib.sha256(_Handler.payload).hexdigest()
    asset = Asset(name="pkg", url=payload_server, sha256=digest)
    destination = tmp_path / "pkg"

    assert download_asset(asset, destination) == destination
    assert destination.read_bytes() == _Handler.payload


def test_download_asset_rejects_bad_checksum(tmp_path, payload_server) -> None:
    asset = Asset(name="pkg", url=payload_server, sha256="0" * 64)
    destination = tmp_path / "pkg"

    with pytest.raises(UpdateError):
        download_asset(asset, destination)
    assert not destination.exists()
    assert not (tmp_path / "pkg.part").exists()
    assert not list(tmp_path.glob("pkg.*.part"))


def test_prepare_update_downloads_and_saves_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(install, "asset_key", lambda: "linux_tarball")

    def fake_download(asset: Asset, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"pkg")
        return destination

    monkeypatch.setattr(service, "download_asset", fake_download)
    pending = service.prepare_update(_release("0.5.0"), "0.4.0", tmp_path)

    assert pending is not None
    assert pending.version == "0.5.0"
    state = load_state(tmp_path)
    assert state.pending_version == "0.5.0"
    assert state.pending_path == str(pending.path)


def test_prepare_update_skips_when_up_to_date(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(install, "asset_key", lambda: "linux_tarball")
    assert service.prepare_update(_release("0.5.0"), "0.5.0", tmp_path) is None


def test_prepare_update_blocks_after_repeated_attempts(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(install, "asset_key", lambda: "linux_tarball")
    state = UpdateState(pending_version="0.5.0", pending_path="/tmp/pkg", attempts=3)
    save_state(tmp_path, state)

    assert service.prepare_update(_release("0.5.0"), "0.4.0", tmp_path) is None
    blocked = load_state(tmp_path)
    assert blocked.blocked_version == "0.5.0"
    assert is_blocked(blocked, "0.5.0")


def test_state_roundtrip_and_attempts(tmp_path) -> None:
    state = UpdateState()
    record_attempt(state, "0.5.0", tmp_path / "pkg", now=100.0)
    save_state(tmp_path, state)

    loaded = load_state(tmp_path)
    assert loaded.pending_version == "0.5.0"
    assert loaded.attempts == 1
    assert loaded.last_attempt == 100.0
    assert state_path(tmp_path).is_file()


def test_block_version_clears_pending(tmp_path) -> None:
    state = UpdateState(pending_version="0.5.0", pending_path="/tmp/pkg")
    block_version(state, "0.5.0", now=1000.0)
    assert is_blocked(state, "0.5.0", now=1001.0)
    assert state.pending_version is None


def _pending_download(base, version: str = "0.5.0"):
    path = base / "updates" / version / "pkg"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"pkg")
    save_state(
        base,
        UpdateState(pending_version=version, pending_path=str(path)),
    )
    return path


def test_accept_manual_request_loads_valid_pending(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(service, "asset_key", lambda: "linux_tarball")
    path = _pending_download(tmp_path)
    service.request_manual_update(tmp_path, "0.5.0")
    update_service = service.UpdateService("0.4.0", tmp_path)

    pending = update_service.accept_manual_request()

    assert pending is not None
    assert pending.version == "0.5.0"
    assert pending.path == path
    assert service.manual_request_path(tmp_path).is_file()


def test_accept_manual_request_clears_invalid_marker(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(service, "asset_key", lambda: "linux_tarball")
    _pending_download(tmp_path)
    service.request_manual_update(tmp_path, "0.6.0")
    update_service = service.UpdateService("0.4.0", tmp_path)

    assert update_service.accept_manual_request() is None
    assert not service.manual_request_path(tmp_path).exists()


def test_accept_manual_request_ignores_exhausted_attempts(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(service, "asset_key", lambda: "linux_tarball")
    path = _pending_download(tmp_path)
    save_state(
        tmp_path,
        UpdateState(
            pending_version="0.5.0",
            pending_path=str(path),
            attempts=3,
        ),
    )
    service.request_manual_update(tmp_path, "0.5.0")
    update_service = service.UpdateService("0.4.0", tmp_path)

    assert update_service.accept_manual_request() is None
    assert not service.manual_request_path(tmp_path).exists()


def test_apply_clears_manual_request_after_success(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(service, "asset_key", lambda: "linux_tarball")
    _pending_download(tmp_path)
    service.request_manual_update(tmp_path, "0.5.0")
    update_service = service.UpdateService("0.4.0", tmp_path)
    assert update_service.accept_manual_request() is not None
    applied = []
    monkeypatch.setattr(
        service,
        "apply_pending",
        lambda pending, base: applied.append((pending, base)),
    )

    assert update_service.apply() is True

    assert applied
    assert update_service.pending is None
    assert not service.manual_request_path(tmp_path).exists()
    assert load_state(tmp_path).attempts == 1


def test_apply_clears_manual_request_after_failure(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(service, "asset_key", lambda: "linux_tarball")
    _pending_download(tmp_path)
    service.request_manual_update(tmp_path, "0.5.0")
    update_service = service.UpdateService("0.4.0", tmp_path)
    assert update_service.accept_manual_request() is not None

    def fail(_pending, _base):
        raise RuntimeError("falhou")

    monkeypatch.setattr(service, "apply_pending", fail)

    with pytest.raises(UpdateError):
        update_service.apply()

    assert update_service.pending is None
    assert not service.manual_request_path(tmp_path).exists()
    assert load_state(tmp_path).attempts == 1


def test_corrupt_state_is_ignored(tmp_path) -> None:
    path = state_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{", encoding="utf-8")
    assert load_state(tmp_path) == UpdateState()


def test_check_and_download_uses_manifest(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(install, "asset_key", lambda: "linux_tarball")
    monkeypatch.setattr(
        service,
        "fetch_manifest",
        lambda _url: _release("0.5.0"),
    )

    def fake_download(asset: Asset, destination):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"pkg")
        return destination

    monkeypatch.setattr(service, "download_asset", fake_download)
    pending = service.check_and_download(
        "0.4.0",
        tmp_path,
        manifest_url="https://example.invalid/latest.json",
    )
    assert pending is not None
    assert pending.version == "0.5.0"


class _ApiHandler(BaseHTTPRequestHandler):
    payload = b"authenticated-package"

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 - nome exigido pelo http.server
        base = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.server.seen_auth.append(self.headers.get("Authorization"))
        if self.path == "/releases/latest":
            body = json.dumps(
                {
                    "tag_name": "v0.5.0",
                    "assets": [
                        {
                            "name": "latest.json",
                            "url": f"{base}/asset/latest",
                        },
                        {
                            "name": "LearningHelper-0.5.0-linux-x86_64.tar.gz",
                            "url": f"{base}/asset/pkg",
                        },
                    ],
                }
            ).encode()
            self._send(200, "application/json", body)
            return
        if self.path == "/asset/latest":
            body = json.dumps(
                {
                    "version": "0.5.0",
                    "assets": {
                        "linux_tarball": {
                            "name": "LearningHelper-0.5.0-linux-x86_64.tar.gz",
                            "url": f"{base}/asset/pkg",
                            "sha256": hashlib.sha256(self.payload).hexdigest(),
                        }
                    },
                }
            ).encode()
            self._send(200, "application/json", body)
            return
        if self.path == "/asset/pkg":
            self._send(200, "application/octet-stream", self.payload)
            return
        self._send(404, "text/plain", b"not found")

    def log_message(self, *_args) -> None:
        return


@pytest.fixture
def api_server(monkeypatch):
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), _ApiHandler)
    httpd.seen_auth = []
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    monkeypatch.setattr(
        client,
        "DEFAULT_RELEASES_API_URL",
        f"{base}/releases/latest",
    )
    monkeypatch.setenv(client.TOKEN_ENV, "secret-token")
    try:
        yield httpd, base
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_fetch_manifest_uses_env_url(monkeypatch) -> None:
    monkeypatch.setenv(client.URL_ENV, "https://example.invalid/latest.json")
    monkeypatch.delenv(client.TOKEN_ENV, raising=False)
    seen = []

    def fake_direct(url, *, timeout):
        seen.append(url)
        return _release("0.5.0")

    monkeypatch.setattr(client, "_fetch_manifest_direct", fake_direct)
    assert client.fetch_manifest().version == "0.5.0"
    assert seen == ["https://example.invalid/latest.json"]


def test_fetch_manifest_api_enriches_and_downloads(tmp_path, api_server) -> None:
    httpd, base = api_server
    release = client._fetch_manifest_api("secret-token", timeout=5)

    assert release.version == "0.5.0"
    asset = release.assets["linux_tarball"]
    assert asset.api_url == f"{base}/asset/pkg"
    assert "Bearer secret-token" in httpd.seen_auth

    destination = tmp_path / "pkg"
    client.download_asset(asset, destination)
    assert destination.read_bytes() == _ApiHandler.payload


def test_fetch_manifest_api_rejects_version_mismatch(monkeypatch) -> None:
    metadata = {
        "tag_name": "v0.6.0",
        "assets": [
            {"name": "latest.json", "url": "https://example.invalid/latest"},
        ],
    }
    manifest = {
        "version": "0.5.0",
        "assets": {
            "linux_tarball": {
                "name": "pkg",
                "url": "https://example.invalid/pkg",
                "sha256": "a" * 64,
            }
        },
    }
    responses = {
        client.DEFAULT_RELEASES_API_URL: json.dumps(metadata).encode(),
        "https://example.invalid/latest": json.dumps(manifest).encode(),
    }

    def fake_read(url, **_kwargs):
        return responses[url]

    monkeypatch.setattr(client, "_read_bytes", fake_read)
    with pytest.raises(UpdateError):
        client._fetch_manifest_api("token", timeout=5)
