from __future__ import annotations

from PIL import Image


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def color_swatch(rgb: tuple[int, int, int], width: int, height: int) -> Image.Image:
    return Image.new("RGB", (width, height), rgb)
