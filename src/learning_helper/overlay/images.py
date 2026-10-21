from __future__ import annotations

from pathlib import Path

from PIL import Image

BATHROOM_IMAGE_NAME = "bathroom.png"


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def color_swatch(rgb: tuple[int, int, int], width: int, height: int) -> Image.Image:
    return Image.new("RGB", (width, height), rgb)


def bathroom_image_path() -> Path:
    return Path(__file__).with_name(BATHROOM_IMAGE_NAME)


def load_bathroom_image() -> Image.Image:
    with Image.open(bathroom_image_path()) as image:
        return image.copy()
