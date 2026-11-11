#!/usr/bin/env python3
"""
layout.py — edita o layout protobuf do watchface.bin (schema v2)

Campos usados (schema do Theme Studio v11, recuperado do codec @joyofit/hwt):

    Element    1 label 2 is_support_option 4 res_preview 5 layer* 8 container*
    Layer      1 index 2 draw_type 4 single_res 6 combined_res
    Container  1 index 5 rect 6 layer* 8 data_type
    Combined   1 res_name* 3 res_position 4 res_align 5 value_type 13 ambient
    Single     1 res_name 2 res_position 5 ambient
    Point      1 x 2 y      Rect 1 x 2 y 3 w 4 h

AlignType: 0 LEFT, 1 CENTER, 2 RIGHT.
ElementLabel: 0 BACKGROUND, 1 TIME, 2 DATE, 3 WIDGET.
"""
from __future__ import annotations


# ---------------------------------------------------------------- wire
def varint(buf: bytes, i: int) -> tuple[int, int]:
    value = shift = 0
    while True:
        b = buf[i]
        i += 1
        value |= (b & 0x7F) << shift
        if not b & 0x80:
            return value, i
        shift += 7


def enc_varint(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def read(buf: bytes) -> list[list]:
    """Devolve [[num, wiretype, valor], ...]; valor int (wt0) ou bytes."""
    out: list[list] = []
    i = 0
    while i < len(buf):
        key, i = varint(buf, i)
        num, wt = key >> 3, key & 7
        if wt == 0:
            val, i = varint(buf, i)
            out.append([num, wt, val])
        elif wt == 2:
            ln, i = varint(buf, i)
            out.append([num, wt, buf[i:i + ln]])
            i += ln
        elif wt == 5:
            out.append([num, wt, buf[i:i + 4]])
            i += 4
        elif wt == 1:
            out.append([num, wt, buf[i:i + 8]])
            i += 8
        else:
            raise ValueError(f"wiretype {wt}")
    return out


def write(fields: list[list]) -> bytes:
    out = bytearray()
    for num, wt, val in fields:
        out += enc_varint((num << 3) | wt)
        if wt == 0:
            out += enc_varint(val)
        elif wt == 2:
            out += enc_varint(len(val)) + val
        else:
            out += val
    return bytes(out)


# ---------------------------------------------------------------- helpers
def get(fields, num, index=0):
    hits = [f for f in fields if f[0] == num]
    return hits[index] if len(hits) > index else None


def get_int(fields, num, default=0):
    f = get(fields, num)
    return f[2] if f else default


def set_int(fields, num, value, index=0):
    hits = [i for i, f in enumerate(fields) if f[0] == num]
    if len(hits) > index:
        fields[hits[index]] = [num, 0, value]
    else:
        fields.append([num, 0, value])


def set_bytes(fields, num, payload, index=0):
    hits = [i for i, f in enumerate(fields) if f[0] == num]
    if len(hits) > index:
        fields[hits[index]] = [num, 2, payload]
    else:
        fields.append([num, 2, payload])


def point(x: int, y: int) -> bytes:
    return write([[1, 0, x], [2, 0, y]])


def rect(x: int, y: int, w: int, h: int) -> bytes:
    return write([[1, 0, x], [2, 0, y], [3, 0, w], [4, 0, h]])


def set_point(fields, num, x, y):
    set_bytes(fields, num, point(x, y))


# ---------------------------------------------------------------- edits
def fix_time_alignment(layout: bytes, *, hour_x: int = 127, colon_x: int = 128,
                       minute_x: int = 257, y: int = 103,
                       hour_align: int = 2, minute_align: int = 2) -> bytes:
    """Hora/minuto ancorados à direita (ou centro) do próprio bloco."""
    root = read(layout)
    for elem in [f for f in root if f[0] == 1]:
        ef = read(elem[2])
        if get_int(ef, 1) != 1:            # ELEMENT_LABEL_TIME
            continue
        for i, lf in enumerate([f for f in ef if f[0] == 5]):
            layer = read(lf[2])
            draw = get_int(layer, 2)
            if draw == 3:                   # COMBINED_RES
                body = get(layer, 6)
                cf = read(body[2])
                vt = get_int(cf, 5)
                if vt == 12:                # hora
                    set_point(cf, 3, hour_x, y)
                    set_int(cf, 4, hour_align)
                elif vt == 13:              # minuto
                    set_point(cf, 3, minute_x, y)
                    set_int(cf, 4, minute_align)
                else:
                    continue
                set_bytes(layer, 6, write(cf))
            elif draw == 1:                 # SINGLE_RES (dois-pontos)
                body = get(layer, 4)
                sf = read(body[2])
                ref = get(sf, 1)
                if not ref or ref[2] not in (b"014", b"025"):
                    continue
                set_point(sf, 2, colon_x, y)
                set_bytes(layer, 4, write(sf))
            else:
                continue
            set_bytes(ef, 5, write(layer), index=i)
        elem[2] = write(ef)
    return write(root)


def add_metric(layout: bytes, refs: list[str], x: int, y: int,
               value_type: int, data_type: int, *,
               index: int = 0, align: int = 0,
               box: tuple[int, int, int, int] | None = None,
               ambient: int = 0) -> bytes:
    """Acrescenta um elemento WIDGET com um container de dígitos combinados."""
    root = read(layout)

    combined = bytearray()
    for ref in refs:
        combined += write([[1, 2, ref.encode()]])
    combined += write([[2, 2, b""], [3, 2, point(x, y)], [4, 0, align],
                       [5, 0, value_type], [6, 2, b""], [7, 0, 0], [8, 0, 0],
                       [13, 0, ambient]])

    layer = write([[1, 0, 0], [2, 0, 3], [6, 2, bytes(combined)]])

    container = write([[1, 0, index], [2, 0, 0]])
    if box:
        container += write([[5, 2, rect(*box)]])
    container += write([[6, 2, layer], [8, 0, data_type]])

    element = write([[1, 0, 3], [2, 0, 0], [8, 2, container]])
    root.append([1, 2, element])
    return write(root)


def add_combined_widget(layout: bytes, refs: list[str], x: int, y: int,
                        value_type: int, data_type: int, **kwargs) -> bytes:
    return add_metric(layout, refs, x, y, value_type, data_type, **kwargs)


def split_pair(layout: bytes, *, in_vt: int, tens_vt: int, units_vt: int,
               tens_x: int, units_x: int, y: int,
               idx_normal: int, idx_aod: int) -> bytes:
    """Troca um controle combinado por dezena + unidade.

    O controle único suprime zeros à esquerda; dois controles garantem 09 e 01.
    """
    root = read(layout)
    for elem in [f for f in root if f[0] == 1]:
        ef = read(elem[2])
        if get_int(ef, 1) != 1:            # ELEMENT_LABEL_TIME
            continue
        layers = [read(f[2]) for f in ef if f[0] == 5]
        out_layers: list[list] = []
        for lf in layers:
            if get_int(lf, 2) != 3:
                out_layers.append(lf)
                continue
            cf = read(get(lf, 6)[2])
            if get_int(cf, 5) != in_vt:
                out_layers.append(lf)
                continue
            ambient = get_int(cf, 13)
            set_int(cf, 5, tens_vt)
            set_point(cf, 3, tens_x, y)
            set_int(cf, 4, 0)
            set_bytes(lf, 6, write(cf))

            units = read(write(lf))
            ucf = read(get(units, 6)[2])
            set_int(ucf, 5, units_vt)
            set_point(ucf, 3, units_x, y)
            set_int(ucf, 4, 0)
            set_bytes(units, 6, write(ucf))
            set_int(units, 1, idx_normal if ambient == 0 else idx_aod)
            out_layers.extend([lf, units])

        keep = [f for f in ef if f[0] != 5]
        keep += [[5, 2, write(lf)]
                 for lf in sorted(out_layers, key=lambda l: get_int(l, 1))]
        elem[2] = write(keep)
    return write(root)


def split_hour(layout: bytes, *, tens_x: int, units_x: int, y: int) -> bytes:
    return split_pair(layout, in_vt=12, tens_vt=59, units_vt=60,
                      tens_x=tens_x, units_x=units_x, y=y,
                      idx_normal=3, idx_aod=7)


def split_minute(layout: bytes, *, tens_x: int, units_x: int, y: int) -> bytes:
    return split_pair(layout, in_vt=13, tens_vt=61, units_vt=62,
                      tens_x=tens_x, units_x=units_x, y=y,
                      idx_normal=8, idx_aod=9)


def _ordered_res(refs, x, y, interval, value_type, mode, ambient, version) -> bytes:
    ordered = bytearray()
    for ref in refs:
        ordered += write([[1, 2, ref.encode()]])
    ordered += write([[2, 2, point(x, y)], [3, 0, interval]])
    if value_type is not None:
        ordered += write([[4, 0, value_type]])
    ordered += write([[5, 0, mode], [8, 0, 0], [9, 0, ambient]])
    if version is not None:
        ordered += write([[13, 0, version]])
    return bytes(ordered)


def add_animation(layout: bytes, refs: list[str], x: int, y: int, *,
                  element_index: int = 0, index: int = 0, interval: int = 0,
                  mode: int = 1, ambient: int = 0,
                  value_type: int | None = 154,
                  version: int | None = 1) -> bytes:
    """Acrescenta o AnimatedLayer a um elemento existente (ex.: o fundo)."""
    root = read(layout)
    elems = [i for i, f in enumerate(root) if f[0] == 1]
    if len(elems) <= element_index:
        raise IndexError("elemento inexistente")
    ef = read(root[elems[element_index]][2])
    ordered = _ordered_res(refs, x, y, interval, value_type, mode, ambient, version)
    animated = write([[1, 0, index], [2, 0, 11], [3, 2, ordered]])
    ef.append([9, 2, animated])
    root[elems[element_index]] = [1, 2, write(ef)]
    return write(root)


def add_animation_element(layout: bytes, refs: list[str], x: int, y: int, *,
                          label: int = 3, after_element: int = 0, index: int = 0,
                          interval: int = 0, mode: int = 1, ambient: int = 0,
                          value_type: int | None = 154,
                          version: int | None = 1) -> bytes:
    """Cria um elemento novo só com a animação, logo acima do fundo."""
    root = read(layout)
    elems = [i for i, f in enumerate(root) if f[0] == 1]
    if len(elems) <= after_element:
        raise IndexError("elemento inexistente")

    ordered = _ordered_res(refs, x, y, interval, value_type, mode, ambient, version)
    animated = write([[1, 0, index], [2, 0, 11], [3, 2, ordered]])
    element = write([[1, 0, label], [2, 0, 0], [9, 2, animated]])
    root.insert(elems[after_element] + 1, [1, 2, element])
    return write(root)
