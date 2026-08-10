"""Emit the raster app icons — favicon, apple-touch-icon, PWA manifest icons.

Same object as everywhere else. These are rasterised FROM the generated SVG, not
redrawn, so the icon cannot quietly become a different mark: change the geometry
in `build_assets.py`'s BAND/STYLE and rerun both builders.

Two things are decided here and nowhere else, because icons are square and the
mark is 1 wide : 2.15 high:

1. FRAMING — the mark is centred on a square canvas with padding.
2. THE TILE — a white rounded tile behind it (founder choice, 2026-08-10, from
   the five treatments in `favicon_options.py`). A bare transparent mark had
   nothing to anchor it and was near-invisible in a tab strip.

Run: python build_icons.py   (after build_assets.py)
"""

import io
import pathlib
import re

import cairosvg
from PIL import Image, ImageDraw

import build_assets as BA
import holo

OUT = pathlib.Path(__file__).resolve().parents[2] / "web" / "public"

# The mark occupies this share of the canvas HEIGHT. 0.86 leaves a margin that
# reads as deliberate; 0.96 was rendered alongside it and read as cramped, the
# mark almost touching the tile edge.
FILL = 0.86

TILE = (255, 255, 255, 255)
# iOS-style continuous-corner proportion. Android and iOS both apply their own
# mask on top for installed icons; this is for the browser tab, where nothing
# else rounds it for us.
RADIUS = 0.22

# Rendered at icon scale, so sampled richly — a favicon is rasterised once and
# cached forever, and the bytes never reach a page.
FIDELITY = dict(samples=300, chunks=34, keys=72, prec=2)

# MORE INK, SAME OBJECT. On the page the lattice is translucent because it is
# drawn 380px tall and depth reads as brightness. At 16px it is ~6px wide, and
# measured: the page values put ZERO pixels above half alpha at both 16 and 32 —
# the favicon rasterised to a smudge with no solid ink anywhere in it.
#
# So the icon raises opacity and stroke weight. That is the same decision as
# varying `samples` between the nav and the hero: the object, its band, its
# strand count and its proportions are untouched; only how heavily it is inked
# changes, because a 16px raster cannot carry a 0.30-alpha hairline.
ICON_INK = dict(
    strand_op=0.85,
    edge_op=1.0,
    rib_op=0.45,
    strand_w=1.4,
    edge_w=2.4,
)

# Supersample factor. Cairo's direct 16px raster of sub-pixel hairlines is
# harsher than drawing large and reducing; compared side by side, 8x is where
# the 16px frame stops looking broken.
SS = 8


def square_svg(canvas=512):
    """The mark alone, centred on a transparent square canvas."""
    style = dict(BA.STYLE)
    style.update(ICON_INK)
    src = holo.svg(512, pulses=(), uid="icon", **BA.BAND, **style, **FIDELITY)
    vb = [float(n) for n in re.search(r'viewBox="([^"]+)"', src).group(1).split()]
    x0, y0, w, h = vb
    inner = re.sub(r"^<svg[^>]*>", "", src)
    inner = re.sub(r"</svg>$", "", inner)

    scale = (canvas * FILL) / h
    tx = (canvas - w * scale) / 2 - x0 * scale
    ty = (canvas - h * scale) / 2 - y0 * scale

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas}" '
        f'height="{canvas}" viewBox="0 0 {canvas} {canvas}">'
        f'<g transform="translate({tx:.3f},{ty:.3f}) scale({scale:.5f})">'
        f"{inner}</g></svg>"
    )


def icon(svg_text, size, rounded=True):
    """Tile + mark at `size`, supersampled then reduced."""
    art = Image.open(
        io.BytesIO(
            cairosvg.svg2png(
                bytestring=svg_text.encode("utf-8"),
                output_width=size * SS,
                output_height=size * SS,
            )
        )
    ).convert("RGBA")

    tile = Image.new("RGBA", art.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(tile)
    box = [0, 0, art.size[0] - 1, art.size[1] - 1]
    if rounded:
        d.rounded_rectangle(box, radius=int(art.size[0] * RADIUS), fill=TILE)
    else:
        # Full bleed: iOS masks apple-touch-icon itself, and a pre-rounded
        # source shows white corners outside its mask.
        d.rectangle(box, fill=TILE)
    tile.alpha_composite(art)
    return tile.resize((size, size), Image.LANCZOS)


def save_png(im, name):
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    (OUT / name).write_bytes(buf.getvalue())
    print(f"  {name:24s} {im.size[0]:4d}px  {len(buf.getvalue()):8,d} bytes")


def main():
    svg_text = square_svg()
    (OUT / "brand" / "tru8-icon.svg").write_text(svg_text, encoding="utf-8")

    save_png(icon(svg_text, 64), "favicon.png")
    save_png(icon(svg_text, 512), "icon-512.png")
    save_png(icon(svg_text, 192), "icon-192.png")
    save_png(icon(svg_text, 180, rounded=False), "apple-touch-icon.png")

    # Multi-resolution .ico — browsers and Windows pick the frame they need
    # rather than downscaling a 64px PNG badly.
    frames = [icon(svg_text, s) for s in (16, 32, 48)]
    frames[0].save(
        OUT / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
        append_images=frames[1:],
    )
    print(
        f"  {'favicon.ico':24s} 16/32/48  "
        f"{(OUT / 'favicon.ico').stat().st_size:8,d} bytes"
    )

    # Legibility guard. With a tile behind it, alpha is opaque everywhere, so
    # the meaningful measure is how much of the tile carries MARK rather than
    # background. If a geometry change drives this toward zero the favicon has
    # silently become a blank white square.
    for s in (16, 32):
        im = icon(svg_text, s).convert("RGB")
        px = list(im.getdata())
        ink = sum(1 for r, g, b in px if (r - b) > 20)
        print(
            f"  [{s:2d}px legibility] {ink:4d} of {len(px)} px carry mark "
            f"— {100 * ink / len(px):.1f}%"
        )

    print(f"\nwritten to {OUT}")


if __name__ == "__main__":
    main()
