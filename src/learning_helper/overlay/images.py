from __future__ import annotations

import numpy as np
from PIL import Image


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#%02x%02x%02x" % rgb


def color_swatch(rgb: tuple[int, int, int], width: int, height: int) -> Image.Image:
    array = np.zeros((height, width, 3), dtype=np.uint8)
    for index, value in enumerate(rgb):
        array[:, :, index] = value
    return Image.fromarray(array)
