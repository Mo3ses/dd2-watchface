#!/usr/bin/env python3
"""
artbg.py — fundo a partir da arte do Kai (fundo.jpg), com os rótulos por cima

    python tools/artbg.py [--src CAMINHO]

Gera build/bg_art.png e build/bg_art_aod.png.
A arte já traz a moldura e o coração de brasa; o script só assenta data,
rótulos e o ícone de pulso na grade de baixo.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
import gen_assets as ga  # noqa: E402

W, H = 280, 456
S = 2
DEFAULT_SRC = Path.home() / "Downloads" / "zapi-img" / "fundo.jpg.jpg"

LABELS = [("CAL", 152, 292), ("\u00b0C", 24, 292), ("BAT", 152, 362)]
DATE = "QUA 11 NOV"
DATE_XY = (256, 62)
HEART = (30, 286)
PCT = (252, 410)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(DEFAULT_SRC))
    args = ap.parse_args()

    src = Path(args.src).expanduser()
    if not src.exists():
        sys.exit(f"[art] nao encontrei: {src}")

    font_path, _ = ga.resolve_font(None, PROJECT)
    build = PROJECT / "build"

    art = Image.open(src).convert("RGBA").resize((W * S, H * S), Image.Resampling.LANCZOS)

    lay = Image.new("RGBA", art.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)

    f_date = ImageFont.truetype(str(font_path), 15 * S)
    d.text((DATE_XY[0] * S, DATE_XY[1] * S), DATE, font=f_date,
           fill=(*ga.PARCHMENT, 255), anchor="rs")

    f_lab = ImageFont.truetype(str(font_path), 12 * S)
    for text, x, y in LABELS:
        ga.tracked(d, (x * S, y * S), text, f_lab, (*ga.BRONZE_LT, 255), tracking=1.3 * S)

    ga.heart(d, HEART[0] * S, HEART[1] * S, 16 * S, (*ga.EMBER, 255))

    f_pct = ImageFont.truetype(str(font_path), 13 * S)
    d.text((PCT[0] * S, PCT[1] * S), "%", font=f_pct, fill=(*ga.BRONZE_LT, 255), anchor="rs")

    art.alpha_composite(lay)
    art.resize((W, H), Image.Resampling.LANCZOS).save(build / "bg_art.png")

    aod = ImageEnhance.Brightness(art.convert("RGB")).enhance(0.42).convert("RGBA")
    aod.resize((W, H), Image.Resampling.LANCZOS).save(build / "bg_art_aod.png")
    print(f"[art] {build / 'bg_art.png'}  + bg_art_aod.png  (fonte {src.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
