#!/usr/bin/env python3
"""
redesign.py — "Arisen Relic HUD": prévia do redesenho limpo

    python tools/redesign.py

Sem palavras de rótulo: ícones vetoriais + número na mesma linha.
Coração livre no centro, hora com gradiente metálico e sombra,
banner de passos abaixo do coração e barra de stamina DD2.
Gera out/v7_redesign.png (560x912) e out/v7_redesign_face.png (280x456).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT))
import gen_assets as ga  # noqa: E402

W, H = 280, 456
SS = 4
SRC = Path.home() / "Downloads" / "zapi-img" / "fundo.jpg.jpg"
OUT2 = PROJECT / "out" / "v7_redesign.png"
OUT1 = PROJECT / "out" / "v7_redesign_face.png"

GOLD_TOP = (0xF7, 0xDF, 0xA0)
GOLD_BOT = (0xC8, 0x9B, 0x52)
SHADOW = (0x2A, 0x12, 0x0A)
DIV = (0x3A, 0x2A, 0x1D)


def s(v: float) -> int:
    return int(round(v * SS))


def heart_icon(d, cx, cy, size, fill, edge=None):
    pts = []
    for i in range(144):
        t = math.tau * i / 144
        x = 16 * math.sin(t) ** 3
        y = (13 * math.cos(t) - 5 * math.cos(2 * t)
             - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * size / 33.0, cy - y * size / 33.0 - size * 0.06))
    d.polygon(pts, fill=fill, outline=edge)


def flame_icon(d, cx, cy, size, edge, inner):
    pts = [(cx, cy - size * 0.62), (cx + size * 0.42, cy - size * 0.02),
           (cx + size * 0.30, cy + size * 0.48), (cx, cy + size * 0.60),
           (cx - size * 0.30, cy + size * 0.48), (cx - size * 0.42, cy - size * 0.02)]
    d.polygon(pts, outline=edge, fill=None)
    inner_pts = [(cx, cy - size * 0.18), (cx + size * 0.18, cy + size * 0.14),
                 (cx, cy + size * 0.42), (cx - size * 0.18, cy + size * 0.14)]
    d.polygon(inner_pts, fill=inner)


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
    inner = [(cx, cy - r * 0.45), (cx + r * 0.45, cy), (cx, cy + r * 0.45), (cx - r * 0.45, cy)]
    d.polygon(inner, fill=color)


def gradient_text(ch, w, h, size, *, baseline=0.88, stroke=1.0, font_path=None):
    """Texto com gradiente vertical e contorno escuro. w/h/size já em pixels de SS."""
    big = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    font = ImageFont.truetype(str(font_path), size)
    d.text((w / 2, h * baseline), ch, font=font, fill=(0, 0, 0, 255),
           anchor="ms", stroke_width=s(stroke), stroke_fill=(*SHADOW, 255))

    mask = Image.new("L", big.size, 0)
    ImageDraw.Draw(mask).text((w / 2, h * baseline), ch, font=font,
                              fill=255, anchor="ms")

    grad = Image.new("RGBA", big.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for y in range(big.height):
        t = y / max(1, big.height - 1)
        col = tuple(int(GOLD_TOP[i] + (GOLD_BOT[i] - GOLD_TOP[i]) * t) for i in range(3))
        gd.line([(0, y), (big.width, y)], fill=(*col, 255))

    big = Image.composite(grad, big, mask)
    return big


def art_background(font_path) -> Image.Image:
    art = Image.open(SRC).convert("RGBA").resize((s(W), s(H)), Image.Resampling.LANCZOS)
    return art


def main() -> int:
    if not SRC.exists():
        sys.exit(f"[art] ausente: {SRC}")
    font_path, _ = ga.resolve_font(None, PROJECT)

    canvas = art_background(font_path)

    # topo
    d = ImageDraw.Draw(canvas)
    f_top = ImageFont.truetype(str(font_path), s(15))
    d.text((s(256), s(42)), "QUA 11 NOV", font=f_top, fill=(*ga.PARCHMENT, 255), anchor="rs")
    ga.diamond(d, s(26), s(37), s(4.5), (*ga.GOLD, 255), width=s(1))
    ga.diamond(d, s(26), s(37), s(1.6), (*ga.GOLD, 255), width=0, fill=(*ga.GOLD, 255))
    d.text((s(38), s(42)), "I", font=f_top, fill=(*ga.GOLD, 255), anchor="ls")

    # hora 10:01 com gradiente
    chars = "10:01"
    widths = [18 if c == ":" else 47 for c in chars]
    total = sum(widths)
    x = s(140) - s(total) / 2
    for ch, w in zip(chars, widths):
        tile = gradient_text(ch, s(w), s(74), s(88), baseline=0.88, font_path=font_path)
        canvas.alpha_composite(tile, (int(x), s(62)))
        x += s(w)

    # banner de passos: ─── ◆ ❖ 3676 ◆ ───
    base_y = s(330)
    f_ban = ImageFont.truetype(str(font_path), s(30))
    num = "3676"
    num_w = f_ban.getlength(num)
    icon = s(15)
    gap = s(7)
    group = icon + gap + num_w
    left = s(140) - group / 2
    right = s(140) + group / 2
    line_y = base_y - s(9)

    d.line([(s(20), line_y), (left - s(17), line_y)], fill=(*DIV, 255), width=s(0.9))
    d.line([(right + s(17), line_y), (s(260), line_y)], fill=(*DIV, 255), width=s(0.9))

    for cx in (left - s(10), right + s(10)):
        ga.diamond(d, cx, line_y, s(3.6), (*ga.GOLD, 255), width=0, fill=(*ga.GOLD, 255))

    ga.diamond(d, left + icon / 2, line_y, s(4.8), (*ga.GOLD, 255), width=s(0.9))
    ga.diamond(d, left + icon / 2, line_y, s(1.7), (*ga.GOLD, 255), width=0, fill=(*ga.GOLD, 255))

    d.text((left + icon + gap, base_y), num, font=f_ban,
           fill=(*ga.GOLD, 255), anchor="ls")

    # barra de stamina
    bar_y = s(333)
    bar_h = s(6)
    x0, x1 = s(45), s(235)
    cham = s(6)
    d.polygon([(x0, bar_y), (x1, bar_y), (x1 - cham, bar_y + bar_h), (x0 + cham, bar_y + bar_h)],
              outline=(*ga.BRONZE_LT, 170), width=s(0.9))
    fill_end = x0 + cham + int((x1 - x0 - cham * 2) * 0.70)
    grad = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(grad)
    for gx in range(x0 + cham, fill_end):
        t = (gx - x0) / max(1, fill_end - x0)
        col = tuple(int(ga.EMBER[i] + (ga.GOLD[i] - ga.EMBER[i]) * t) for i in range(3))
        gd.line([(gx, bar_y + s(1.5)), (gx, bar_y + bar_h - s(1.5))], fill=(*col, 240))
    canvas.alpha_composite(grad)
    for cx in (x0 - s(2), x1 + s(2)):
        ga.diamond(d, cx, bar_y + bar_h / 2, s(3.4), (*ga.GOLD, 255), width=0, fill=(*ga.GOLD, 255))

    # HUD sem rótulos: ícone + número na mesma linha
    f_val = ImageFont.truetype(str(font_path), s(34))
    f_sm = ImageFont.truetype(str(font_path), s(30))
    rows = [
        (360, heart_icon, ("75", 60), None),
        (360, flame_icon, ("289", 190), None),
        (412, sun_icon, ("24°", 60), None),
        (412, energy_icon, ("97%", 190), None),
    ]
    for cy, icon, (text, tx), _ in rows:
        if icon is heart_icon:
            heart_icon(d, s(46), s(cy), s(17), (*ga.EMBER, 255))
        elif icon is flame_icon:
            flame_icon(d, s(176), s(cy), s(17), (*ga.GOLD, 255), (*ga.EMBER, 235))
        elif icon is sun_icon:
            sun_icon(d, s(46), s(cy), s(6.5), (*ga.GOLD, 255))
        else:
            energy_icon(d, s(176), s(cy), s(8), (*ga.GOLD, 255))
        f = f_sm if ("°" in text or "%" in text) else f_val
        d.text((s(tx), s(cy + 12)), text, font=f, fill=(*ga.GOLD, 255), anchor="ls")

    # ornamento central único
    ga.diamond(d, s(140), s(392), s(4.2), (*ga.GOLD, 255), width=s(0.9))
    ga.diamond(d, s(140), s(392), s(1.4), (*ga.GOLD, 255), width=0, fill=(*ga.GOLD, 255))

    face = canvas.resize((W, H), Image.Resampling.LANCZOS)
    face.save(OUT1)
    face.resize((W * 2, H * 2), Image.Resampling.LANCZOS).save(OUT2)
    print(f"[redesign] {OUT1}  +  {OUT2}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


