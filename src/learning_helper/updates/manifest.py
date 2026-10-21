"""Manifesto de atualização publicado junto com cada release."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping

VERSION_RE = re.compile(r"^[vV]?(\d+(?:\.\d+)*)")
SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class UpdateError(RuntimeError):
    """Falha ao ler, baixar ou aplicar uma atualização."""


@dataclass(frozen=True)
class Asset:
    name: str
    url: str
    sha256: str
    # Preenchido pelo modo autenticado da API do GitHub; quando presente,
    # é preferido para o download (necessário em repositórios privados).
    api_url: str | None = None


@dataclass(frozen=True)
class Release:
    version: str
    assets: Mapping[str, Asset]


def parse_version(value: str) -> tuple[int, ...]:
    match = VERSION_RE.match(value.strip())
    if match is None:
        raise UpdateError(f"Versão inválida: {value!r}")
    return tuple(int(part) for part in match.group(1).split("."))


def is_newer(candidate: str, current: str) -> bool:
    candidate_parts = parse_version(candidate)
    current_parts = parse_version(current)
    size = max(len(candidate_parts), len(current_parts))
    return candidate_parts + (0,) * (size - len(candidate_parts)) > (
        current_parts + (0,) * (size - len(current_parts))
    )


def _asset_from_dict(key: str, value: Any) -> Asset:
    if not isinstance(value, Mapping):
        raise UpdateError(f"Asset {key!r} inválido no manifesto.")
    name = value.get("name")
    url = value.get("url")
    sha256 = value.get("sha256")
    if not isinstance(name, str) or not name.strip():
        raise UpdateError(f"Asset {key!r} sem nome.")
    if not isinstance(url, str) or not url.strip():
        raise UpdateError(f"Asset {key!r} sem URL.")
    if not isinstance(sha256, str) or SHA256_RE.fullmatch(sha256) is None:
        raise UpdateError(f"Asset {key!r} sem SHA-256 válido.")
    return Asset(name=name, url=url, sha256=sha256.lower())


def parse_manifest(payload: Any) -> Release:
    if not isinstance(payload, Mapping):
        raise UpdateError("Manifesto de atualização inválido.")
    version = payload.get("version")
    if not isinstance(version, str):
        raise UpdateError("Manifesto sem versão.")
    parse_version(version)
    raw_assets = payload.get("assets")
    if not isinstance(raw_assets, Mapping) or not raw_assets:
        raise UpdateError("Manifesto sem assets.")
    assets = {
        str(key): _asset_from_dict(str(key), value)
        for key, value in raw_assets.items()
    }
    return Release(version=version.lstrip("vV"), assets=assets)
