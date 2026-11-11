#!/usr/bin/env python3
"""
reencode_check.py — mede o quanto o encoder reproduz bytes de um pacote real

    python tools/reencode_check.py base/ref/SpaceRed.hwt

Se todas as imagens voltarem idênticas com min_run=4, o codec entende o
formato como o fabricante entende. Divergência aponta onde o encoder erra.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hwformat import decode_image, encode_image, load_package, parse_bin  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        sys.exit("uso: reencode_check.py pacote.hwt")
    pkg = load_package(Path(sys.argv[1]).expanduser())
    info = parse_bin(pkg["bin"])
    exact4 = exact2 = total = 0
    for img in info["images"]:
        if not img["size"]:
            continue
        total += 1
        w, h, rgba = decode_image(img["blob"])
        if encode_image(w, h, rgba, min_run=4) == img["blob"]:
            exact4 += 1
            exact2 += 1
        elif encode_image(w, h, rgba, min_run=2) == img["blob"]:
            exact2 += 1
    print(f"[codec] {total} imagens | min_run=4 exato: {exact4} | min_run<=2: {exact2}")
    print("[codec] " + ("formato confirmado" if exact4 == total else
                        f"{total - exact4} imagens divergem"))
    return 0 if exact4 == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
