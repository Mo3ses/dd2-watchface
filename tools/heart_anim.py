#!/usr/bin/env python3
"""
heart_anim.py — frames de pulsacao do coracao + fundo sem o coracao + GIF

    python tools/heart_anim.py
    python tools/heart_anim.py --gif out/v10_face.png

Recorta 190x180 centrado no coracao, gera 10 frames em ping-pong
(brilho de brasa + micro-escala 1.00..1.03 + fagulhas), apaga o coracao do
fundo com mascara suave e monta o GIF sobre a face renderizada.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

PROJECT = Path(__file__).resolve().parent.parent
BOX = (55, 120, 245, 300)          # x0, y0, x1, y1
FRAMES = 10
DURATION = 90                       # ms por quadro no GIF


def ember_mask(crop: Image.Image) -> Image.Image:
    px = crop.load()
    mask = Image.new("L", crop.size, 0)
    mp = mask.load()
    for y in range(crop.height):
        for x in range(crop.width):
            r, g, b = px[x, y][:3]
            if r > 80 and r > g * 1.25 and r > b * 1.15:
                mp[x, y] = min(255, int((r - 80) * 2.4))
    return mask


def feather_mask(size: tuple[int, int]) -> Image.Image:
    w, h = size
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([6, 6, w - 7, h - 7], radius=26, fill=255)
    return mask.filter(ImageFilter.GaussianBlur(10))


def make_frames(bg_path: Path, build: Path) -> tuple[list[Path], Image.Image]:
    bg = Image.open(bg_path).convert("RGB")
    crop = bg.crop(BOX).convert("RGBA")
    base = crop.copy()
    mask = ember_mask(crop)
    bloom = mask.filter(ImageFilter.GaussianBlur(3))
    feather = feather_mask(crop.size)

    out = build / "heart"
    out.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    w, h = crop.size

    for i in range(FRAMES):
        k = math.sin(math.pi * i / (FRAMES - 1))       # 0 -> 1 -> 0
        scale = 1.0 + 0.03 * k
        scaled = base.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
        left = (scaled.width - w) // 2
        top = (scaled.height - h) // 2
        frame = scaled.crop((left, top, left + w, top + h))

        if k > 0.01:
            frame = ImageEnhance.Brightness(frame).enhance(1.0 + 0.45 * k)
            frame = ImageEnhance.Color(frame).enhance(1.0 + 0.55 * k)
            glow = Image.new("RGBA", frame.size, (255, 106, 0, 0))
            glow.putalpha(bloom.point(lambda v: int(v * 0.85 * k)))
            frame = Image.alpha_composite(frame, glow)

        frame.putalpha(feather)
        p = out / f"heart_{i:02d}.png"
        frame.save(p)
        paths.append(p)

    # fundo sem o coracao, com borda suave
    patch = Image.new("RGBA", (w, h), (0, 0, 0, 255))
    patch.putalpha(feather)
    bg_rgba = bg.convert("RGBA")
    bg_rgba.paste(patch, (BOX[0], BOX[1]), feather)
    bg_rgba.convert("RGB").save(build / "bg_relic_anim.png")
    return paths, bg_rgba


def make_gif(face_path: Path, frames: list[Path], dest: Path) -> None:
    face = Image.open(face_path).convert("RGBA")
    seq = list(range(FRAMES)) + list(range(FRAMES - 2, 0, -1))
    gif_frames = []
    for i in seq:
        f = Image.open(frames[i]).convert("RGBA")
        canvas = face.copy()
        canvas.alpha_composite(f, (BOX[0], BOX[1]))
        gif_frames.append(canvas.convert("RGB"))
    gif_frames[0].save(dest, save_all=True, append_images=gif_frames[1:],
                       duration=DURATION, loop=0, optimize=True)
    print(f"[gif] {dest}  ({len(gif_frames)} quadros)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gif", default=None)
    args = ap.parse_args()

    build = PROJECT / "build"
    bg = build / "bg_relic.png"
    if not bg.exists():
        sys.exit(f"[anim] fundo ausente: {bg} (rode tools/artbg_relic.py)")
    frames, _ = make_frames(bg, build)
    print(f"[anim] {len(frames)} frames em {build / 'heart'}  + bg_relic_anim.png")

    if args.gif:
        out = PROJECT / "out"
        out.mkdir(exist_ok=True)
        make_gif(Path(args.gif).expanduser(), frames, out / "dd2_watchface_pulsing.gif")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
