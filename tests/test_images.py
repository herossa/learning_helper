from learning_helper.overlay.images import (
    bathroom_image_path,
    color_swatch,
    load_bathroom_image,
    rgb_to_hex,
)


def test_rgb_to_hex() -> None:
    assert rgb_to_hex((255, 0, 128)) == "#ff0080"


def test_color_swatch_size_and_pixels() -> None:
    image = color_swatch((12, 34, 56), 5, 7)
    assert image.size == (5, 7)
    assert image.getpixel((0, 0)) == (12, 34, 56)
    assert image.getpixel((4, 6)) == (12, 34, 56)


def test_bathroom_image_exists_and_loads() -> None:
    path = bathroom_image_path()
    assert path.is_file()
    image = load_bathroom_image()
    assert image.size == (512, 512)
    assert image.mode == "RGBA"

