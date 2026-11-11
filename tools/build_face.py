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
}


def render(ch: str, w: int, h: int, size: int, color, colon: bool = False,
           baseline: float = 0.78) -> Image.Image:
    img = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(FONT), size * SS)
    if colon:
        d.text((w * SS / 2, h * SS * 0.47), ch, font=font, fill=(*color, 255), anchor="mm")
    else:
        d.text((w * SS / 2, h * SS * baseline), ch, font=font,
               fill=(*color, 255), anchor="ms")
    return img.resize((w, h), Image.Resampling.LANCZOS)


def build_tiles(name: str, cfg: dict, build: Path) -> dict[str, list[Path]]:
    tw, th = cfg["tile"]
    cw, chh = cfg["colon"]
    base = cfg.get("baseline", 0.78)
    paths: dict[str, list[Path]] = {}
    for sub, color in (("normal", ga.GOLD), ("aod", ga.AOD_GOLD)):
        out = build / f"tiles_{name}_{sub}"
        out.mkdir(parents=True, exist_ok=True)
        digits = []
        for i in range(10):
            p = out / f"{i}.png"
            render(str(i), tw, th, cfg["size"], color, baseline=base).save(p)
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
        mapping: dict[int, Path] = {
            SLOTS["thumb"]: build / "thumb.png",
            SLOTS["bg"]: build / ("bg_art.png" if cfg.get("art") else "bg.png"),
            SLOTS["aod_bg"]: build / ("bg_art_aod.png" if cfg.get("art") else "bg_aod_plain.png"),
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

        override = {}
        if pkg["description"]:
            override["description.xml"] = bump_description(pkg["description"], index)

        new_bin = build_bin(info["version"], layout_bytes, blobs,
                            signature=info["signature"], reserved=info["reserved"])
        dest = out / f"ARISEN_HUD_{name}.hwt"
        save_package(pkg, new_bin, dest, overrides=override)
        print(f"[{name}] {dest}  ({len(new_bin)} B de binario)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
