#!/usr/bin/env python3
"""
hwformat.py — formato do watchface.bin (lite wearable / HWHD)

Estrutura (16 bytes de header + layout + tabela + bin):

    off  size
    0    u16le version      1 ou 2
    2    u16le layoutLen    bytes do layout (protobuf)
    4    u32le tableLen     8 x numero de imagens
    8    u32le binLen       bytes do fim da tabela ate o EOF
    12   u32le reserved     0
    16   layout[layoutLen]
         table[tableLen]    { u32le offset, u32le size } por imagem
         bin[binLen]        8 bytes de assinatura + imagens em sequencia

Cada imagem: 45 23 88 88 | u16 w | u16 h | pixels BGRA com escape RLE
(89 67 45 23 + BGRA + u32 count). Offsets da tabela contam do inicio do bin,
a primeira imagem comeca em 8.

Fonte do formato: doc do codec @joyofit/hwt (packages/hwt/README.md), verificado
contra amostras reais.
"""
from __future__ import annotations

import io
import struct
import zipfile
from pathlib import Path

from PIL import Image

HDR = struct.Struct("<HHIII")
IMG_MAGIC = b"\x45\x23\x88\x88"
ESC = b"\x89\x67\x45\x23"
SIG_DEFAULT = bytes.fromhex("5555555501000001")


class FormatError(Exception):
    pass


# ---------------------------------------------------------------- imagens
def decode_image(blob: bytes) -> tuple[int, int, bytes]:
    if blob[:4] != IMG_MAGIC:
        raise FormatError(f"magic de imagem desconhecido: {blob[:4].hex()}")
    w = int.from_bytes(blob[4:6], "little")
    h = int.from_bytes(blob[6:8], "little")
    total = w * h
    out = bytearray(total * 4)
    pos = 8
    i = 0
    n_bytes = len(blob)
    while i < total:
        if blob[pos:pos + 4] == ESC:
            pos += 4
            if pos + 8 > n_bytes:
                raise FormatError("escape truncado")
            b, g, r, a = blob[pos:pos + 4]
            pos += 4
            count = int.from_bytes(blob[pos:pos + 4], "little")
            pos += 4
            if count < 1 or i + count > total:
                raise FormatError(f"run invalido: {count}")
            out[i * 4:(i + count) * 4] = bytes((r, g, b, a)) * count
            i += count
        else:
            if pos + 4 > n_bytes:
                raise FormatError("pixel truncado")
            b, g, r, a = blob[pos:pos + 4]
            pos += 4
            out[i * 4:i * 4 + 4] = bytes((r, g, b, a))
            i += 1
    if pos != n_bytes:
        raise FormatError(f"{n_bytes - pos} bytes sobrando na imagem")
    return w, h, bytes(out)


def encode_image(w: int, h: int, rgba: bytes, min_run: int = 4) -> bytes:
    total = w * h
    if len(rgba) != total * 4:
        raise ValueError("buffer RGBA com tamanho errado")
    out = bytearray(IMG_MAGIC + struct.pack("<HH", w, h))
    i = 0
    while i < total:
        r, g, b, a = rgba[i * 4], rgba[i * 4 + 1], rgba[i * 4 + 2], rgba[i * 4 + 3]
        run_rgba = rgba[i * 4:i * 4 + 4]
        j = i + 1
        while j < total and rgba[j * 4:j * 4 + 4] == run_rgba:
            j += 1
        count = j - i
        bgra = bytes((b, g, r, a))
        if count >= min_run or bgra == ESC:
            out += ESC + bgra + struct.pack("<I", count)
        else:
            out += bgra * count
        i = j
    return bytes(out)


def image_to_pil(blob: bytes) -> Image.Image:
    w, h, rgba = decode_image(blob)
    return Image.frombytes("RGBA", (w, h), rgba)


def pil_to_blob(img: Image.Image, min_run: int = 4) -> bytes:
    img = img.convert("RGBA")
    return encode_image(img.width, img.height, img.tobytes(), min_run=min_run)


