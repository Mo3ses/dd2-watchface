#!/usr/bin/env python3
"""
sim_preview.py — simula o que o relógio desenha, usando os slots do .hwt

    python tools/sim_preview.py out/ARISEN_HUD_v5.hwt --time 9:11 \
        --values "hr=62,cal=412,temp=24,bat=87,steps=8420"

Coordenadas do layout final (v5):
hora termina em 131, dois-pontos em 131, minuto começa em 149, topo y=68.
Valores: BPM/CAL em y=310 (centros 75/205), TEMP/BAT em y=382 (75/214),
passos centrados em 140, y=250.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hwformat import image_to_pil, load_package, parse_bin  # noqa: E402

HOUR_END, COLON_X, MIN_X, TOP = 131, 131, 149, 68
ROW1, ROW2 = 334, 406
BAT_X, STEPS_Y = 222, 266
STEPS_Y = 250


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("hwt")
    ap.add_argument("--time", default="9:11")
    ap.add_argument("--split-hour", action="store_true",
                    help="hora em dois controles (dezena 59 + unidade 60), sempre 09")
    ap.add_argument("--values", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    path = Path(args.hwt).expanduser()
    pkg = load_package(path)
    info = parse_bin(pkg["bin"])
    imgs = {s["index"]: image_to_pil(s["blob"]) for s in info["images"] if s["size"]}
    canvas = imgs[1].copy()
    tile_w = imgs[3].width

    hh, mm = args.time.split(":")

    def digits(text: str, x: int, y: int, tiles: dict[str, Image.Image]) -> int:
        for ch in text:
            canvas.alpha_composite(tiles[ch], (x, y))
            x += tiles[ch].width
        return x

    hour_tiles = {str(i): imgs[3 + i] for i in range(10)}
    if args.split_hour:
        hh = hh.zfill(2)
        digits(hh[:1], 37, TOP, hour_tiles)
        digits(hh[1:], 84, TOP, hour_tiles)
    else:
        digits(hh, HOUR_END - tile_w * len(hh), TOP, hour_tiles)
    canvas.alpha_composite(imgs[13], (COLON_X, TOP))
    digits(mm, MIN_X, TOP, hour_tiles)

    if args.values:
        vals = dict(kv.split("=") for kv in args.values.split(","))
        vdir = Path(__file__).resolve().parent.parent / "build" / "value"
        vt = {str(i): Image.open(vdir / f"{i}.png").convert("RGBA") for i in range(10)}
        th = vt["0"].height

        def center(text: str, cx: int, y: int, tiles=None) -> None:
            tiles = tiles or vt
            h = tiles["0"].height
            w = sum(tiles[c].width for c in text)
            digits(text, cx - w // 2, y - h // 2, tiles)

        def right(text: str, x: int, y: int) -> None:
            w = sum(vt[c].width for c in text)
            digits(text, x - w, y, vt)

        if vals.get("hr"):
            center(vals["hr"], 75, ROW1)
        if vals.get("cal"):
            center(vals["cal"], 205, ROW1)
        if vals.get("temp"):
            center(vals["temp"], 75, ROW2)
        if vals.get("bat"):
            right(vals["bat"], BAT_X, ROW2 - 20)

        if vals.get("steps"):
            bdir = Path(__file__).resolve().parent.parent / "build" / "tiles_v5_banner"
            if bdir.exists():
                bt = {str(i): Image.open(bdir / f"{i}.png").convert("RGBA") for i in range(10)}
                center(vals["steps"], 140, STEPS_Y, bt)

    out = Path(args.out) if args.out else path.with_name(path.stem + "_sim.png")
    canvas.save(out)
    print(f"[sim] {out}  (tile {tile_w}px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
