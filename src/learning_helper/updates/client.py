"""Cliente HTTP mínimo para o manifesto e os pacotes de atualização.

Em repositórios públicos, o manifesto é lido direto de
``releases/latest/download/latest.json``. Em repositórios privados, defina
``LEARNING_HELPER_UPDATE_TOKEN`` com um token somente leitura; nesse caso o
cliente usa a API do GitHub e baixa os assets pela URL autenticada.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from pathlib import Path
from urllib.request import Request, urlopen

from learning_helper import __version__
from learning_helper.updates.manifest import Asset, Release, UpdateError, parse_manifest

DEFAULT_MANIFEST_URL = (
    "https://github.com/herossa/learning_helper/releases/latest/download/latest.json"
)
DEFAULT_RELEASES_API_URL = (
    "https://api.github.com/repos/herossa/learning_helper/releases/latest"
)
TOKEN_ENV = "LEARNING_HELPER_UPDATE_TOKEN"
URL_ENV = "LEARNING_HELPER_UPDATE_URL"
MAX_MANIFEST_BYTES = 256 * 1024
MAX_DOWNLOAD_BYTES = 500 * 1024 * 1024
CHUNK_SIZE = 64 * 1024


def _auth_token() -> str | None:
    token = os.environ.get(TOKEN_ENV, "").strip()
    return token or None


def _headers(
    *,
    token: str | None = None,
    accept: str | None = None,
) -> dict[str, str]:
    headers = {
        "User-Agent": f"LearningHelper/{__version__}",
        "Cache-Control": "no-cache",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if accept:
        headers["Accept"] = accept
    return headers


def _open(
    url: str,
    *,
    token: str | None = None,
    accept: str | None = None,
    timeout: float,
):
    return urlopen(
        Request(url, headers=_headers(token=token, accept=accept)),
        timeout=timeout,
    )


def _loads(body: bytes):
    try:
        return json.loads(body)
    except (TypeError, ValueError) as exc:
        raise UpdateError("Manifesto de atualização inválido.") from exc


def _read_bytes(
    url: str,
    *,
    token: str | None = None,
    accept: str | None = None,
    timeout: float,
    max_bytes: int,
) -> bytes:
    try:
        with _open(url, token=token, accept=accept, timeout=timeout) as response:
            if not 200 <= response.status < 300:
                raise UpdateError(
                    f"Conteúdo de atualização indisponível (HTTP {response.status})."
                )
            body = response.read(max_bytes + 1)
    except UpdateError:
        raise
    except Exception as exc:
        raise UpdateError(f"Não foi possível consultar atualizações: {exc}") from exc
    if len(body) > max_bytes:
        raise UpdateError("Manifesto de atualização grande demais.")
    return body


def _fetch_manifest_direct(url: str, *, timeout: float) -> Release:
    body = _read_bytes(
        url,
        timeout=timeout,
        max_bytes=MAX_MANIFEST_BYTES,
    )
    return parse_manifest(_loads(body))


def _fetch_manifest_api(token: str, *, timeout: float) -> Release:
    metadata = _loads(
        _read_bytes(
            DEFAULT_RELEASES_API_URL,
            token=token,
            accept="application/vnd.github+json",
            timeout=timeout,
            max_bytes=MAX_MANIFEST_BYTES,
        )
    )
    if not isinstance(metadata, dict):
        raise UpdateError("Resposta da API do GitHub inválida.")

    raw_assets = metadata.get("assets")
    if not isinstance(raw_assets, list):
        raise UpdateError("Release mais recente sem assets.")
    by_name: dict[str, str] = {}
    for item in raw_assets:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        api_url = item.get("url")
        if isinstance(name, str) and isinstance(api_url, str):
            by_name[name] = api_url

    manifest_url = by_name.get("latest.json")
    if manifest_url is None:
        raise UpdateError("Release mais recente sem latest.json.")

    release = parse_manifest(
        _loads(
            _read_bytes(
                manifest_url,
                token=token,
                accept="application/octet-stream",
                timeout=timeout,
                max_bytes=MAX_MANIFEST_BYTES,
            )
        )
    )

    tag = metadata.get("tag_name")
    if isinstance(tag, str) and tag.lstrip("vV") != release.version:
        raise UpdateError("Manifesto não corresponde à release mais recente.")

    assets: dict[str, Asset] = {}
    for key, asset in release.assets.items():
        api_url = by_name.get(asset.name)
        if api_url is None:
            assets[key] = asset
        else:
            assets[key] = Asset(
                name=asset.name,
                url=asset.url,
                sha256=asset.sha256,
                api_url=api_url,
            )
    return Release(version=release.version, assets=assets)


def fetch_manifest(
    url: str | None = None,
    *,
    timeout: float = 5.0,
    token: str | None = None,
) -> Release:
    configured = (url or "").strip()
    if not configured:
        configured = os.environ.get(URL_ENV, "").strip()
    configured = configured or DEFAULT_MANIFEST_URL

    token = token or _auth_token()
    if token and configured == DEFAULT_MANIFEST_URL:
        return _fetch_manifest_api(token, timeout=timeout)
    try:
        return _fetch_manifest_direct(configured, timeout=timeout)
    except UpdateError as exc:
        if configured == DEFAULT_MANIFEST_URL and not token:
            raise UpdateError(
                f"{exc} Se o repositório for privado, defina {TOKEN_ENV} "
                "com um token somente leitura."
            ) from exc
        raise


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_asset(
    asset: Asset,
    destination: Path,
    *,
    timeout: float = 60.0,
) -> Path:
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_file() and sha256_file(destination) == asset.sha256:
        return destination

    url = asset.api_url or asset.url
    token = _auth_token() if asset.api_url else None
    accept = "application/octet-stream" if asset.api_url else None
    # Nome único por processo/thread: o app principal e as Configurações podem
    # baixar o mesmo pacote ao mesmo tempo sem corromper o arquivo um do outro.
    temporary = destination.with_name(
        f"{destination.name}.{os.getpid()}.{threading.get_ident()}.part"
    )
    digest = hashlib.sha256()
    total = 0
    try:
        with _open(url, token=token, accept=accept, timeout=timeout) as response:
            if not 200 <= response.status < 300:
                raise UpdateError(
                    f"Download indisponível (HTTP {response.status})."
                )
            with temporary.open("wb") as handle:
                for chunk in iter(lambda: response.read(CHUNK_SIZE), b""):
                    total += len(chunk)
                    if total > MAX_DOWNLOAD_BYTES:
                        raise UpdateError("Pacote de atualização grande demais.")
                    digest.update(chunk)
                    handle.write(chunk)
    except UpdateError:
        temporary.unlink(missing_ok=True)
        raise
    except Exception as exc:
        temporary.unlink(missing_ok=True)
        raise UpdateError(f"Falha ao baixar atualização: {exc}") from exc

    if digest.hexdigest() != asset.sha256:
        temporary.unlink(missing_ok=True)
        raise UpdateError("SHA-256 do pacote não confere; atualização cancelada.")
    temporary.replace(destination)
    return destination
