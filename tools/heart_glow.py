#!/usr/bin/env python3
"""
heart_glow.py — frames de brilho (overlay) para o coracao, sem duplicar a arte

    python tools/heart_glow.py
    python tools/heart_glow.py --gif out/v9_face.png

Cada frame e so o bloom das rachaduras em laranja, com alpha proporcional ao
pulso. O fundo mantem o coracao estatico: se a animacao nao rodar, a face
continua identica ao v9; se rodar, o coracao acende.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

PROJECT = Path(__file__).resolve().parent.parent
BOX = (55, 120, 245, 300)
FRAMES = 10
DURATION = 90
WARM = (255, 106, 0)


def ember_mask(crop: Image.Image) -> Image.Image:
    px = crop.load()
    mask = Image.new("L", crop.size, 0)
    mp = mask.load()
    for y in range(crop.height):
        for x in range(crop.width):
            r, g, b = px[x, y][:3]
            if r > 80 and r > g * 1.25 and r > b * 1.15:
                mp[x, y] = min(255, int((r - 70) * 2.6))
    return mask


def feather_mask(size: tuple[int, int]) -> Image.Image:
    w, h = size
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle([6, 6, w - 7, h - 7], radius=26, fill=255)
    return m.filter(ImageFilter.GaussianBlur(10))


def make_frames(bg_path: Path, build: Path) -> list[Path]:
    bg = Image.open(bg_path).convert("RGB")
    crop = bg.crop(BOX)
    mask = ember_mask(crop)
    core = mask.filter(ImageFilter.GaussianBlur(2))
    bloom = mask.filter(ImageFilter.GaussianBlur(9))
    feather = feather_mask(crop.size)

    out = build / "heart_glow"
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for i in range(FRAMES):
        k = math.sin(math.pi * i / (FRAMES - 1))
        a = ImageChops.add(core.point(lambda v: int(v * 0.80 * k)),
                           bloom.point(lambda v: int(v * 0.45 * k)))
        a = ImageChops.multiply(a, feather)
        frame = Image.new("RGBA", crop.size, (*WARM, 0))
        frame.putalpha(a)
        p = out / f"glow_{i:02d}.png"
        frame.save(p)
        paths.append(p)
    return paths


def make_gif(face_path: Path, frames: list[Path], dest: Path) -> None:
    face = Image.open(face_path).convert("RGBA")
    seq = list(range(FRAMES)) + list(range(FRAMES - 2, 0, -1))
    imgs = []
    for i in seq:
        f = Image.open(frames[i]).convert("RGBA")
        c = face.copy()
        c.alpha_composite(f, (BOX[0], BOX[1]))
        imgs.append(c.convert("RGB"))
    imgs[0].save(dest, save_all=True, append_images=imgs[1:],
                 duration=DURATION, loop=0, optimize=True)
    print(f"[gif] {dest}  ({len(imgs)} quadros)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gif", default=None)
    args = ap.parse_args()
    build = PROJECT / "build"
    bg = build / "bg_relic.png"
    if not bg.exists():
        sys.exit(f"[glow] fundo ausente: {bg}")
    frames = make_frames(bg, build)
    print(f"[glow] {len(frames)} frames em {build / 'heart_glow'}")
    if args.gif:
        out = PROJECT / "out"
        out.mkdir(exist_ok=True)
        make_gif(Path(args.gif).expanduser(), frames, out / "dd2_watchface_pulsing.gif")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
