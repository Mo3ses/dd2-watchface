#!/usr/bin/env python3
"""
inspect_hwt.py — abre um .hwt e escreve o inventário de slots

    python tools/inspect_hwt.py base/seed.hwt [--out pasta]

Saída: slots.json, um PNG por imagem e (se houver) o description.xml.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hwformat import FormatError, image_to_pil, load_package, parse_bin, verify_bin  # noqa: E402


def description_fields(xml: bytes | None) -> dict:
    if not xml:
        return {}
    text = xml.decode("utf-8", "replace")
    out = {}
    for key in ("title", "screen", "version", "author", "designer", "font"):
        m = re.search(rf"<{key}>(.*?)</{key}>", text, re.S)
        if m:
            out[key] = m.group(1).strip()
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("seed")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    seed = Path(args.seed).expanduser()
    out = Path(args.out).expanduser() if args.out else seed.parent / (seed.stem + "_slots")
    pkg = load_package(seed)
    info = parse_bin(pkg["bin"])
    desc = description_fields(pkg["description"])

    print(f"[pkg] {seed.name}  container={pkg['container']}  bin={len(pkg['bin'])} B")
    if pkg["entries"]:
        print(f"[pkg] entries: {[i.filename for i, _ in pkg['entries']]}")
    if desc:
        print(f"[pkg] desc: {desc}")
    print(f"[bin] version={info['version']}  layout={len(info['layout'])} B  "
          f"slots={len(info['images'])}  assinatura={info['signature'].hex()}")

    problems = verify_bin(pkg["bin"])
    print(f"[bin] integridade: {'ok' if not problems else problems}")

    out.mkdir(parents=True, exist_ok=True)
    inventory = []
    for img in info["images"]:
        if not img["size"]:
            inventory.append({"index": img["index"], "empty": True})
            continue
        try:
            pil = image_to_pil(img["blob"])
        except FormatError as exc:
            print(f"  [{img['index']:3d}] nao decodifica: {exc}")
            inventory.append({"index": img["index"], "error": str(exc),
                              "bytes": img["size"]})
            continue
        name = f"{img['index']:03d}_{pil.width}x{pil.height}.png"
        pil.save(out / name)
        inventory.append({"index": img["index"], "file": name, "width": pil.width,
                          "height": pil.height, "bytes": img["size"],
                          "sha256": hashlib.sha256(img["blob"]).hexdigest()[:16]})
        print(f"  [{img['index']:3d}] {pil.width:>4}x{pil.height:<4} {img['size']:>8} B  {name}")

    (out / "slots.json").write_text(json.dumps({
        "seed": str(seed), "container": pkg["container"], "description": desc,
        "version": info["version"], "layout_len": len(info["layout"]),
        "signature": info["signature"].hex(), "slots": inventory,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    if pkg["description"]:
        (out / "description.xml").write_bytes(pkg["description"])
    print(f"[out] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
