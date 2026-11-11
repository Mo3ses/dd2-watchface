#!/usr/bin/env python3
"""
selftest.py — prova o codec sem relógio

Monta pacotes sintéticos no formato real (header/layout/tabela/bin), roda
inspect_hwt e pack_hwt por CLI e confere que os pixels voltam idênticos.
Cobre container flat e nested.

    python tools/selftest.py
"""
from __future__ import annotations

import hashlib
import io
import json
import struct
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from PIL import Image

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from hwformat import (build_bin, decode_image, encode_image, parse_bin,  # noqa: E402
                      verify_bin)

ESC_RGBA = (137, 103, 69, 35)


def img(w: int, h: int, colors) -> tuple[bytes, bytes]:
    px = bytearray()
    for y in range(h):
        for x in range(w):
            px += bytes(colors[(x + y) % len(colors)])
    return encode_image(w, h, bytes(px)), bytes(px)


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="hwt-selftest-"))
    a_blob, a_raw = img(6, 4, [(0, 0, 0, 255), (236, 192, 105, 255), ESC_RGBA])
    b_blob, b_raw = img(8, 2, [(0, 0, 0, 255), (217, 56, 30, 255)])
    layout = b"\x08\x01\x12\x04test"
    bin_data = build_bin(2, layout, [a_blob, b_blob])
    assert not verify_bin(bin_data)
    info = parse_bin(bin_data)
    assert info["version"] == 2 and len(info["images"]) == 2
    assert decode_image(info["images"][0]["blob"])[2] == a_raw
    print("[ok] bin: header/tabela/tiling, decode idêntico ao original")

    desc = ('<?xml version="1.0" encoding="UTF-8"?><HwTheme><title>Teste</title>'
            '<screen>HWHD06</screen><version>2.1.1</version></HwTheme>')

    flat = tmp / "flat.hwt"
    with zipfile.ZipFile(flat, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("com.huawei.watchface", bin_data)
        z.writestr("description.xml", desc)

    inner = io.BytesIO()
    with zipfile.ZipFile(inner, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("watchface.bin", bin_data)
    nested = tmp / "nested.hwt"
    with zipfile.ZipFile(nested, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("com.huawei.watchface", inner.getvalue())
        z.writestr("description.xml", desc)

    for seed in (flat, nested):
        r = subprocess.run([sys.executable, str(TOOLS / "inspect_hwt.py"), str(seed)],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        inv = json.loads((tmp / f"{seed.stem}_slots" / "slots.json").read_text(encoding="utf-8"))
        assert len(inv["slots"]) == 2, inv
        print(f"[ok] inspect_hwt: {seed.name} ({inv['container']})")

    new = Image.new("RGBA", (6, 4), (0, 0, 0, 255))
    new.putpixel((1, 1), (236, 192, 105, 255))
    build = tmp / "build"
    build.mkdir()
    new.save(build / "bg.png")
    slotmap = tmp / "slotmap.json"
    slotmap.write_text(json.dumps({"slots": {"0": "bg.png"}}), encoding="utf-8")

    out = tmp / "out.hwt"
    r = subprocess.run([sys.executable, str(TOOLS / "pack_hwt.py"),
                        "--seed", str(nested), "--map", str(slotmap),
                        "--build", str(build), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    print("[ok] pack_hwt: nested reescrito")

    with zipfile.ZipFile(out) as z:
        blob = z.read("com.huawei.watchface")
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        final = z.read("watchface.bin")
    parsed = parse_bin(final)
    assert not verify_bin(final)
    assert decode_image(parsed["images"][0]["blob"])[2] == new.tobytes()
    assert parsed["images"][1]["blob"] == b_blob
    assert hashlib.sha256(parsed["layout"]).digest() == hashlib.sha256(layout).digest()
    print("[ok] round-trip: slot trocado, slot intocado, layout preservado")
    print(f"[ok] artefatos em {tmp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
