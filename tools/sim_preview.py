#!/usr/bin/env python3
"""
sim_preview.py — simula o que o relogio desenha, usando os slots do .hwt

    python tools/sim_preview.py out/ARISEN_HUD_v2.hwt --time 9:11

Coordenadas do layout HWHD06 (v2, ancorado a direita):
hora termina em x=127, dois-pontos em 128, minuto termina em 257, topo y=103.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hwformat import image_to_pil, load_package, parse_bin  # noqa: E402

HOUR_END, COLON_X, MIN_END, TOP = 127, 128, 257, 103


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("hwt")
    ap.add_argument("--time", default="9:11")
    ap.add_argument("--values", default=None,
                    help="hr=62,cal=412,temp=24,bat=87 (so desenha, nao vem do layout)")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    path = Path(args.hwt).expanduser()
    pkg = load_package(path)
    info = parse_bin(pkg["bin"])
    imgs = {s["index"]: image_to_pil(s["blob"]) for s in info["images"] if s["size"]}
    bg = imgs.get(1)
    if bg is None:
        sys.exit("slot 1 (fundo) vazio")
    canvas = bg.copy()
    tile_w = imgs[3].width

    hh, mm = args.time.split(":")

    def draw_num(text: str, end_x: int, slot_base: int = 3) -> None:
        x = end_x - tile_w * len(text)
        for ch in text:
            canvas.alpha_composite(imgs[slot_base + int(ch)], (x, TOP))
            x += tile_w

    draw_num(hh, HOUR_END)
    canvas.alpha_composite(imgs[13], (COLON_X, TOP))
    draw_num(mm, MIN_END)

    if args.values:
        vals = dict(kv.split("=") for kv in args.values.split(","))
        vdir = Path(__file__).resolve().parent.parent / "build" / "value"
        tiles = {str(i): Image.open(vdir / f"{i}.png").convert("RGBA") for i in range(10)}

        def num(text: str, x: int, y: int, right: int | None = None) -> None:
            w = sum(tiles[c].width for c in text)
            if right is not None:
                x = right - w
            for c in text:
                canvas.alpha_composite(tiles[c], (x, y))
                x += tiles[c].width

        num(vals.get("hr", "62"), 24, 300)
        num(vals.get("cal", "412"), 152, 300)
        num(vals.get("temp", "24"), 24, 372)
        num(vals.get("bat", "87"), 0, 372, right=246)

    out = Path(args.out) if args.out else path.with_name(path.stem + "_sim.png")
    canvas.save(out)
    print(f"[sim] {out}  (tile {tile_w}px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
