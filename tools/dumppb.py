#!/usr/bin/env python3
"""
dumppb.py — despeja a árvore protobuf do layout de um .hwt

    python tools/dumppb.py base/ref/Donen.hwt [--max-depth 6]

Sem schema: mostra campo/wiretype/valor para mapear a estrutura contra a
documentação do codec (@joyofit/hwt) e montar o nosso layout do zero.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from hwformat import load_package, parse_bin  # noqa: E402


def varint(buf: bytes, i: int) -> tuple[int, int]:
    shift = 0
    value = 0
    while True:
        b = buf[i]
        i += 1
        value |= (b & 0x7F) << shift
        if not b & 0x80:
            return value, i
        shift += 7


def printable(data: bytes) -> str | None:
    if not data or len(data) > 40:
        return None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if all(32 <= ord(c) < 127 for c in text):
        return text
    return None


def dump(buf: bytes, depth: int, max_depth: int, out: list[str], prefix: str = "") -> None:
    i = 0
    n = len(buf)
    while i < n:
        try:
            key, i = varint(buf, i)
        except IndexError:
            out.append(f"{prefix}!! truncado")
            return
        field, wt = key >> 3, key & 7
        if field == 0:
            out.append(f"{prefix}!! field 0")
            return
        if wt == 0:
            value, i = varint(buf, i)
            out.append(f"{prefix}{field}: {value}")
        elif wt == 2:
            length, i = varint(buf, i)
            data = buf[i:i + length]
            i += length
            text = printable(data)
            head = f"{prefix}{field}: len={length}"
            if text is not None:
                out.append(f"{head} \"{text}\"")
            elif depth < max_depth and length:
                out.append(head + " {")
                dump(data, depth + 1, max_depth, out, prefix + "  ")
                out.append(prefix + "}")
            else:
                out.append(head + f" {data[:16].hex()}")
        elif wt == 5:
            data = buf[i:i + 4]
            i += 4
            out.append(f"{prefix}{field}: f32 {data.hex()}")
        elif wt == 1:
            data = buf[i:i + 8]
            i += 8
            out.append(f"{prefix}{field}: f64 {data.hex()}")
        else:
            out.append(f"{prefix}!! wiretype {wt}")
            return


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("seed")
    ap.add_argument("--max-depth", type=int, default=6)
    args = ap.parse_args()
    pkg = load_package(Path(args.seed).expanduser())
    info = parse_bin(pkg["bin"])
    out: list[str] = []
    print(f"[layout] {len(info['layout'])} bytes, version {info['version']}")
    dump(info["layout"], 0, args.max_depth, out)
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
