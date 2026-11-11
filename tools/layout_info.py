#!/usr/bin/env python3
"""layout_info.py — resumo legível do layout de um .hwt"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout as L  # noqa: E402
from hwformat import load_package, parse_bin  # noqa: E402

LABELS = {0: "BACKGROUND", 1: "TIME", 2: "DATE", 3: "WIDGET", 4: "COMPLICATION"}
DRAW = {0: "text", 1: "single", 2: "selected", 3: "combined", 5: "hand", 6: "line",
        7: "arc", 10: "text2", 13: "arc_text"}


def layer_info(lf: list) -> str:
    draw = L.get_int(lf, 2)
    body_num = {0: 3, 1: 4, 2: 5, 3: 6, 5: 8, 6: 9, 7: 10, 10: 11, 13: 12}.get(draw)
    body = L.get(lf, body_num) if body_num else None
    bits = [f"idx={L.get_int(lf, 1)}", DRAW.get(draw, str(draw))]
    if body:
        bf = L.read(body[2])
        vt = L.get(bf, 5)
        if vt is None:
            vt = L.get(bf, 6)
        if vt is None:
            vt = L.get(bf, 3)
        if vt is not None and isinstance(vt[2], int):
            bits.append(f"vt={vt[2]}")
        idx = L.get_int(lf, 1)
        pos = L.get(bf, 3) or L.get(bf, 2)
        if pos and pos[1] == 2:
            p = L.read(pos[2])
            bits.append(f"pos=({L.get_int(p,1)},{L.get_int(p,2)})")
        al = L.get(bf, 4)
        if al:
            bits.append(f"align={al[2]}")
        amb = L.get(bf, 13) or L.get(bf, 5)
        if amb:
            bits.append(f"amb={amb[2]}")
        n = len([f for f in bf if f[0] == 1])
        bits.append(f"imgs={n}")
    return " ".join(bits)


def main() -> int:
    pkg = load_package(Path(sys.argv[1]).expanduser())
    info = parse_bin(pkg["bin"])
    root = L.read(info["layout"])
    for i, elem in enumerate(f for f in root if f[0] == 1):
        ef = L.read(elem[2])
        label = L.get_int(ef, 1)
        layers = [L.read(f[2]) for f in ef if f[0] == 5]
        conts = [L.read(f[2]) for f in ef if f[0] == 8]
        print(f"element {i}: label={label} ({LABELS.get(label, '?')}) "
              f"layers={len(layers)} containers={len(conts)}")
        for lf in layers:
            print(f"   layer {layer_info(lf)}")
        for c in conts:
            print(f"   container idx={L.get_int(c,1)} data_type={L.get_int(c,8)} "
                  f"layers={len([f for f in c if f[0]==6])}")
            for lf in (L.read(f[2]) for f in c if f[0] == 6):
                print(f"      layer {layer_info(lf)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
