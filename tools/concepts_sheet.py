#!/usr/bin/env python3
"""
concepts_sheet.py — folha 2x dos conceitos, sem corpo de relógio

    python tools/concepts_sheet.py

Gera out/concepts_hires.png (5 células: A, B, C, D e tudo junto) e
out/concept_<A..D>.png em 560x912.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
import gen_assets as ga  # noqa: E402

S = 2
BASE = PROJECT / "out" / "v8_target.png"
OUT = PROJECT / "out" / "concepts_hires.png"
DIV = (0x3A, 0x2A, 0x1D)


def draw_secs(d: ImageDraw.ImageDraw, font_path: Path) -> None:
    f = ImageFont.truetype(str(font_path), 15 * S)
    fs = ImageFont.truetype(str(font_path), 9 * S)
    d.text((66 * S, 42 * S), "42", font=f, fill=(*ga.GOLD, 255), anchor="ls")
    d.text((88 * S, 42 * S), "s", font=fs, fill=(*ga.BRONZE_LT, 255), anchor="ls")


def draw_steps(d: ImageDraw.ImageDraw) -> None:
    x0, x1, y = 56 * S, 224 * S, 291 * S
    d.line([(x0, y), (x1, y)], fill=(*DIV, 255), width=2 * S)
    end = x0 + int((x1 - x0) * 0.70)
    d.line([(x0, y), (end, y)], fill=(*ga.GOLD, 220), width=2 * S)
    ga.diamond(d, end, y, 3.0 * S, (*ga.GOLD, 255), width=0, fill=(*ga.GOLD, 255))


def draw_weather(d: ImageDraw.ImageDraw) -> None:
    cx, cy, r = 110 * S, 372 * S, 5.5 * S
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*ga.GOLD, 255), width=S)
    for i in range(8):
        a = math.tau * i / 8
        d.line([(cx + math.cos(a) * (r + 3 * S), cy + math.sin(a) * (r + 3 * S)),
                (cx + math.cos(a) * (r + 6 * S), cy + math.sin(a) * (r + 6 * S))],
               fill=(*ga.GOLD, 255), width=S)


def draw_battery(d: ImageDraw.ImageDraw) -> None:
    x0, x1, y = 176 * S, 232 * S, 424 * S
    d.line([(x0, y), (x1, y)], fill=(*DIV, 255), width=2 * S)
    end = x0 + int((x1 - x0) * 0.97)
    d.line([(x0, y), (end, y)], fill=(*ga.GOLD, 220), width=2 * S)


CONCEPTS = [
    ("A", "segundos no topo", [draw_secs]),
    ("B", "progresso de passos", [draw_steps]),
    ("C", "icone de clima", [draw_weather]),
    ("D", "bateria em barra", [draw_battery]),
    ("E", "A + B + C + D", [draw_secs, draw_steps, draw_weather, draw_battery]),
]


def render(base: Image.Image, font_path: Path, fns) -> Image.Image:
    img = base.copy()
    d = ImageDraw.Draw(img)
    for fn in fns:
        if fn is draw_secs:
            fn(d, font_path)
        else:
            fn(d)
    return img


def main() -> int:
    if not BASE.exists():
        sys.exit(f"base ausente: {BASE} (rode tools/sim_preview.py)")
    font_path, _ = ga.resolve_font(None, PROJECT)
    base = Image.open(BASE).convert("RGBA").resize(
        (280 * S, 456 * S), Image.Resampling.LANCZOS)

    cells = []
    for letter, caption, fns in CONCEPTS:
        img = render(base, font_path, fns)
        img.save(PROJECT / "out" / f"concept_{letter}.png")
        cells.append((letter, caption, img))

    cell_w, cell_h = 560, 912
    cols, rows = 3, 2
    sheet = Image.new("RGB", (cols * cell_w + 60, rows * (cell_h + 50) + 40), (11, 9, 8))
    d = ImageDraw.Draw(sheet)
    f_cap = ImageFont.truetype(str(font_path), 22)
    for i, (letter, caption, img) in enumerate(cells):
        col, row = i % cols, i // cols
        x = 20 + col * (cell_w + 10)
        y = 20 + row * (cell_h + 50)
        d.text((x, y), f"{letter}  ·  {caption}", font=f_cap, fill=(236, 192, 105))
        sheet.paste(img, (x, y + 22))

    sheet.save(OUT, quality=95)
    print(f"[concepts] {OUT}  + concept_A..E.png em out/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
