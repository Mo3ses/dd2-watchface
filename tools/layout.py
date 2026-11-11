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


def split_hour(layout: bytes, *, tens_x: int, units_x: int, y: int) -> bytes:
    """Troca a hora (vt 12) por dezena (59) + unidade (60): 9 vira 09.

    O controle único suprime o zero à esquerda; com dois controles, a dezena
    sempre desenha e o relógio mostra 09:58.
    """
    root = read(layout)
    for elem in [f for f in root if f[0] == 1]:
        ef = read(elem[2])
        if get_int(ef, 1) != 1:            # ELEMENT_LABEL_TIME
            continue
        layers = [read(f[2]) for f in ef if f[0] == 5]
        out_layers: list[list] = []
        for lf in layers:
            if get_int(lf, 2) != 3:        # só COMBINED_RES
                out_layers.append(lf)
                continue
            cf = read(get(lf, 6)[2])
            if get_int(cf, 5) != 12:       # só hora
                out_layers.append(lf)
                continue
            ambient = get_int(cf, 13)
            set_int(cf, 5, 59)             # hora, dezena
            set_point(cf, 3, tens_x, y)
            set_int(cf, 4, 0)              # LEFT
            set_bytes(lf, 6, write(cf))

            units = read(write(lf))        # cópia profunda
            ucf = read(get(units, 6)[2])
            set_int(ucf, 5, 60)            # hora, unidade
            set_point(ucf, 3, units_x, y)
            set_int(ucf, 4, 0)
            set_bytes(units, 6, write(ucf))
            set_int(units, 1, 3 if ambient == 0 else 7)
            out_layers.extend([lf, units])

        keep = [f for f in ef if f[0] != 5]
        keep += [[5, 2, write(lf)] for lf in sorted(out_layers, key=lambda l: get_int(l, 1))]
        elem[2] = write(keep)
    return write(root)