# ---------------------------------------------------------------- binario
def parse_bin(data: bytes) -> dict:
    if len(data) < 16:
        raise FormatError("binario curto demais")
    version, layout_len, table_len, bin_len, reserved = HDR.unpack_from(data, 0)
    if table_len % 8:
        raise FormatError("tabela nao e multipla de 8")
    off_layout = 16
    off_table = off_layout + layout_len
    off_bin = off_table + table_len
    if off_bin + bin_len != len(data):
        raise FormatError(
            f"tamanhos nao fecham: {off_bin + bin_len} != {len(data)}")
    layout = data[off_layout:off_table]
    table = [struct.unpack_from("<II", data, off_table + 8 * k)
             for k in range(table_len // 8)]
    signature = data[off_bin:off_bin + 8]
    images = []
    for index, (offset, size) in enumerate(table):
        blob = data[off_bin + offset:off_bin + offset + size] if size else b""
        images.append({"index": index, "offset": offset, "size": size, "blob": blob})
    return {"version": version, "layout": layout, "images": images,
            "signature": signature, "reserved": reserved, "size": len(data)}


def build_bin(version: int, layout: bytes, blobs: list[bytes],
              signature: bytes = SIG_DEFAULT, reserved: int = 0) -> bytes:
    table = []
    body = bytearray(signature)
    offset = len(signature)
    for blob in blobs:
        table.append((offset, len(blob)))
        body += blob
        offset += len(blob)
    table_bytes = b"".join(struct.pack("<II", o, s) for o, s in table)
    return HDR.pack(version, len(layout), len(table_bytes), len(body), reserved) \
        + layout + table_bytes + bytes(body)


def verify_bin(data: bytes) -> list[str]:
    """Confere header, tabela e tiling. Devolve lista de problemas."""
    problems: list[str] = []
    try:
        info = parse_bin(data)
    except FormatError as exc:
        return [str(exc)]
    offset = 8
    for img in info["images"]:
        if img["size"] and img["offset"] != offset:
            problems.append(f"slot {img['index']}: offset {img['offset']} != {offset}")
        offset += img["size"]
    if info["signature"][:4] not in (b"\x55\x55\x55\x55", b"\x2e\x2e\x2e\x2e"):
        problems.append(f"assinatura inesperada: {info['signature'].hex()}")
    return problems


# ---------------------------------------------------------------- pacote
def load_package(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            infos = z.infolist()
            entries = [(i, z.read(i.filename)) for i in infos]
            names = [i.filename for i in infos]
            if "com.huawei.watchface" in names:
                blob = dict((i.filename, d) for i, d in entries)["com.huawei.watchface"]
            elif "watchface.bin" in names:
                blob = dict((i.filename, d) for i, d in entries)["watchface.bin"]
            else:
                raise FormatError(f"pacote sem watchface: {names}")
            description = None
            if "description.xml" in names:
                description = dict((i.filename, d) for i, d in entries)["description.xml"]
        container = "nested" if blob[:2] == b"PK" else "flat"
        inner = None
        if container == "nested":
            with zipfile.ZipFile(io.BytesIO(blob)) as z:
                inner = [(i, z.read(i.filename)) for i in z.infolist()]
            bin_bytes = dict((i.filename, d) for i, d in inner)["watchface.bin"]
        else:
            bin_bytes = blob
        return {"path": path, "entries": entries, "container": container,
                "inner": inner, "bin": bin_bytes, "description": description}
    data = path.read_bytes()
    return {"path": path, "entries": None, "container": "raw",
            "inner": None, "bin": data, "description": None}


def save_package(pkg: dict, new_bin: bytes, out: Path,
                 overrides: dict[str, bytes] | None = None) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    overrides = overrides or {}
    if pkg["entries"] is None:
        out.write_bytes(new_bin)
        return
    if pkg["container"] == "nested":
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            for info, data in pkg["inner"]:
                if info.filename == "watchface.bin":
                    data = new_bin
                elif info.filename in overrides:
                    data = overrides[info.filename]
                z.writestr(info, data, compress_type=info.compress_type)
        blob = buf.getvalue()
    else:
        blob = new_bin
    with zipfile.ZipFile(out, "w") as z:
        for info, data in pkg["entries"]:
            if info.filename in ("com.huawei.watchface", "watchface.bin"):
                data = blob
            elif info.filename in overrides:
                data = overrides[info.filename]
            z.writestr(info, data, compress_type=info.compress_type)
