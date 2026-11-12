#!/usr/bin/env python3
"""Gera o latest.json publicado junto com os pacotes de uma release."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPOSITORY = "herossa/learning_helper"
ASSET_PATTERNS = {
    "windows_setup": "LearningHelper-{version}-Setup.exe",
    "linux_appimage": "LearningHelper-{version}-x86_64.AppImage",
    "linux_tarball": "LearningHelper-{version}-linux-x86_64.tar.gz",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(
    version: str,
    dist_dir: Path,
    *,
    tag: str | None = None,
    base_url: str | None = None,
    asset_keys: list[str] | None = None,
) -> dict:
    release_tag = tag or f"v{version}"
    release_url = base_url or (
        f"https://github.com/{REPOSITORY}/releases/download/{release_tag}"
    )
    selected = (
        list(ASSET_PATTERNS)
        if asset_keys is None
        else [key for key in asset_keys if key in ASSET_PATTERNS]
    )
    assets = {}
    missing = []
    for key in selected:
        pattern = ASSET_PATTERNS[key]
        name = pattern.format(version=version)
        path = dist_dir / name
        if not path.is_file():
            missing.append(name)
            continue
        assets[key] = {
            "name": name,
            "url": f"{release_url.rstrip('/')}/{name}",
            "sha256": sha256_file(path),
        }
    if missing:
        raise SystemExit("Arquivos ausentes para o manifesto: " + ", ".join(missing))
    if not assets:
        raise SystemExit("Nenhum asset selecionado para o manifesto.")
    return {"version": version, "assets": assets}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--tag")
    parser.add_argument("--base-url")
    parser.add_argument(
        "--assets",
        help=(
            "Chaves separadas por vírgula a incluir no manifesto "
            "(padrão: todas). Ex.: windows_setup"
        ),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    asset_keys = None
    if args.assets:
        asset_keys = [item.strip() for item in args.assets.split(",") if item.strip()]
        unknown = [item for item in asset_keys if item not in ASSET_PATTERNS]
        if unknown:
            parser.error("assets desconhecidos: " + ", ".join(unknown))

    version = args.version.lstrip("vV")
    manifest = build_manifest(
        version,
        args.dist,
        tag=args.tag,
        base_url=args.base_url,
        asset_keys=asset_keys,
    )
    output = args.output or (args.dist / "latest.json")
    output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
