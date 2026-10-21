"""Gera o ícone do app (PNG 512 e ICO multi-tamanho).

Rode com `uv run python packaging/make_icon.py` sempre que quiser trocar a arte.
Os arquivos gerados são commitados para o build não depender deste script.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SIZE = 512
OUT_DIR = Path(__file__).resolve().parent / "icons"
BACKGROUND = (43, 45, 66, 255)
SQUARES = ((255, 209, 102), (0, 122, 255), (52, 199, 89), (255, 59, 48))
FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
)


def _font(size: int) -> ImageFont.ImageFont:
    for candidate in FONT_CANDIDATES:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow antigo
        return ImageFont.load_default()


def build_icon(size: int = SIZE) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = size // 16
    draw.rounded_rectangle(
        (margin, margin, size - margin, size - margin),
        radius=size // 6,
        fill=BACKGROUND,
    )

    grid = int(size * 0.46)
    gap = size // 40
    cell = (grid - gap) // 2
    left = (size - grid) // 2 - size // 16
    top = (size - grid) // 2 - size // 20
    for index, color in enumerate(SQUARES):
        x = left + (index % 2) * (cell + gap)
        y = top + (index // 2) * (cell + gap)
        draw.rounded_rectangle(
            (x, y, x + cell, y + cell),
            radius=cell // 6,
            fill=color,
        )

    badge_radius = int(size * 0.17)
    center = (int(size * 0.72), int(size * 0.72))
    draw.ellipse(
        (
            center[0] - badge_radius,
            center[1] - badge_radius,
            center[0] + badge_radius,
            center[1] + badge_radius,
        ),
        fill=(255, 255, 255, 255),
    )
    font = _font(int(size * 0.24))
    draw.text(center, "?", font=font, fill=BACKGROUND, anchor="mm")
    return image


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    icon = build_icon()
    icon.save(OUT_DIR / "learning-helper.png")
    icon.save(
        OUT_DIR / "learning-helper.ico",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print(f"Ícones gravados em {OUT_DIR}")


if __name__ == "__main__":
    main()
