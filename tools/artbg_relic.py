#!/usr/bin/env python3
"""
artbg_relic.py — fundo estatico do Arisen Relic HUD (v9)

    python tools/artbg_relic.py

Assa no fundo tudo que nao muda: moldura, topo, linhas e losangos do banner,
moldura da barra de stamina com preenchimento estatico, icones vetoriais do
HUD, sufixos ° e % e o placeholder --.
Gera build/bg_relic.png e build/bg_relic_aod.png.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFont

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
import gen_assets as ga  # noqa: E402

W, H = 280, 456
SS = 4
SRC = Path.home() / "Downloads" / "zapi-img" / "fundo.jpg.jpg"
DIV = (0x3A, 0x2A, 0x1D)
SHADOW = (0x2A, 0x12, 0x0A)

BANNER_LINE_Y = 321
BAR_Y, BAR_H = 333, 6
BAR_X0, BAR_X1 = 45, 235


def s(v: float) -> int:
    return int(round(v * SS))


def heart_icon(d, cx, cy, size, fill):
    pts = []
    for i in range(144):
        t = math.tau * i / 144
        x = 16 * math.sin(t) ** 3
        y = (13 * math.cos(t) - 5 * math.cos(2 * t)
             - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * size / 33.0, cy - y * size / 33.0 - size * 0.06))
    d.polygon(pts, fill=fill)


def flame_icon(d, cx, cy, size, edge, inner):
    pts = [(cx, cy - size * 0.62), (cx + size * 0.42, cy - size * 0.02),
           (cx + size * 0.30, cy + size * 0.48), (cx, cy + size * 0.60),
           (cx - size * 0.30, cy + size * 0.48), (cx - size * 0.42, cy - size * 0.02)]
    d.polygon(pts, outline=edge, fill=None)
    d.polygon([(cx, cy - size * 0.18), (cx + size * 0.18, cy + size * 0.14),
               (cx, cy + size * 0.42), (cx - size * 0.18, cy + size * 0.14)], fill=inner)


def sun_icon(d, cx, cy, r, color):
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=s(0.9))
    for i in range(8):
        a = math.tau * i / 8
        d.line([(cx + math.cos(a) * (r + s(3)), cy + math.sin(a) * (r + s(3))),
                (cx + math.cos(a) * (r + s(6)), cy + math.sin(a) * (r + s(6)))],
               fill=color, width=s(0.9))


def energy_icon(d, cx, cy, r, color):
    pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    d.line(pts + [pts[0]], fill=color, width=s(0.9))
    d.polygon([(cx, cy - r * 0.45), (cx + r * 0.45, cy), (cx, cy + r * 0.45),
               (cx - r * 0.45, cy)], fill=color)


def main() -> int:
    if not SRC.exists():
        sys.exit(f"[art] ausente: {SRC}")
    font_path, _ = ga.resolve_font(None, PROJECT)
    build = PROJECT / "build"

    canvas = Image.open(SRC).convert("RGBA").resize((s(W), s(H)), Image.Resampling.LANCZOS)
    d = ImageDraw.Draw(canvas)

    # topo
    f_top = ImageFont.truetype(str(font_path), s(15))
    d.text((s(256), s(42)), "QUA 11 NOV", font=f_top, fill=(*ga.PARCHMENT, 255), anchor="rs")
    ga.diamond(d, s(26), s(37), s(4.5), (*ga.GOLD, 255), width=s(1))
    ga.diamond(d, s(26), s(37), s(1.6), (*ga.GOLD, 255), width=0, fill=(*ga.GOLD, 255))
    d.text((s(38), s(42)), "I", font=f_top, fill=(*ga.GOLD, 255), anchor="ls")

    # banner: linhas, losangos e o glifo
    ly = s(BANNER_LINE_Y)
    d.line([(s(20), ly), (s(90), ly)], fill=(*DIV, 255), width=s(0.9))
    d.line([(s(218), ly), (s(260), ly)], fill=(*DIV, 255), width=s(0.9))
    for cx in (s(96), s(214)):
        ga.diamond(d, cx, ly, s(3.6), (*ga.GOLD, 255), width=0, fill=(*ga.GOLD, 255))
    ga.diamond(d, s(104), ly, s(4.8), (*ga.GOLD, 255), width=s(0.9))
    ga.diamond(d, s(104), ly, s(1.7), (*ga.GOLD, 255), width=0, fill=(*ga.GOLD, 255))

    # barra de stamina: moldura chanfrada + preenchimento estatico de 70%
    y0 = s(BAR_Y)
    hgt = s(BAR_H)
    x0, x1, cham = s(BAR_X0), s(BAR_X1), s(6)
    d.polygon([(x0, y0), (x1, y0), (x1 - cham, y0 + hgt), (x0 + cham, y0 + hgt)],
              outline=(*ga.BRONZE_LT, 170), width=s(0.9))
    fill_end = x0 + cham + int((x1 - x0 - cham * 2) * 0.70)
    grad = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for gx in range(x0 + cham, fill_end):
        t = (gx - x0) / max(1, fill_end - x0)
        col = tuple(int(ga.EMBER[i] + (ga.GOLD[i] - ga.EMBER[i]) * t) for i in range(3))
        gd.line([(gx, y0 + s(1.5)), (gx, y0 + hgt - s(1.5))], fill=(*col, 240))
    canvas.alpha_composite(grad)
    for cx in (x0 - s(2), x1 + s(2)):
        ga.diamond(d, cx, y0 + hgt / 2, s(3.4), (*ga.GOLD, 255), width=0, fill=(*ga.GOLD, 255))

    # icones do HUD
    heart_icon(d, s(46), s(360), s(17), (*ga.EMBER, 255))
    flame_icon(d, s(176), s(360), s(17), (*ga.GOLD, 255), (*ga.EMBER, 235))
    sun_icon(d, s(46), s(412), s(6.5), (*ga.GOLD, 255))
    energy_icon(d, s(176), s(412), s(8), (*ga.GOLD, 255))
    ga.diamond(d, s(140), s(392), s(4.2), (*ga.GOLD, 255), width=s(0.9))
    ga.diamond(d, s(140), s(392), s(1.4), (*ga.GOLD, 255), width=0, fill=(*ga.GOLD, 255))

    # sufixos e placeholder
    f_sm = ImageFont.truetype(str(font_path), s(30))
    d.text((s(102), s(427)), "\u00b0", font=f_sm, fill=(*ga.GOLD, 255), anchor="ls")
    d.text((s(232), s(427)), "%", font=f_sm, fill=(*ga.GOLD, 255), anchor="ls")
    d.text((s(60), s(427)), "--", font=f_sm, fill=(*DIV, 255), anchor="ls")

    canvas.resize((W, H), Image.Resampling.LANCZOS).save(build / "bg_relic.png")
    aod = ImageEnhance.Brightness(canvas.convert("RGB")).enhance(0.42).convert("RGBA")
    aod.resize((W, H), Image.Resampling.LANCZOS).save(build / "bg_relic_aod.png")
    print(f"[relic] {build / 'bg_relic.png'} + bg_relic_aod.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
