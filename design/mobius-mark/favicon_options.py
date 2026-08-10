"""Render favicon treatments side by side so the choice is made by looking.

Not a build step — `build_icons.py` emits the real assets. This exists to answer
one question: does a tile background plus rounded corners make the mark more
identifiable at 16 and 32px than a bare transparent mark?

Run: python favicon_options.py   -> design/preview/05-favicon-tiles.png
"""

import io
import pathlib
import re

import cairosvg
from PIL import Image, ImageDraw

import build_assets as BA
import build_icons as BI
import holo

OUT = pathlib.Path(__file__).resolve().parents[1] / "preview"

# On a dark tile the on-white ramp disappears — it renders the light as INK,
# and ink on black is invisible. Dark tiles get the bright glow instead.
GLOW_ON_LIGHT = "#EA580C"
GLOW_ON_DARK = "#FB923C"


def mark_png(size, fill, glow, bg, radius_frac):
    style = dict(BA.STYLE)
    style.update(BI.ICON_INK)
    style["glow"] = glow
    src = holo.svg(512, pulses=(), uid="opt", **BA.BAND, **style, **BI.FIDELITY)
    vb = [float(n) for n in re.search(r'viewBox="([^"]+)"', src).group(1).split()]
    x0, y0, w, h = vb
    inner = re.sub(r"^<svg[^>]*>", "", src)
    inner = re.sub(r"</svg>$", "", inner)
    C = 512
    sc = (C * fill) / h
    tx = (C - w * sc) / 2 - x0 * sc
    ty = (C - h * sc) / 2 - y0 * sc
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{C}" height="{C}" '
        f'viewBox="0 0 {C} {C}">'
        f'<g transform="translate({tx:.3f},{ty:.3f}) scale({sc:.5f})">'
        f"{inner}</g></svg>"
    )
    art = Image.open(
        io.BytesIO(
            cairosvg.svg2png(
                bytestring=svg.encode("utf-8"),
                output_width=size * 8,
                output_height=size * 8,
            )
        )
    ).convert("RGBA")

    if bg is None:
        tile = Image.new("RGBA", art.size, (0, 0, 0, 0))
    else:
        tile = Image.new("RGBA", art.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(tile)
        r = int(art.size[0] * radius_frac)
        d.rounded_rectangle([0, 0, art.size[0] - 1, art.size[1] - 1], radius=r, fill=bg)
    tile.alpha_composite(art)
    # Supersampled 8x then reduced — Cairo's own 16px raster of hairlines is
    # harsher than a downsampled one, and the tab icon is what the user sees.
    return tile.resize((size, size), Image.LANCZOS)


OPTIONS = [
    ("A  transparent (current)", None, 0.86, GLOW_ON_LIGHT, 0.0),
    ("B  white tile, rounded", (255, 255, 255, 255), 0.86, GLOW_ON_LIGHT, 0.22),
    ("C  white tile, larger", (255, 255, 255, 255), 0.96, GLOW_ON_LIGHT, 0.22),
    ("D  black tile, rounded", (9, 9, 11, 255), 0.86, GLOW_ON_DARK, 0.22),
    ("E  black tile, larger", (9, 9, 11, 255), 0.96, GLOW_ON_DARK, 0.22),
]

SIZES = (16, 32, 64)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    pad, label_w, cell = 16, 210, 120
    sheet = Image.new(
        "RGBA",
        (label_w + len(SIZES) * cell * 2 + pad, len(OPTIONS) * cell + 70),
        (150, 150, 155, 255),  # mid grey: white tiles and dark tiles both show
    )
    d = ImageDraw.Draw(sheet)
    x = label_w
    for s in SIZES:
        d.text((x + 20, 12), f"{s}px actual", fill=(0, 0, 0, 255))
        d.text((x + cell + 10, 12), f"{s}px magnified", fill=(0, 0, 0, 255))
        x += cell * 2

    y = 40
    for label, bg, fill, glow, rad in OPTIONS:
        d.text((10, y + cell // 2), label, fill=(0, 0, 0, 255))
        x = label_w
        for s in SIZES:
            im = mark_png(s, fill, glow, bg, rad)
            sheet.alpha_composite(im, (x + (cell - s) // 2, y + (cell - s) // 2))
            big = im.resize((96, 96), Image.NEAREST)
            sheet.alpha_composite(big, (x + cell + 12, y + 12))
            x += cell * 2
        y += cell

    sheet.convert("RGB").save(OUT / "05-favicon-tiles.png")
    print(f"-> {OUT / '05-favicon-tiles.png'}")


if __name__ == "__main__":
    main()
