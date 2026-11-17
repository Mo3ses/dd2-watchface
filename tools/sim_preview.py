#!/usr/bin/env python3
"""
sim_preview.py — simula o que o relógio desenha, usando os slots do .hwt

    python tools/sim_preview.py out/ARISEN_HUD_v5.hwt --time 9:11 \
        --values "hr=62,cal=412,temp=24,bat=87,steps=8420"

    python tools/sim_preview.py out/ARISEN_HUD_v13.hwt --v9 \
        --split-hour --split-minute --date 2026-11-17

Coordenadas do layout final (v5):
hora termina em 131, dois-pontos em 131, minuto começa em 149, topo y=68.
Valores: BPM/CAL em y=310 (centros 75/205), TEMP/BAT em y=382 (75/214),
passos centrados em 140, y=250.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout as L  # noqa: E402
from hwformat import image_to_pil, load_package, parse_bin  # noqa: E402

HOUR_END, COLON_X, MIN_X, top = 131, 131, 149, 68
ROW1, ROW2 = 334, 406
BAT_X, STEPS_Y = 222, 266
STEPS_Y = 250


def draw_date(canvas: Image.Image, imgs: dict, root: list, iso: str) -> bool:
    """Desenha o elemento DATE do layout para a data pedida (só camadas normais)."""
    date = dt.date.fromisoformat(iso)
    weekday = date.isoweekday()              # segunda=1 ... domingo=7
    month = date.month
    elem = next((L.read(f[2]) for f in root
                 if f[0] == 1 and L.get_int(L.read(f[2]), 1) == 2), None)
    if elem is None:
        return False
    for lf in (L.read(f[2]) for f in elem if f[0] == 5):
        draw = L.get_int(lf, 2)
        if draw == 2:
            body = L.read(L.get(lf, 5)[2])
            vt = L.get_int(body, 3)
            if L.get_int(body, 6) != 0:
                continue
            refs = [f[2].decode() for f in body if f[0] == 1]
            value = {52: weekday, 51: month}.get(vt)
            if value is None or value >= len(refs):
                continue
            pos = L.read(L.get(body, 2)[2])
            tile = imgs.get(int(refs[value]) - 1)
            if tile:
                canvas.alpha_composite(tile, (L.get_int(pos, 1), L.get_int(pos, 2)))
        elif draw == 3:
            body = L.read(L.get(lf, 6)[2])
            if L.get_int(body, 5) != 17 or L.get_int(body, 13) != 0:
                continue
            refs = [f[2].decode() for f in body if f[0] == 1]
            pos = L.read(L.get(body, 3)[2])
            x, y = L.get_int(pos, 1), L.get_int(pos, 2)
            for ch in str(date.day):
                tile = imgs.get(int(refs[int(ch)]) - 1)
                if not tile:
                    break
                canvas.alpha_composite(tile, (x, y))
                x += tile.width
    return True


def render(info: dict, *, time: str = "10:08", values: dict | None = None,
           v9: bool = False, split_hour: bool = False, split_minute: bool = False,
           date: str | None = None, build: Path | None = None) -> Image.Image:
    """Monta a face 280x456 a partir dos slots do bin, sem passar pelo .hwt."""
    build = build or Path(__file__).resolve().parent.parent / "build"
    imgs = {s["index"]: image_to_pil(s["blob"]) for s in info["images"] if s["size"]}
    canvas = imgs[1].copy()
    tile_w = imgs[3].width

    top_y = 64 if v9 else TOP
    hh, mm = time.split(":")

    def digits(text: str, x: int, y: int, tiles: dict[str, Image.Image]) -> int:
        for ch in text:
            canvas.alpha_composite(tiles[ch], (x, y))
            x += tiles[ch].width
        return x

    hour_tiles = {str(i): imgs[3 + i] for i in range(10)}
    if split_hour:
        hh = hh.zfill(2)
        digits(hh[:1], 37, top_y, hour_tiles)
        digits(hh[1:], 84, top_y, hour_tiles)
    else:
        digits(hh, HOUR_END - tile_w * len(hh), top_y, hour_tiles)
    canvas.alpha_composite(imgs[13], (COLON_X, top_y))
    if split_minute:
        mm = mm.zfill(2)
        digits(mm[:1], 149, top_y, hour_tiles)
        digits(mm[1:], 196, top_y, hour_tiles)
    else:
        digits(mm, MIN_X, top_y, hour_tiles)

    if values:
        vdir = build / "value"
        vt = {str(i): Image.open(vdir / f"{i}.png").convert("RGBA") for i in range(10)}

        def center(text: str, cx: int, y: int, tiles=None) -> None:
            tiles = tiles or vt
            h = tiles["0"].height
            w = sum(tiles[c].width for c in text)
            digits(text, cx - w // 2, y - h // 2, tiles)

        def right(text: str, x: int, y: int) -> None:
            w = sum(vt[c].width for c in text)
            digits(text, x - w, y, vt)

        if v9:
            if values.get("hr"):
                digits(values["hr"], 60, 344, vt)
            if values.get("cal"):
                digits(values["cal"], 190, 344, vt)
            if values.get("temp"):
                digits(values["temp"], 60, 396, vt)
            if values.get("bat"):
                right(values["bat"], 228, 396)
            if values.get("steps"):
                bdir = build / "tiles_v9_banner"
                if bdir.exists():
                    bt = {str(i): Image.open(bdir / f"{i}.png").convert("RGBA")
                          for i in range(10)}
                    digits(values["steps"], 118, 302, bt)
        else:
            if values.get("hr"):
                center(values["hr"], 75, ROW1)
            if values.get("cal"):
                center(values["cal"], 205, ROW1)
            if values.get("temp"):
                center(values["temp"], 75, ROW2)
            if values.get("bat"):
                right(values["bat"], BAT_X, ROW2 - 20)
            if values.get("steps"):
                bdir = build / "tiles_v5_banner"
                if bdir.exists():
                    bt = {str(i): Image.open(bdir / f"{i}.png").convert("RGBA")
                          for i in range(10)}
                    center(values["steps"], 140, STEPS_Y, bt)

    if date:
        root = L.read(info["layout"])
        if not draw_date(canvas, imgs, root, date):
            print("[sim] aviso: layout sem elemento DATE", file=sys.stderr)
    return canvas


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("hwt")
    ap.add_argument("--time", default="9:11")
    ap.add_argument("--split-hour", action="store_true",
                    help="hora em dois controles (dezena 59 + unidade 60), sempre 09")
    ap.add_argument("--split-minute", action="store_true",
                    help="minuto em dois controles (dezena 61 + unidade 62), sempre 01")
    ap.add_argument("--values", default=None)
    ap.add_argument("--v9", action="store_true", help="posicoes do Relic HUD")
    ap.add_argument("--date", default=None,
                    help="AAAA-MM-DD: desenha o elemento DATE do layout")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    path = Path(args.hwt).expanduser()
    pkg = load_package(path)
    info = parse_bin(pkg["bin"])
    values = dict(kv.split("=") for kv in args.values.split(",")) if args.values else None
    canvas = render(info, time=args.time, values=values, v9=args.v9,
                    split_hour=args.split_hour, split_minute=args.split_minute,
                    date=args.date)
    out = Path(args.out) if args.out else path.with_name(path.stem + "_sim.png")
    canvas.save(out)
    tile = next(s for s in info["images"] if s["index"] == 3)
    print(f"[sim] {out}  (tile {image_to_pil(tile['blob']).width}px)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
