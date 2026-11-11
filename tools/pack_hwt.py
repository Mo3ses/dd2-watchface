#!/usr/bin/env python3
"""
pack_hwt.py — troca sprites de um .hwt e remonta header/tabela/bin

    python tools/pack_hwt.py --seed base/seed.hwt --suggest
    python tools/pack_hwt.py --seed base/seed.hwt --map spec/slotmap.json

Reescreve layoutLen, tabela (offset/size) e binLen a partir do modelo, entao
trocar imagem por uma de tamanho diferente nao desalinha o pacote.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hwformat import (build_bin, decode_image, load_package, parse_bin,  # noqa: E402
                      pil_to_blob, save_package, verify_bin)


def load_map(map_path: Path, build: Path) -> dict[int, Path]:
    doc = json.loads(map_path.read_text(encoding="utf-8"))
    slots = doc.get("slots", doc)
    result = {}
    for key, value in slots.items():
        if not isinstance(value, str) or not value:
            continue
        p = Path(value)
        if not p.is_absolute():
            p = build / value
        if not p.exists():
            sys.exit(f"[map] slot {key}: arquivo ausente {p}")
        result[int(key)] = p
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", required=True)
    ap.add_argument("--map", default=None)
    ap.add_argument("--build", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--suggest", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    project = Path(__file__).resolve().parent.parent
    build = Path(args.build).expanduser() if args.build else project / "build"
    seed = Path(args.seed).expanduser()
    out = Path(args.out).expanduser() if args.out else project / "out" / "ARISEN_HUD.hwt"

    pkg = load_package(seed)
    info = parse_bin(pkg["bin"])
    print(f"[seed] {len(info['images'])} slots, layout {len(info['layout'])} B")

    if args.suggest or not args.map:
        assets: dict[tuple[int, int], list[str]] = {}
        for p in sorted(build.rglob("*.png")):
            with Image.open(p) as im:
                assets.setdefault(im.size, []).append(str(p.relative_to(build)))
        print("\n[slots]                        [assets de mesma medida]")
        for img in info["images"]:
            if not img["size"]:
                print(f"  {img['index']:3d}  vazio")
                continue
            w = int.from_bytes(img["blob"][4:6], "little")
            h = int.from_bytes(img["blob"][6:8], "little")
            cand = assets.get((w, h), [])
            hint = ", ".join(cand[:6]) + (" ..." if len(cand) > 6 else "")
            print(f"  {img['index']:3d}  {w:>4}x{h:<4}  {hint}")
        print("\nmonte spec/slotmap.json com os indices e rode de novo.")
        return 0

    mapping = load_map(Path(args.map).expanduser(), build)
    unknown = sorted(set(mapping) - {i["index"] for i in info["images"]})
    if unknown:
        sys.exit(f"[map] indices fora do seed: {unknown}")

    blobs: list[bytes] = []
    expected: list[bytes] = []
    for img in info["images"]:
        raw = img["blob"]
        if img["index"] in mapping:
            with Image.open(mapping[img["index"]]) as im:
                im = im.convert("RGBA")
                if img["size"]:
                    old_w, old_h, _ = decode_image(img["blob"])
                    if (im.width, im.height) != (old_w, old_h):
                        print(f"[map] slot {img['index']:3d}: {old_w}x{old_h} -> "
                              f"{im.width}x{im.height} (tamanho muda, layout pode deslocar)")
                raw = pil_to_blob(im)
                expected.append(im.tobytes())
                rel = mapping[img["index"]]
                print(f"[map] slot {img['index']:3d} <- "
                      f"{rel.relative_to(build) if rel.is_relative_to(build) else rel}")
        else:
            expected.append(b"")
        blobs.append(raw)

    new_bin = build_bin(info["version"], info["layout"], blobs,
                        signature=info["signature"], reserved=info["reserved"])
    problems = verify_bin(new_bin)
    if problems:
        sys.exit(f"[verify] {problems}")

    check = parse_bin(new_bin)
    for img, exp in zip(check["images"], expected):
        if not exp:
            continue
        got = decode_image(img["blob"])[2] if img["size"] else b""
        if hashlib.sha256(got).digest() != hashlib.sha256(exp).digest():
            sys.exit(f"[verify] slot {img['index']} nao voltou identico")

    print(f"[bin] {len(pkg['bin'])} -> {len(new_bin)} bytes")
    if args.dry_run:
        print("[dry-run] nada escrito")
        return 0
    save_package(pkg, new_bin, out)
    print(f"[out] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
