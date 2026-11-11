#!/usr/bin/env python3
"""
artbg.py — fundo a partir da arte do Kai (fundo.jpg) + HUD v5

    python tools/artbg.py [--src CAMINHO]

Gera build/bg_art.png e build/bg_art_aod.png com:
  topo      ❖ I (ouro) + data (pergaminho)
  banner    ❖ PASSOS centrado + hairlines
  grid      rótulos BPM/CAL/TEMP °C/BAT, cruz 1px #3a2a1d e losango #6e5233
  %         na baseline do número de bateria
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
import gen_assets as ga  # noqa: E402

W, H = 280, 456
S = 2
DEFAULT_SRC = Path.home() / "Downloads" / "zapi-img" / "fundo.jpg.jpg"

DIV = (0x3A, 0x2A, 0x1D)
DIA = (0x6E, 0x52, 0x33)

DATE = "QUA 11 NOV"
GRID = {  # rótulo: (x, baseline)
    "CAL": (205, 304),
    "BPM": (75, 304),
    "TEMP": (75, 376),
    "BAT": (205, 376),
}
BANNER_LABEL = "\u2756 PASSOS"
BANNER_BASE = 238
RULE_BANNER = 292
RULE_MID = 360
GRID_TOP, GRID_BOT = 292, 428
PCT = (224, 416)


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

    # topo
    f_top = ImageFont.truetype(str(font_path), 15 * S)
    d.text((256 * S, 42 * S), DATE, font=f_top, fill=(*ga.PARCHMENT, 255), anchor="rs")
    ga.diamond(d, 26 * S, 37 * S, 4.5 * S, (*ga.GOLD, 255), width=2 * S)
    ga.diamond(d, 26 * S, 37 * S, 1.6 * S, (*ga.GOLD, 255), width=0, fill=(*ga.GOLD, 255))
    d.text((38 * S, 42 * S), "I", font=f_top, fill=(*ga.GOLD, 255), anchor="ls")

    # faixa escura atrás do banner: a fumaça da arte come o contraste do texto
    band = Image.new("RGBA", art.size, (0, 0, 0, 0))
    ImageDraw.Draw(band).rounded_rectangle([16 * S, 228 * S, 264 * S, 290 * S],
                                           radius=10 * S, fill=(0, 0, 0, 150))
    art.alpha_composite(band.filter(ImageFilter.GaussianBlur(10 * S)))

    # banner de passos
    f_ban = ImageFont.truetype(str(font_path), 10.5 * S)
    ga.tracked(d, (140 * S - ga.tracked_width(BANNER_LABEL, f_ban, 1.2 * S) / 2, BANNER_BASE * S),
               BANNER_LABEL, f_ban, (*ga.BRONZE_LT, 255), tracking=1.2 * S)
    for x0, x1 in ((20, 54), (226, 260)):
        d.line([(x0 * S, 266 * S), (x1 * S, 266 * S)], fill=(*DIV, 255), width=S)

    # régua do banner e cruz do grid
    d.line([(16 * S, RULE_BANNER * S), (264 * S, RULE_BANNER * S)], fill=(*DIV, 255), width=S)
    d.line([(16 * S, RULE_MID * S), (264 * S, RULE_MID * S)], fill=(*DIV, 255), width=S)
    d.line([(140 * S, GRID_TOP * S), (140 * S, GRID_BOT * S)], fill=(*DIV, 255), width=S)
    ga.diamond(d, 140 * S, RULE_MID * S, 3.6 * S, (*DIA, 255), width=0, fill=(*DIA, 255))

    # rótulos
    f_lab = ImageFont.truetype(str(font_path), 11.5 * S)
    for text, (x, base) in GRID.items():
        txt = "TEMP \u00b0C" if text == "TEMP" else text
        w = ga.tracked_width(txt, f_lab, 1.2 * S)
        ga.tracked(d, (x * S - w / 2, base * S), txt, f_lab,
                   (*ga.BRONZE_LT, 255), tracking=1.2 * S)

    # coração do rótulo BPM, à esquerda do texto
    ga.heart(d, 55 * S, 299 * S, 12 * S, (*ga.EMBER, 255))

    # %
    f_pct = ImageFont.truetype(str(font_path), 13 * S)
    d.text((PCT[0] * S, PCT[1] * S), "%", font=f_pct, fill=(*ga.BRONZE_LT, 255), anchor="ls")

    art.alpha_composite(lay)
    art.resize((W, H), Image.Resampling.LANCZOS).save(build / "bg_art.png")

    aod = ImageEnhance.Brightness(art.convert("RGB")).enhance(0.42).convert("RGBA")
    aod.resize((W, H), Image.Resampling.LANCZOS).save(build / "bg_art_aod.png")
    print(f"[art] {build / 'bg_art.png'} + bg_art_aod.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
