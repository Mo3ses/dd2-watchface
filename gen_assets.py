#!/usr/bin/env python3
"""
gen_assets.py — ARISEN HUD · rice Dragon's Dogma 2
Alvo: HUAWEI WATCH FIT Special Edition (STA-B39) · HarmonyOS 2.1 · AMOLED 280x456

Gera todos os sprites estaticos, os atlas de digitos, os conjuntos de
palavras (dia/mes pt-BR), o preview composto e o manifest de montagem.

Nada de texto dinamico e assado no fundo: hora, data e as quatro leituras
viram sprites com posicao declarada no manifest, para binding no Theme
Studio (ou, no caminho sem GUI, no tools/pack_hwt.py).

Uso:
    python gen_assets.py                 # build/ ao lado do script
    python gen_assets.py --font C:/.../TerminessNerdFontMono-Bold.ttf
    python gen_assets.py --strict        # falha se preto puro < 80%
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

# --------------------------------------------------------------------------
# spec
# --------------------------------------------------------------------------
W, H = 280, 456
SS = 3                      # supersampling de formas; texto tambem sobe e volta

GOLD      = (0xEC, 0xC0, 0x69)   # ouro velho
EMBER     = (0xD9, 0x38, 0x1E)   # brasa viva
BRONZE    = (0x4A, 0x35, 0x25)   # bronze oxidado
PARCHMENT = (0xE6, 0xDA, 0xC8)   # pergaminho
BRONZE_LT = (0xC8, 0x9B, 0x52)   # bronze claro
BLACK     = (0x00, 0x00, 0x00)
GLOW_HOT  = (0x4A, 0x18, 0x10)
GLOW_COOL = (0x24, 0x10, 0x0C)
AOD_GOLD  = (0x8A, 0x6F, 0x3D)

# geometria (px logicos)
FRAME_OUT   = (8, 8, 271, 447)
FRAME_IN    = (13, 13, 266, 442)
HEADER_Y    = 56
HEADER_BASE = 40
GRID_TOP    = 274
GRID_MID    = 357
GRID_BOT    = 436
GRID_X      = 140
COL_L, COL_R = 24, 152
LABEL_BASE = (296, 379)
VALUE_BASE = (338, 417)
TIME_BASE   = 176
ORN_Y       = 204
TIME_MAX_W  = 236

WEEKDAYS = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SAB"]
MONTHS = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN",
          "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]

PREVIEW = {"time": "23:47", "weekday": "QUA", "day": "11", "month": "NOV",
           "heart": "62", "calorie": "412", "temp": "24", "battery": "87"}


# --------------------------------------------------------------------------
# fonte
# --------------------------------------------------------------------------
FONT_HINTS = [
    "TerminessNerdFontMono-Bold.ttf",
    "TerminessNerdFontMono-Regular.ttf",
    "TerminessNerdFontMono-BoldItalic.ttf",
    "TerminessNerdFontMono-Italic.ttf",
]
SYSTEM_FONT_DIRS = [
    Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts",
    Path(os.environ.get("WINDIR", r"C:/Windows")) / "Fonts",
]
FALLBACK = ["CascadiaMono.ttf", "consolab.ttf", "consola.ttf", "DejaVuSansMono-Bold.ttf"]


def resolve_font(explicit: str | None, project: Path) -> tuple[Path, bool]:
    """Devolve (caminho, is_terminess)."""
    if explicit:
        p = Path(explicit).expanduser()
        if not p.exists():
            sys.exit(f"[font] nao encontrei: {p}")
        return p, "erminess" in p.name.lower()

    local = sorted((project / "fonts").glob("*.ttf")) + sorted((project / "fonts").glob("*.otf"))
    for p in local:
        if "erminess" in p.name.lower():
            if "bold" in p.name.lower():
                return p, True
    for p in local:
        if "erminess" in p.name.lower():
            return p, True

    for d in SYSTEM_FONT_DIRS:
        if not d.is_dir():
            continue
        for hint in FONT_HINTS:
            p = d / hint
            if p.exists():
                return p, True

    for d in SYSTEM_FONT_DIRS:
        if not d.is_dir():
            continue
        for hint in FALLBACK:
            p = d / hint
            if p.exists():
                print(f"[font] Terminess ausente - geometria provisoria com {p.name}", file=sys.stderr)
                print(f"[font] jogue o TTF em {project / 'fonts'} e rode de novo.", file=sys.stderr)
                return p, False

    sys.exit("[font] nenhuma fonte mono encontrada; passe --font CAMINHO.ttf")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def S(v: float) -> int:
    return int(round(v * SS))


def rgba(c, a=255):
    return (c[0], c[1], c[2], a)


def layer(canvas):
    lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    return lay, ImageDraw.Draw(lay)


def diamond(d: ImageDraw.ImageDraw, cx, cy, r, color, width=1, fill=None):
    pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    if fill:
        d.polygon(pts, fill=fill)
    if width:
        d.line(pts + [pts[0]], fill=color, width=width, joint="curve")


def heart(d: ImageDraw.ImageDraw, cx, cy, size, color):
    # curva cardiaca parametrica: arestas limpas em 15-16 px
    pts = []
    for i in range(144):
        t = math.tau * i / 144
        x = 16 * math.sin(t) ** 3
        y = (13 * math.cos(t) - 5 * math.cos(2 * t)
             - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * size / 33.0, cy - y * size / 33.0 - size * 0.06))
    d.polygon(pts, fill=color)


def tracked(d, xy, text, font, fill, tracking=0.0, anchor_y="ls"):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill, anchor=anchor_y)
        x += font.getlength(ch) + tracking
    return x


def tracked_width(text, font, tracking=0.0):
    return sum(font.getlength(c) for c in text) + tracking * max(0, len(text) - 1)


def _blob_mask(canvas, center, radii, alpha_max, power, blur):
    mask = Image.new("L", canvas.size, 0)
    md = ImageDraw.Draw(mask)
    cx, cy = center
    rx, ry = radii
    steps = 64
    for i in range(steps, 0, -1):
        t = i / steps
        a = int(alpha_max * (1.0 - t) ** power)
        if a <= 0:
            continue
        md.ellipse([cx - rx * t, cy - ry * t, cx + rx * t, cy + ry * t], fill=a)
    return mask.filter(ImageFilter.GaussianBlur(blur))


def glow(canvas, center, radii, alpha_max, power=2.4, blur=18):
    # mascara em L, depois colorir: borrar RGBA mistura preto dentro do brilho
    hot = Image.new("RGBA", canvas.size, rgba(GLOW_HOT, 0))
    hot.putalpha(_blob_mask(canvas, center, radii, alpha_max, power, blur))
    canvas.alpha_composite(hot)

    cool = Image.new("RGBA", canvas.size, rgba(GLOW_COOL, 0))
    cool.putalpha(_blob_mask(canvas, center, (radii[0] * 0.46, radii[1] * 0.46),
                             int(alpha_max * 0.9), power * 0.8, blur * 0.8))
    canvas.alpha_composite(cool)


def embers(canvas, center, radii, count=22, seed=1337):
    rng = random.Random(seed)
    lay, d = layer(canvas)
    for _ in range(count):
        ang = rng.uniform(0, math.tau)
        rad = rng.uniform(0.12, 1.0) ** 0.65
        x = center[0] + math.cos(ang) * radii[0] * rad
        y = center[1] + math.sin(ang) * radii[1] * rad
        r = rng.uniform(0.55, 1.45)
        col = GOLD if rng.random() < 0.55 else EMBER
        a = rng.randint(45, 150)
        d.ellipse([x - r, y - r, x + r, y + r], fill=rgba(col, a))
    canvas.alpha_composite(lay)


def frame(canvas, dim=1.0):
    lay, d = layer(canvas)
    d.rectangle([S(FRAME_OUT[0]), S(FRAME_OUT[1]), S(FRAME_OUT[2]), S(FRAME_OUT[3])],
                outline=rgba(BRONZE, int(235 * dim)), width=SS)
    d.rectangle([S(FRAME_IN[0]), S(FRAME_IN[1]), S(FRAME_IN[2]), S(FRAME_IN[3])],
                outline=rgba(BRONZE, int(130 * dim)), width=SS)

    # cantos: losango + duas hastes
    for cx, cy, dx, dy in [(FRAME_IN[0], FRAME_IN[1], 1, 1),
                           (FRAME_IN[2], FRAME_IN[1], -1, 1),
                           (FRAME_IN[0], FRAME_IN[3], 1, -1),
                           (FRAME_IN[2], FRAME_IN[3], -1, -1)]:
        diamond(d, S(cx), S(cy), S(4.2), rgba(BRONZE_LT, int(190 * dim)), width=SS)
        d.line([(S(cx + dx * 8), S(cy)), (S(cx + dx * 16), S(cy))],
               fill=rgba(BRONZE_LT, int(150 * dim)), width=SS)
        d.line([(S(cx), S(cy + dy * 8)), (S(cx), S(cy + dy * 16))],
               fill=rgba(BRONZE_LT, int(150 * dim)), width=SS)

    # ticks laterais, marca de inventario
    for y in range(84, 356, 16):
        d.line([(S(9.5), S(y)), (S(11.5), S(y))], fill=rgba(BRONZE_LT, int(90 * dim)), width=SS)
        d.line([(S(W - 11.5), S(y)), (S(W - 9.5), S(y))], fill=rgba(BRONZE_LT, int(90 * dim)), width=SS)

    canvas.alpha_composite(lay)


def rules(canvas):
    lay, d = layer(canvas)
    for y, a in ((HEADER_Y, 210), (GRID_TOP, 200), (GRID_MID, 180), (GRID_BOT, 120)):
        d.line([(S(16), S(y)), (S(W - 16), S(y))], fill=rgba(BRONZE, a), width=SS)
    d.line([(S(GRID_X), S(GRID_TOP)), (S(GRID_X), S(GRID_BOT))], fill=rgba(BRONZE, 180), width=SS)

    # nos de losango nos cruzamentos
    diamond(d, S(GRID_X), S(HEADER_Y), S(3.2), rgba(BRONZE, 170), width=SS, fill=(0, 0, 0, 0))
    diamond(d, S(GRID_X), S(GRID_MID), S(3.6), rgba(BRONZE_LT, 200), width=SS, fill=rgba(BLACK, 255))
    canvas.alpha_composite(lay)


def static_labels(canvas, font_path: Path):
    lay, d = layer(canvas)
    f_lab = ImageFont.truetype(str(font_path), S(11.5))
    f_unit = ImageFont.truetype(str(font_path), S(12.5))

    tracked(d, (S(COL_R), S(LABEL_BASE[0])), "CAL", f_lab, rgba(BRONZE_LT, 255), S(1.4))
    tracked(d, (S(COL_L), S(LABEL_BASE[1])), "\u00b0C", f_lab, rgba(BRONZE_LT, 255), S(1.4))
    tracked(d, (S(COL_R), S(LABEL_BASE[1])), "BAT", f_lab, rgba(BRONZE_LT, 255), S(1.4))
    d.text((S(252), S(VALUE_BASE[1])), "%", font=f_unit, fill=rgba(BRONZE_LT, 255), anchor="ls")

    # coracao da celula superior esquerda
    heart(d, S(COL_L + 9), S(LABEL_BASE[0] - 5), S(16), rgba(EMBER, 255))

    canvas.alpha_composite(lay)


def time_ornament(canvas):
    lay, d = layer(canvas)
    d.line([(S(96), S(ORN_Y)), (S(126), S(ORN_Y))], fill=rgba(BRONZE, 220), width=SS)
    d.line([(S(154), S(ORN_Y)), (S(184), S(ORN_Y))], fill=rgba(BRONZE, 220), width=SS)
    diamond(d, S(140), S(ORN_Y), S(5.4), rgba(GOLD, 230), width=SS)
    diamond(d, S(140), S(ORN_Y), S(2.0), rgba(GOLD, 200), width=0, fill=rgba(GOLD, 220))
    canvas.alpha_composite(lay)


def ornament_glyph(canvas, cx, cy, r):
    """O glifo do cabecalho: losango vazado com nucleo."""
    lay, d = layer(canvas)
    diamond(d, S(cx), S(cy), S(r), rgba(GOLD, 255), width=SS)
    diamond(d, S(cx), S(cy), S(r * 0.34), None, width=0, fill=rgba(GOLD, 255))
    canvas.alpha_composite(lay)


# --------------------------------------------------------------------------
# atlas de digitos
# --------------------------------------------------------------------------
def digit_atlas(font_path: Path, size: int, color, chars: str, out_dir: Path,
                pad: int = 2, names: dict | None = None) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    f = ImageFont.truetype(str(font_path), size * SS)
    adv = f.getlength("0")
    asc, desc = f.getmetrics()
    tw = int(round(adv)) + pad * 2 * SS
    th = asc + desc
    meta = {"size": size, "tile": [int(round(tw / SS)), int(round(th / SS))],
            "advance": round(adv / SS, 3)}
    names = names or {}
    for ch in chars:
        img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.text((pad * SS, asc), ch, font=f, fill=rgba(color, 255), anchor="ls")
        img = img.resize((int(round(tw / SS)), int(round(th / SS))), Image.Resampling.LANCZOS)
        name = names.get(ch, {"0": "0", "1": "1", "2": "2", "3": "3", "4": "4",
                              "5": "5", "6": "6", "7": "7", "8": "8", "9": "9",
                              ":": "colon", "-": "minus", "/": "slash", "%": "percent",
                              "\u00b0": "degree"}.get(ch, f"u{ord(ch):04x}"))
        img.save(out_dir / f"{name}.png")
    return meta


def word_set(font_path: Path, size: int, color, words: list[str], prefix: str, out_dir: Path,
             pad: int = 2) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    f = ImageFont.truetype(str(font_path), size * SS)
    asc, desc = f.getmetrics()
    th = asc + desc
    widths = []
    for w in words:
        tw = int(round(f.getlength(w))) + pad * 2 * SS
        img = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
        ImageDraw.Draw(img).text((pad * SS, asc), w, font=f, fill=rgba(color, 255), anchor="ls")
        img.resize((int(round(tw / SS)), int(round(th / SS))), Image.Resampling.LANCZOS) \
           .save(out_dir / f"{prefix}_{len(widths) + 1:02d}.png")
        widths.append(round(tw / SS, 1))
    return {"size": size, "height": int(round(th / SS)), "widths": widths}


def fit_time_size(font_path: Path, text: str, max_w: int, hi: int = 108, lo: int = 48) -> int:
    s = hi
    while s > lo:
        f = ImageFont.truetype(str(font_path), s * SS)
        if f.getlength(text) <= max_w * SS:
            return s
        s -= 2
    return lo


# --------------------------------------------------------------------------
# composicao
# --------------------------------------------------------------------------
def background(font_path: Path) -> tuple[Image.Image, dict]:
    canvas = Image.new("RGBA", (W * SS, H * SS), rgba(BLACK, 255))
    glow(canvas, (140, 150), (70, 86), alpha_max=96, power=2.6, blur=20)
    embers(canvas, (140, 148), (62, 74), count=18)
    frame(canvas)
    rules(canvas)
    static_labels(canvas, font_path)
    time_ornament(canvas)
    ornament_glyph(canvas, 27, 34, 4.6)

    f_date = ImageFont.truetype(str(font_path), S(15))
    d = ImageDraw.Draw(canvas)
    txt = f"{PREVIEW['weekday']} {PREVIEW['day']} {PREVIEW['month']}"
    d.text((S(W - 24), S(HEADER_BASE)), txt, font=f_date,
           fill=rgba(PARCHMENT, 255), anchor="rs")

    f_i = ImageFont.truetype(str(font_path), S(16))
    d.text((S(38), S(HEADER_BASE + 7)), "I", font=f_i, fill=rgba(GOLD, 255), anchor="ls")

    return canvas


def compose_preview(canvas: Image.Image, font_path: Path, time_size: int) -> Image.Image:
    prev = canvas.copy()
    lay, d = layer(prev)
    f_time = ImageFont.truetype(str(font_path), time_size * SS)
    d.text((S(140), S(TIME_BASE)), PREVIEW["time"], font=f_time,
           fill=rgba(GOLD, 255), anchor="ms")

    f_val = ImageFont.truetype(str(font_path), S(34))
    d.text((S(COL_L), S(VALUE_BASE[0])), PREVIEW["heart"], font=f_val,
           fill=rgba(GOLD, 255), anchor="ls")
    d.text((S(COL_R), S(VALUE_BASE[0])), PREVIEW["calorie"], font=f_val,
           fill=rgba(GOLD, 255), anchor="ls")
    d.text((S(COL_L), S(VALUE_BASE[1])), PREVIEW["temp"], font=f_val,
           fill=rgba(GOLD, 255), anchor="ls")
    bat_w = f_val.getlength(PREVIEW["battery"])
    d.text((S(246) - bat_w, S(VALUE_BASE[1])), PREVIEW["battery"], font=f_val,
           fill=rgba(GOLD, 255), anchor="ls")
    prev.alpha_composite(lay)
    return prev.resize((W, H), Image.Resampling.LANCZOS)


def aod(font_path: Path, time_size: int) -> Image.Image:
    canvas = _aod_base(font_path)
    lay, d = layer(canvas)
    f_time = ImageFont.truetype(str(font_path), time_size * SS)
    d.text((S(140), S(TIME_BASE)), PREVIEW["time"], font=f_time, fill=rgba(AOD_GOLD, 255), anchor="ms")
    f_date = ImageFont.truetype(str(font_path), S(14))
    d.text((S(W - 24), S(HEADER_BASE)), f"{PREVIEW['weekday']} {PREVIEW['day']}",
           font=f_date, fill=rgba(AOD_GOLD, 190), anchor="rs")
    canvas.alpha_composite(lay)
    return canvas.resize((W, H), Image.Resampling.LANCZOS)


def _aod_base(font_path: Path) -> Image.Image:
    canvas = Image.new("RGBA", (W * SS, H * SS), rgba(BLACK, 255))
    frame(canvas, dim=0.45)
    lay, d = layer(canvas)
    d.line([(S(16), S(HEADER_Y)), (S(W - 16), S(HEADER_Y))], fill=rgba(BRONZE, 90), width=SS)
    canvas.alpha_composite(lay)
    return canvas


def aod_plain(font_path: Path) -> Image.Image:
    """Fundo de AOD sem hora: o relogio desenha os digitos por cima."""
    return _aod_base(font_path).resize((W, H), Image.Resampling.LANCZOS)


def black_ratio(img: Image.Image) -> float:
    data = img.convert("RGB").tobytes()
    black = sum(1 for i in range(0, len(data), 3)
                if data[i] == 0 and data[i + 1] == 0 and data[i + 2] == 0)
    return black / (img.width * img.height)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--font", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--strict", action="store_true", help="exigir >=80%% de preto puro")
    args = ap.parse_args()

    project = Path(__file__).resolve().parent
    out = Path(args.out).expanduser() if args.out else project / "build"
    out.mkdir(parents=True, exist_ok=True)

    font_path, is_term = resolve_font(args.font, project)
    print(f"[font] {font_path}  (terminess={is_term})")

    bg_canvas = background(font_path)
    time_size = fit_time_size(font_path, PREVIEW["time"], TIME_MAX_W)
    print(f"[layout] hora em {time_size}px")

    bg = bg_canvas.resize((W, H), Image.Resampling.LANCZOS)
    bg.save(out / "bg.png")

    aod_img = aod(font_path, time_size)
    aod_img.save(out / "bg_aod.png")
    aod_plain(font_path).save(out / "bg_aod_plain.png")

    preview = compose_preview(bg_canvas, font_path, time_size)
    preview.save(out / "preview.png")

    time_meta = digit_atlas(font_path, time_size, GOLD, "0123456789:", out / "time")
    value_meta = digit_atlas(font_path, 34, GOLD, "0123456789-", out / "value")
    date_meta = digit_atlas(font_path, 15, PARCHMENT, "0123456789", out / "date")
    aod_meta = digit_atlas(font_path, time_size, AOD_GOLD, "0123456789:", out / "time_aod")

    wd_meta = word_set(font_path, 15, PARCHMENT, WEEKDAYS, "wd", out / "words")
    mo_meta = word_set(font_path, 15, PARCHMENT, MONTHS, "mo", out / "words")

    # icones avulsos
    ico = Image.new("RGBA", (S(22), S(22)), rgba(BLACK, 0))
    heart(ImageDraw.Draw(ico), S(11), S(10), S(16), rgba(EMBER, 255))
    ico.resize((22, 22), Image.Resampling.LANCZOS).save(out / "icon_heart.png")

    ratio = black_ratio(bg)
    print(f"[pixel] preto puro: {ratio * 100:.2f}%  (alvo >= 80%)")

    manifest = {
        "face": "ARISEN HUD",
        "device": "HUAWEI WATCH FIT Special Edition (STA-B39)",
        "os": "HarmonyOS 2.1",
        "resolution": [W, H],
        "palette": {
            "gold": "#ecc069", "ember": "#d9381e", "bronze": "#4a3525",
            "parchment": "#e6dac8", "bronze_light": "#c89b52", "black": "#000000",
        },
        "font": {"file": font_path.name, "is_terminess": is_term},
        "time": {"size": time_size, "baseline_y": TIME_BASE, "center_x": 140,
                 "atlas": "time/", "meta": time_meta},
        "value_font": {"size": 34, "atlas": "value/", "meta": value_meta},
        "date": {"size": 15, "baseline_y": HEADER_BASE, "right_x": W - 24,
                 "digits": date_meta, "weekdays": wd_meta, "months": mo_meta,
                 "weekday_order": WEEKDAYS, "month_order": MONTHS},
        "cells": {
            "heart":  {"icon": "icon_heart.png", "label": None, "column": 0, "row": 0,
                       "value_baseline_y": VALUE_BASE[0], "x": COL_L, "value_type": "heart_rate"},
            "calorie": {"label": "CAL", "column": 1, "row": 0,
                        "value_baseline_y": VALUE_BASE[0], "x": COL_R, "value_type": "calorie"},
            "temp":   {"label": "\u00b0C", "column": 0, "row": 1,
                       "value_baseline_y": VALUE_BASE[1], "x": COL_L, "value_type": "temperature",
                       "fallback": "--"},
            "battery": {"label": "BAT", "column": 1, "row": 1,
                        "value_baseline_y": VALUE_BASE[1], "right_x": 247,
                        "suffix": "%", "value_type": "battery_level"},
        },
        "frames": {"outer": FRAME_OUT, "inner": FRAME_IN,
                   "header_y": HEADER_Y, "grid_top": GRID_TOP,
                   "grid_mid": GRID_MID, "grid_bottom": GRID_BOT, "grid_x": GRID_X},
        "preview_values": PREVIEW,
        "pixel_black_ratio": round(ratio, 4),
        "notes": [
            "hora/data/valores NAO estao assados no bg.png: viram controles dinamicos.",
            "temperature vem do clima sincronizado pelo celular; sem sync mostra --.",
        ],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[out] {out}")
    print(f"      bg.png  bg_aod.png  preview.png  manifest.json + {len(list(out.rglob('*.png')))} sprites")

    if args.strict and ratio < 0.80:
        print("[pixel] FALHOU: abaixo de 80% de preto puro", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
