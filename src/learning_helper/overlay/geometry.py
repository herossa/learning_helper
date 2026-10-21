from __future__ import annotations


def format_geometry(width: int, height: int, x: int = 0, y: int = 0) -> str:
    """Geometria Tk com offsets assinados (monitor à esquerda/acima)."""
    return f"{width}x{height}{x:+d}{y:+d}"
