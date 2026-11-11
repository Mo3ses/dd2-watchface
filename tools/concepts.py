#!/usr/bin/env python3
"""
concepts.py — folha de conceitos A/B/C/D sobre o render v8

    python tools/concepts.py

Gera out/concepts.png: quatro mockups lado a lado com um acréscimo cada.
"""
from __future__ import annotations

import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
import gen_assets as ga  # noqa: E402

BASE = PROJECT / "out" / "v8_target.png"
OUT = PROJECT / "out" / "concepts.png"


def secs(img: Image.Image) -> Image.Image:
    out = img.copy()
    d = ImageDraw.Draw(out)
    f = ImageFont.truetype(str(ga.resolve_font(None, PROJECT)[0]), 15)
    d.text((66, 42), "42", font=f, fill=(*ga.GOLD, 255), anchor="ls")
    d.text((88, 42), "s", font=ImageFont.truetype(str(ga.resolve_font(None, PROJECT)[0]), 9),
           fill=(*ga.BRONZE_LT, 255), anchor="ls")
    return out


def steps_ring(img: Image.Image) -> Image.Image:
    out = img.copy()
    d = ImageDraw.Draw(out)
    x0, x1, y = 56, 224, 291
    d.line([(x0, y), (x1, y)], fill=(0x3A, 0x2A, 0x1D, 255), width=2)
    end = x0 + int((x1 - x0) * 0.70)
    d.line([(x0, y), (end, y)], fill=(*ga.GOLD, 220), width=2)
    ga.diamond(d, end, y, 3.0, (*ga.GOLD, 255), width=0, fill=(*ga.GOLD, 255))
    return out


def weather(img: Image.Image) -> Image.Image:
    out = img.copy()
    d = ImageDraw.Draw(out)
    cx, cy, r = 110, 372, 5.5
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(*ga.GOLD, 255), width=1)
    for i in range(8):
        a = math.tau * i / 8
        d.line([(cx + math.cos(a) * (r + 3), cy + math.sin(a) * (r + 3)),
                (cx + math.cos(a) * (r + 6), cy + math.sin(a) * (r + 6))],
               fill=(*ga.GOLD, 255), width=1)
    return out


def battery_bar(img: Image.Image) -> Image.Image:
    out = img.copy()
    d = ImageDraw.Draw(out)
    x0, x1, y = 176, 232, 424
    d.line([(x0, y), (x1, y)], fill=(0x3A, 0x2A, 0x1D, 255), width=2)
    end = x0 + int((x1 - x0) * 0.97)
    d.line([(x0, y), (end, y)], fill=(*ga.GOLD, 220), width=2)
    return out


CAPTIONS = [
    ("A", "segundos no topo", secs),
    ("B", "progresso de passos", steps_ring),
    ("C", "icone de clima", weather),
    ("D", "bateria em barra", battery_bar),
]


def main() -> int:
    base = Image.open(BASE).convert("RGBA")
    font_path, _ = ga.resolve_font(None, PROJECT)
    f_cap = ImageFont.truetype(str(font_path), 20)

    tmp = Path(tempfile.mkdtemp(prefix="concepts-"))
    tiles = []
    for letter, caption, fn in CAPTIONS:
        face = fn(base)
        face_path = tmp / f"{letter}.png"
        face.save(face_path)
        out = tmp / f"{letter}_mock.png"
        subprocess.run([sys.executable, str(PROJECT / "tools" / "mockup.py"),
                        str(face_path), str(out)], check=True,
                       stdout=subprocess.DEVNULL)
        tiles.append((letter, caption, Image.open(out)))

    cell_w, cell_h = 520, 780
    sheet = Image.new("RGB", (cell_w * 2 + 60, cell_h * 2 + 170), (11, 9, 8))
    d = ImageDraw.Draw(sheet)
    for i, (letter, caption, tile) in enumerate(tiles):
        col, row = i % 2, i // 2
        x = 20 + col * (cell_w + 20)
        y = 20 + row * (cell_h + 90)
        d.text((x, y), f"{letter}  ·  {caption}", font=f_cap, fill=(236, 192, 105))
        sheet.paste(tile.resize((cell_w, cell_h), Image.Resampling.LANCZOS), (x, y + 30))

    sheet.save(OUT, quality=95)
    print(f"[concepts] {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
