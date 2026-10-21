"""Gera a imagem placeholder do lembrete de banheiro.

Rode com `uv run python packaging/make_bathroom_image.py` para regerar
`src/learning_helper/overlay/bathroom.png` (commitado no repositório).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 512
OUTPUT = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "learning_helper"
    / "overlay"
    / "bathroom.png"
)
BACKGROUND = (0, 122, 255, 255)
PORCELAIN = (255, 255, 255, 255)


def build_image(size: int = SIZE) -> Image.Image:
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    margin = size // 16
    draw.rounded_rectangle(
        (margin, margin, size - margin, size - margin),
        radius=size // 5,
        fill=BACKGROUND,
    )

    # Caixa de descarga.
    draw.rounded_rectangle(
        (int(size * 0.33), int(size * 0.16), int(size * 0.67), int(size * 0.42)),
        radius=int(size * 0.04),
        fill=PORCELAIN,
    )
    # Botão.
    draw.ellipse(
        (int(size * 0.60), int(size * 0.20), int(size * 0.64), int(size * 0.24)),
        fill=BACKGROUND,
    )
    # Vaso e abertura do assento.
    draw.ellipse(
        (int(size * 0.29), int(size * 0.40), int(size * 0.71), int(size * 0.80)),
        fill=PORCELAIN,
    )
    draw.ellipse(
        (int(size * 0.35), int(size * 0.46), int(size * 0.65), int(size * 0.72)),
        fill=BACKGROUND,
    )
    return image


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    build_image().save(OUTPUT)
    print(f"Imagem gravada em {OUTPUT}")


if __name__ == "__main__":
    main()
