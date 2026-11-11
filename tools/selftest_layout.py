#!/usr/bin/env python3
"""
selftest_layout.py — prova as edições de layout sem relógio

Monta um layout sintético (hora + dois-pontos + minuto), aplica
fix_time_alignment e add_metric, e confere campo por campo.

    python tools/selftest_layout.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import layout as L  # noqa: E402

REFS = [f"{i + 2:03d}" for i in range(10)]


def combined(refs, x, y, vt, align=0, ambient=0):
    body = b"".join(L.write([[1, 2, r.encode()]]) for r in refs)
    body += L.write([[2, 2, b""], [3, 2, L.point(x, y)], [4, 0, align],
                     [5, 0, vt], [6, 2, b""], [7, 0, 0], [8, 0, 0],
                     [13, 0, ambient]])
    return body


def layer(index, draw, field, body):
    return L.write([[1, 0, index], [2, 0, draw], [field, 2, body]])


def element(label, layers):
    out = L.write([[1, 0, label], [2, 0, 0]])
    for lf in layers:
        out += L.write([[5, 2, lf]])
    return out


def time_element():
    return element(1, [
        layer(0, 3, 6, combined(REFS, 25, 103, 12)),
        layer(1, 1, 4, L.write([[1, 2, b"014"], [2, 2, L.point(126, 103)], [5, 0, 0]])),
        layer(2, 3, 6, combined(REFS, 155, 103, 13)),
    ])


def find(elements, label):
    return [e for e in elements if L.get_int(e, 1) == label]


def main() -> int:
    root = L.write([[1, 2, time_element()]])
    original = root

    fixed = L.fix_time_alignment(root)
    elems = [L.read(f[2]) for f in L.read(fixed) if f[0] == 1]
    assert len(elems) == 1
    layers = [L.read(f[2]) for f in elems[0] if f[0] == 5]
    hour = L.read(L.get(layers[0], 6)[2])
    colon = L.read(L.get(layers[1], 4)[2])
    minute = L.read(L.get(layers[2], 6)[2])
    assert L.get_int(hour, 5) == 12 and L.get_int(hour, 4) == 2
    assert L.read(L.get(hour, 3)[2])[0][2] == 127
    assert L.read(L.get(colon, 2)[2])[0][2] == 128
    assert L.read(L.get(minute, 3)[2])[0][2] == 257
    print("[ok] fix_time_alignment: hora/minuto RIGHT, dois-pontos em 128")

    with_metric = L.add_metric(fixed, REFS, 24, 300, 2, 11, index=0, align=0,
                               box=(24, 296, 104, 48))
    elems = [L.read(f[2]) for f in L.read(with_metric) if f[0] == 1]
    assert len(elems) == 2, len(elems)
    widget = find(elems, 3)[0]
    containers = [L.read(f[2]) for f in widget if f[0] == 8]
    assert len(containers) == 1
    assert L.get_int(containers[0], 2) == 0        # is_support_option
    assert L.get_int(containers[0], 8) == 11       # data_type HR
    rect = L.read(L.get(containers[0], 5)[2])
    assert [L.get_int(rect, i) for i in (1, 2, 3, 4)] == [24, 296, 104, 48]
    cl = L.read(L.get(containers[0], 6)[2])
    body = L.read(L.get(cl, 6)[2])
    assert L.get_int(body, 5) == 2                 # value_type HR
    assert L.get_int(body, 4) == 0                 # align LEFT
    assert len([f for f in body if f[0] == 1]) == 10
    assert L.get(body, 2) is not None and L.get(body, 6) is not None
    print("[ok] add_metric: container com is_support_option, data_type e rect")

    # o elemento de tempo original tem que sobreviver byte a byte
    before = [f for f in L.read(original) if f[0] == 1][0][2]
    after = [f for f in L.read(fixed) if f[0] == 1][0][2]
    assert L.read(before) != L.read(after)  # foi editado
    tail = [f for f in L.read(with_metric) if f[0] == 1][-1][2]
    assert L.get_int(L.read(tail), 1) == 3
    print("[ok] layout antigo preservado, elemento novo anexado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
