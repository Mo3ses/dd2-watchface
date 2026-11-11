#!/usr/bin/env python3
"""
mockup.py — põe a face renderizada no corpo de um Watch Fit SE

    python tools/mockup.py out/ARISEN_HUD_v2_sim.png out/preview_device.png

Fundo escuro com brasa, pulseira, caixa polimérica preta, vidro com reflexo.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

SS = 2
W, H = 1000, 1500
FACE_W, FACE_H = 280, 456
SCALE = 2

BG_TOP = (12, 9, 8)
BG_BOT = (5, 4, 4)
STRAP = (26, 21, 18)
STRAP_EDGE = (38, 30, 24)
CASE = (10, 10, 10)
CASE_EDGE = (44, 36, 28)


def gradient(size: tuple[int, int], top, bottom) -> Image.Image:
    w, h = size
    img = Image.new("RGB", (1, h))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        d.point((0, y), tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)))
    return img.resize((w, h), Image.Resampling.BILINEAR)


def main() -> int:
    if len(sys.argv) < 2:
        sys.exit("uso: mockup.py face.png [saida.png]")
    face_path = Path(sys.argv[1]).expanduser()
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else face_path.with_name("preview_device.png")

    face = Image.open(face_path).convert("RGBA")
    face = face.resize((FACE_W * SCALE, FACE_H * SCALE), Image.Resampling.LANCZOS)

    canvas = gradient((W, H), BG_TOP, BG_BOT).convert("RGBA")

    # brilho de brasa atras do relogio
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([W / 2 - 230, 610, W / 2 + 230, 1010], fill=(90, 28, 14, 55))
    canvas.alpha_composite(glow.filter(ImageFilter.GaussianBlur(60)))

    # pulseira
    strap = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(strap)
    sd.rounded_rectangle([W / 2 - 150, 90, W / 2 + 150, H - 90], radius=120, fill=(*STRAP, 255))
    sd.rounded_rectangle([W / 2 - 150, 90, W / 2 + 150, H - 90], radius=120,
                         outline=(*STRAP_EDGE, 255), width=3)
    canvas.alpha_composite(strap)

    # caixa
    case_w, case_h = FACE_W * SCALE + 80, FACE_H * SCALE + 76
    case_box = [W / 2 - case_w / 2, H / 2 - case_h / 2,
                W / 2 + case_w / 2, H / 2 + case_h / 2]
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(case_box, radius=110, fill=(0, 0, 0, 190))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(30)))

    case = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cd = ImageDraw.Draw(case)
    cd.rounded_rectangle(case_box, radius=110, fill=(*CASE, 255))
    cd.rounded_rectangle(case_box, radius=110, outline=(*CASE_EDGE, 255), width=3)
    canvas.alpha_composite(case)

    # tela
    sx = (W - face.width) // 2
    sy = (H - face.height) // 2
    canvas.alpha_composite(face, (sx, sy))

    # vidro: reflexo diagonal suave (alpha por linha, recortado nos cantos)
    glass = Image.new("RGBA", face.size, (0, 0, 0, 0))
    gld = ImageDraw.Draw(glass)
    for i in range(face.height):
        alpha = int(22 * max(0.0, 1 - abs(i - face.height * 0.26) / (face.height * 0.45)))
        gld.line([(0, i), (face.width, i)], fill=(255, 244, 220, alpha))
    mask = Image.new("L", face.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, face.width - 1, face.height - 1],
                                           radius=26, fill=255)
    from PIL import ImageChops
    glass.putalpha(ImageChops.multiply(glass.getchannel("A"), mask))
    canvas.alpha_composite(glass, (sx, sy))

    # botao lateral
    bd = ImageDraw.Draw(canvas)
    bd.rounded_rectangle([case_box[2] - 6, H / 2 - 60, case_box[2] + 14, H / 2 + 60],
                         radius=12, fill=(24, 22, 20, 255))

    canvas.convert("RGB").save(out, quality=95)
    print(f"[mockup] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
