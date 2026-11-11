#!/usr/bin/env python3
"""
build_face.py — monta a face sobre o layout HWHD06 do JoyoFit Studio

O seed base/myface.hwt doa a config (elementos, layers, value types 12/13).
Aqui a gente troca a pele e, quando a variante pede, corrige o layout.

    slot  0        thumbnail do seletor
    slot  1        fundo normal 280x456
    slot  2        fundo AOD 280x456
    slots 3..12    digitos normais 0-9
    slot  13       dois-pontos normal
    slots 14..23   digitos AOD
    slot  24       dois-pontos AOD
    slots 25..     atlas de valores (34px) e do banner (30px)

Variantes:
    v0  digitos 50x53 (medida do seed)
    v1  digitos 51x111 (relogio grande)
    v2  v1 + hora/minuto ancorados a direita
    v3  v2 + containers de batimento e bateria
    v4  v3 + arte do fundo.jpg como plano de fundo
    v5  layout final: hora alta, banner de passos, grid 2x2, 5 metricas

    python tools/build_face.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PROJECT = Path(__file__).resolve().parent.parent
TOOLS = Path(__file__).resolve().parent
SS = 3

sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(TOOLS))
import gen_assets as ga  # noqa: E402
import layout as L  # noqa: E402
from hwformat import build_bin, load_package, parse_bin, pil_to_blob, save_package  # noqa: E402

SLOTS = {
    "thumb": 0, "bg": 1, "aod_bg": 2,
    "digits": list(range(3, 13)), "colon": 13,
    "aod_digits": list(range(14, 24)), "aod_colon": 24,
}

VARIANTS = {
    "v0": {"tile": (50, 53), "colon": (28, 53), "size": 44, "layout": None},
    "v1": {"tile": (51, 111), "colon": (20, 111), "size": 94, "layout": None},
    "v2": {"tile": (51, 111), "colon": (20, 111), "size": 94, "layout": "align"},
    "v3": {"tile": (51, 111), "colon": (20, 111), "size": 94, "layout": "align",
           "metrics": [
               {"x": 24, "y": 306, "vt": 2, "dt": 11, "align": 0,
                "box": (24, 300, 104, 48)},
               {"x": 246, "y": 387, "vt": 9, "dt": 17, "align": 2,
                "box": (152, 381, 96, 48)},
           ]},
    "v4": {"tile": (51, 111), "colon": (20, 111), "size": 94, "layout": "align",
           "art": True,
           "metrics": [
               {"x": 24, "y": 300, "vt": 2, "dt": 11, "align": 0,
                "box": (24, 296, 104, 48)},
               {"x": 246, "y": 372, "vt": 9, "dt": 17, "align": 2,
                "box": (152, 368, 96, 48)},
           ]},
    "v5": {"tile": (47, 74), "colon": (18, 74), "size": 88, "baseline": 0.88,
           "layout": "v5", "art": True,
           "banner": {"tile": (18, 32), "size": 30, "baseline": 0.86},
           "metrics": [
               {"atlas": "value", "x": 75, "y": 310, "vt": 2, "dt": 11, "align": 1,
                "box": (24, 306, 102, 48)},
               {"atlas": "value", "x": 205, "y": 310, "vt": 1, "dt": 12, "align": 1,
                "box": (152, 306, 102, 48)},
               {"atlas": "value", "x": 75, "y": 382, "vt": 4, "dt": 21, "align": 1,
                "box": (24, 378, 102, 48)},
               {"atlas": "value", "x": 214, "y": 382, "vt": 9, "dt": 17, "align": 2,
                "box": (152, 378, 102, 48)},
               {"atlas": "banner", "x": 140, "y": 250, "vt": 0, "dt": 10, "align": 1,
                "box": (60, 246, 160, 40)},
           ]},
    "v6": {"tile": (47, 74), "colon": (18, 74), "size": 88, "baseline": 0.88,
           "layout": "v5", "art": True,
           "banner": {"tile": (18, 32), "size": 30, "baseline": 0.86},
           "metrics": [
               {"atlas": "value", "x": 75, "y": 334, "vt": 2, "dt": 11, "align": 1,
                "box": (24, 314, 102, 48)},
               {"atlas": "value", "x": 205, "y": 334, "vt": 1, "dt": 12, "align": 1,
                "box": (152, 314, 102, 48)},
               {"atlas": "value", "x": 75, "y": 406, "vt": 4, "dt": 21, "align": 1,
                "box": (24, 386, 102, 48)},
               {"atlas": "value", "x": 222, "y": 386, "vt": 9, "dt": 17, "align": 2,
                "box": (152, 382, 102, 48)},
               {"atlas": "banner", "x": 140, "y": 266, "vt": 0, "dt": 10, "align": 1,
                "box": (60, 246, 160, 40)},
           ]},
    "v7": {"tile": (47, 74), "colon": (18, 74), "size": 88, "baseline": 0.88,
           "layout": "v7", "art": True,
           "banner": {"tile": (18, 32), "size": 30, "baseline": 0.86},
           "metrics": [
               {"atlas": "value", "x": 75, "y": 334, "vt": 2, "dt": 11, "align": 1,
                "box": (24, 314, 102, 48)},
               {"atlas": "value", "x": 205, "y": 334, "vt": 1, "dt": 12, "align": 1,
                "box": (152, 314, 102, 48)},
               {"atlas": "value", "x": 75, "y": 406, "vt": 4, "dt": 21, "align": 1,
                "box": (24, 386, 102, 48)},
               {"atlas": "value", "x": 222, "y": 386, "vt": 9, "dt": 17, "align": 2,
                "box": (152, 382, 102, 48)},
               {"atlas": "banner", "x": 140, "y": 266, "vt": 0, "dt": 10, "align": 1,
                "box": (60, 246, 160, 40)},
           ]},
    "v8": {"tile": (47, 74), "colon": (18, 74), "size": 88, "baseline": 0.88,
           "layout": "v8", "art": True,
           "banner": {"tile": (18, 32), "size": 30, "baseline": 0.86},
           "metrics": [
               {"atlas": "value", "x": 75, "y": 334, "vt": 2, "dt": 11, "align": 1,
                "box": (24, 314, 102, 48)},
               {"atlas": "value", "x": 205, "y": 334, "vt": 1, "dt": 12, "align": 1,
                "box": (152, 314, 102, 48)},
               {"atlas": "value", "x": 75, "y": 406, "vt": 4, "dt": 21, "align": 1,
                "box": (24, 386, 102, 48)},
               {"atlas": "value", "x": 222, "y": 386, "vt": 9, "dt": 17, "align": 2,
                "box": (152, 382, 102, 48)},
               {"atlas": "banner", "x": 140, "y": 266, "vt": 0, "dt": 10, "align": 1,
                "box": (60, 246, 160, 40)},
           ]},
    "v9": {"tile": (47, 74), "colon": (18, 74), "size": 88, "baseline": 0.88,
           "gradient": ((0xF7, 0xDF, 0xA0), (0xC8, 0x9B, 0x52)),
           "stroke": (0x2A, 0x12, 0x0A),
           "layout": "v9", "art": "relic",
           "banner": {"tile": (18, 32), "size": 30, "baseline": 0.86},
           "metrics": [
               {"atlas": "value", "x": 60, "y": 344, "vt": 2, "dt": 11, "align": 0,
                "box": (56, 340, 96, 44)},
               {"atlas": "value", "x": 190, "y": 344, "vt": 1, "dt": 12, "align": 0,
                "box": (186, 340, 72, 44)},
               {"atlas": "value", "x": 60, "y": 396, "vt": 4, "dt": 21, "align": 0,
                "box": (56, 392, 72, 44)},
               {"atlas": "value", "x": 228, "y": 396, "vt": 9, "dt": 17, "align": 2,
                "box": (184, 392, 72, 44)},
               {"atlas": "banner", "x": 118, "y": 302, "vt": 0, "dt": 10, "align": 0,
                "box": (114, 300, 110, 36)},
           ]},
    "v11": {"tile": (47, 74), "colon": (18, 74), "size": 88, "baseline": 0.88,
            "gradient": ((0xF7, 0xDF, 0xA0), (0xC8, 0x9B, 0x52)),
            "stroke": (0x2A, 0x12, 0x0A),
            "layout": "v9", "art": "relic",
            "banner": {"tile": (18, 32), "size": 30, "baseline": 0.86},
            "animation": {"x": 55, "y": 120, "glow": True, "label": 3,
                          "after": 0, "value_type": 154, "mode": 1,
                          "version": 1, "interval": 0},
            "metrics": [
                {"atlas": "value", "x": 60, "y": 344, "vt": 2, "dt": 11, "align": 0,
                 "box": (56, 340, 96, 44)},
                {"atlas": "value", "x": 190, "y": 344, "vt": 1, "dt": 12, "align": 0,
                 "box": (186, 340, 72, 44)},
                {"atlas": "value", "x": 60, "y": 396, "vt": 4, "dt": 21, "align": 0,
                 "box": (56, 392, 72, 44)},
                {"atlas": "value", "x": 228, "y": 396, "vt": 9, "dt": 17, "align": 2,
                 "box": (184, 392, 72, 44)},
                {"atlas": "banner", "x": 118, "y": 302, "vt": 0, "dt": 10, "align": 0,
                 "box": (114, 300, 110, 36)},
            ]},
    "v12": {"tile": (47, 74), "colon": (18, 74), "size": 88, "baseline": 0.88,
            "gradient": ((0xF7, 0xDF, 0xA0), (0xC8, 0x9B, 0x52)),
            "stroke": (0x2A, 0x12, 0x0A),
            "layout": "v9", "art": "relic",
            "banner": {"tile": (18, 32), "size": 30, "baseline": 0.86},
            "animation": {"x": 55, "y": 120, "glow": True, "in_element": 0,
                          "value_type": 154, "mode": 1, "version": 1, "interval": 0},
            "metrics": [
                {"atlas": "value", "x": 60, "y": 344, "vt": 2, "dt": 11, "align": 0,
                 "box": (56, 340, 96, 44)},
                {"atlas": "value", "x": 190, "y": 344, "vt": 1, "dt": 12, "align": 0,
                 "box": (186, 340, 72, 44)},
                {"atlas": "value", "x": 60, "y": 396, "vt": 4, "dt": 21, "align": 0,
                 "box": (56, 392, 72, 44)},
                {"atlas": "value", "x": 228, "y": 396, "vt": 9, "dt": 17, "align": 2,
                 "box": (184, 392, 72, 44)},
                {"atlas": "banner", "x": 118, "y": 302, "vt": 0, "dt": 10, "align": 0,
                 "box": (114, 300, 110, 36)},
            ]},
}


def render(ch: str, w: int, h: int, size: int, color, colon: bool = False,
           baseline: float = 0.78, gradient=None, stroke=None) -> Image.Image:
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(FONT), size * SS)
    xy = (w * SS / 2, h * SS * 0.47) if colon else (w * SS / 2, h * SS * baseline)
    anchor = "mm" if colon else "ms"
    if gradient:
        d.text(xy, ch, font=font, fill=(0, 0, 0, 255), anchor=anchor,
               stroke_width=SS, stroke_fill=(*(stroke or (0x2A, 0x12, 0x0A)), 255))
        mask = Image.new("L", img.size, 0)
        ImageDraw.Draw(mask).text(xy, ch, font=font, fill=255, anchor=anchor)
        grad = Image.new("RGBA", img.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(grad)
        for y in range(img.height):
            t = y / max(1, img.height - 1)
            col = tuple(int(gradient[0][i] + (gradient[1][i] - gradient[0][i]) * t)
                        for i in range(3))
            gd.line([(0, y), (img.width, y)], fill=(*col, 255))
        img = Image.composite(grad, img, mask)
    else:
        d.text(xy, ch, font=font, fill=(*color, 255), anchor=anchor)
    return img.resize((w, h), Image.Resampling.LANCZOS)


def build_tiles(name: str, cfg: dict, build: Path) -> dict[str, list[Path]]:
    tw, th = cfg["tile"]
    cw, chh = cfg["colon"]
    base = cfg.get("baseline", 0.78)
    paths: dict[str, list[Path]] = {}
    for sub, color in (("normal", ga.GOLD), ("aod", ga.AOD_GOLD)):
        out = build / f"tiles_{name}_{sub}"
        out.mkdir(parents=True, exist_ok=True)
        gradient = cfg.get("gradient") if sub == "normal" else None
        stroke = cfg.get("stroke") if sub == "normal" else None
        digits = []
        for i in range(10):
            p = out / f"{i}.png"
            render(str(i), tw, th, cfg["size"], color, baseline=base,
                   gradient=gradient, stroke=stroke).save(p)
            digits.append(p)
        colon = out / "colon.png"
        render(":", cw, chh, cfg["size"], color, colon=True).save(colon)
        paths[sub] = digits
        paths[f"{sub}_colon"] = [colon]
    return paths


def build_banner(name: str, cfg: dict, build: Path) -> list[Path]:
    tw, th = cfg["tile"]
    base = cfg.get("baseline", 0.86)
    out = build / f"tiles_{name}_banner"
    out.mkdir(parents=True, exist_ok=True)
    digits = []
    for i in range(10):
        p = out / f"{i}.png"
        render(str(i), tw, th, cfg["size"], ga.GOLD, baseline=base).save(p)
        digits.append(p)
    return digits


def rename_description(desc: bytes) -> bytes:
    import re
    replacements = [
        (rb"<title>.*?</title>", b"<title>Arisen HUD</title>"),
        (rb"<title-cn>.*?</title-cn>", "<title-cn>Arisen HUD</title-cn>".encode()),
        (rb"<author>.*?</author>", b"<author>Mo3ses</author>"),
        (rb"<designer>.*?</designer>", b"<designer>Mo3ses</designer>"),
    ]
    for pattern, value in replacements:
        desc = re.sub(pattern, value, desc, count=1, flags=re.S)
    return desc


def bump_description(desc: bytes, index: int) -> bytes:
    import re
    hit = re.search(rb"<version>(\d+)\.(\d+)\.(\d+)</version>", desc)
    if not hit:
        return desc
    z = int(hit.group(3)) + index
    return desc.replace(hit.group(0),
                        f"<version>{hit.group(1).decode()}."
                        f"{hit.group(2).decode()}.{z}</version>".encode())


def main() -> int:
    global FONT
    build = PROJECT / "build"
    out = PROJECT / "out"
    seed = PROJECT / "base" / "myface.hwt"
    if not seed.exists():
        sys.exit(f"[seed] ausente: {seed}")

    font_path, _ = ga.resolve_font(None, PROJECT)
    FONT = font_path
    print(f"[font] {font_path}")

    preview = Image.open(build / "preview.png").convert("RGB")
    preview.resize((156, 256), Image.Resampling.LANCZOS).save(build / "thumb.png")

    pkg = load_package(seed)
    info = parse_bin(pkg["bin"])
    print(f"[seed] {len(info['images'])} slots, layout {len(info['layout'])} B")

    for index, (name, cfg) in enumerate(VARIANTS.items()):
        tiles = build_tiles(name, cfg, build)
        art = cfg.get("art")
        if art == "relic":
            bg_name, aod_name = "bg_relic.png", "bg_relic_aod.png"
        elif art:
            bg_name, aod_name = "bg_art.png", "bg_art_aod.png"
        else:
            bg_name, aod_name = "bg.png", "bg_aod_plain.png"
        mapping: dict[int, Path] = {
            SLOTS["thumb"]: build / "thumb.png",
            SLOTS["bg"]: build / bg_name,
            SLOTS["aod_bg"]: build / aod_name,
        }
        for i, idx in enumerate(SLOTS["digits"]):
            mapping[idx] = tiles["normal"][i]
        mapping[SLOTS["colon"]] = tiles["normal_colon"][0]
        for i, idx in enumerate(SLOTS["aod_digits"]):
            mapping[idx] = tiles["aod"][i]
        mapping[SLOTS["aod_colon"]] = tiles["aod_colon"][0]

        blobs = []
        for img in info["images"]:
            path = mapping.get(img["index"])
            if path is None:
                blobs.append(img["blob"])
            else:
                with Image.open(path) as im:
                    blobs.append(pil_to_blob(im.convert("RGBA")))

        layout_bytes = info["layout"]
        if cfg.get("layout") == "align":
            layout_bytes = L.fix_time_alignment(layout_bytes)
        elif cfg.get("layout") == "v5":
            layout_bytes = L.fix_time_alignment(layout_bytes, hour_x=131, colon_x=131,
                                                minute_x=149, y=68, minute_align=0)
        elif cfg.get("layout") == "v7":
            layout_bytes = L.fix_time_alignment(layout_bytes, hour_x=131, colon_x=131,
                                                minute_x=149, y=68, minute_align=0)
            layout_bytes = L.split_hour(layout_bytes, tens_x=37, units_x=84, y=68)
        elif cfg.get("layout") == "v8":
            layout_bytes = L.fix_time_alignment(layout_bytes, hour_x=131, colon_x=131,
                                                minute_x=149, y=68, minute_align=0)
            layout_bytes = L.split_hour(layout_bytes, tens_x=37, units_x=84, y=68)
            layout_bytes = L.split_minute(layout_bytes, tens_x=149, units_x=196, y=68)
        elif cfg.get("layout") == "v9":
            layout_bytes = L.fix_time_alignment(layout_bytes, hour_x=131, colon_x=131,
                                                minute_x=149, y=64, minute_align=0)
            layout_bytes = L.split_hour(layout_bytes, tens_x=37, units_x=84, y=64)
            layout_bytes = L.split_minute(layout_bytes, tens_x=149, units_x=196, y=64)

        if cfg.get("metrics"):
            atlases: dict[str, list[str]] = {}
            kinds = {m.get("atlas", "value") for m in cfg["metrics"]}
            if "value" in kinds:
                start = len(blobs)
                for i in range(10):
                    with Image.open(build / "value" / f"{i}.png") as im:
                        blobs.append(pil_to_blob(im.convert("RGBA")))
                atlases["value"] = [f"{start + i + 1:03d}" for i in range(10)]
            if "banner" in kinds:
                bdigits = build_banner(name, cfg["banner"], build)
                start = len(blobs)
                for p in bdigits:
                    with Image.open(p) as im:
                        blobs.append(pil_to_blob(im.convert("RGBA")))
                atlases["banner"] = [f"{start + i + 1:03d}" for i in range(10)]
            for i, m in enumerate(cfg["metrics"]):
                layout_bytes = L.add_metric(
                    layout_bytes, atlases[m.get("atlas", "value")],
                    m["x"], m["y"], m["vt"], m["dt"],
                    index=i, align=m.get("align", 0), box=m.get("box"))

        if cfg.get("animation"):
            anim = cfg["animation"]
            hdir = build / ("heart_glow" if anim.get("glow") else "heart")
            frames = sorted(hdir.glob("*.png"))
            if not frames:
                sys.exit(f"[anim] frames ausentes em {hdir}")
            start = len(blobs)
            for p in frames:
                with Image.open(p) as im:
                    blobs.append(pil_to_blob(im.convert("RGBA")))
            refs = [f"{start + i + 1:03d}" for i in range(len(frames))]
            if "in_element" in anim:
                layout_bytes = L.add_animation(
                    layout_bytes, refs, anim["x"], anim["y"],
                    element_index=anim["in_element"],
                    interval=anim.get("interval", 0),
                    mode=anim.get("mode", 1),
                    value_type=anim.get("value_type", 154),
                    version=anim.get("version", 1))
            else:
                layout_bytes = L.add_animation_element(
                    layout_bytes, refs, anim["x"], anim["y"],
                    label=anim.get("label", 3), after_element=anim.get("after", 0),
                    interval=anim.get("interval", 0), mode=anim.get("mode", 1),
                    value_type=anim.get("value_type", 154),
                    version=anim.get("version", 1))

        override = {}
        if pkg["description"]:
            desc = rename_description(pkg["description"])
            override["description.xml"] = bump_description(desc, index)

        new_bin = build_bin(info["version"], layout_bytes, blobs,
                            signature=info["signature"], reserved=info["reserved"])
        dest = out / f"ARISEN_HUD_{name}.hwt"
        save_package(pkg, new_bin, dest, overrides=override)
        print(f"[{name}] {dest}  ({len(new_bin)} B de binario)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
