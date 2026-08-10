"""Emit the raster app icons — favicon, apple-touch-icon, PWA manifest icons.

Same object as everywhere else. These are rasterised FROM the generated SVG, not
redrawn, so the icon cannot quietly become a different mark: change the geometry
in `build_assets.py`'s BAND/STYLE and rerun both builders.

Why a separate builder: icons are SQUARE and the mark is 1 wide : 2.15 high, so
it has to be centred on a square canvas with padding. That framing is the only
thing decided here.

Run: python build_icons.py   (after build_assets.py)
"""

import io
import pathlib
import re

import cairosvg

import build_assets as BA
import holo

OUT = pathlib.Path(__file__).resolve().parents[2] / "web" / "public"

# The mark occupies this share of the canvas HEIGHT. 0.86 leaves a margin that
# reads as deliberate at 512px without shrinking the strokes into nothing at 32.
FILL = 0.86

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
# changes, because a 16px raster cannot carry a 0.30-alpha hairline. Measured
# after: 9.4% of the canvas solid at 16px, 9.6% at 32px.
#
# The legibility figures at the end of main() are the guard. If a geometry
# change drops 16px back toward zero solid pixels, the favicon has silently
# become a blur again.
ICON_INK = dict(
    strand_op=0.85,
    edge_op=1.0,
    rib_op=0.45,
    strand_w=1.4,
    edge_w=2.4,
)


def square_svg(canvas=512):
    """The mark, centred on a transparent square canvas of `canvas` units."""
    style = dict(BA.STYLE)
    style.update(ICON_INK)
    src = holo.svg(512, pulses=(), uid="icon", **BA.BAND, **style, **FIDELITY)
    vb = [float(n) for n in re.search(r'viewBox="([^"]+)"', src).group(1).split()]
    x0, y0, w, h = vb
    inner = re.sub(r"^<svg[^>]*>", "", src)
    inner = re.sub(r"</svg>$", "", inner)

    scale = (canvas * FILL) / h
    # Centre the mark's own bounding box on the canvas, in canvas units.
    tx = (canvas - w * scale) / 2 - x0 * scale
    ty = (canvas - h * scale) / 2 - y0 * scale

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{canvas}" '
        f'height="{canvas}" viewBox="0 0 {canvas} {canvas}">'
        f'<g transform="translate({tx:.3f},{ty:.3f}) scale({scale:.5f})">'
        f"{inner}</g></svg>"
    )


def png(svg_text, size, background=None):
    return cairosvg.svg2png(
        bytestring=svg_text.encode("utf-8"),
        output_width=size,
        output_height=size,
        background_color=background,
    )


def main():
    from PIL import Image

    svg_text = square_svg()
    (OUT / "brand" / "tru8-icon.svg").write_text(svg_text, encoding="utf-8")

    # Transparent everywhere except apple-touch-icon: iOS composites it onto
    # the home screen with no background of its own, so a transparent PNG
    # renders as a black tile.
    targets = [
        ("favicon.png", 64, None),
        ("apple-touch-icon.png", 180, "#ffffff"),
        ("icon-512.png", 512, None),
        ("icon-192.png", 192, None),
    ]
    for name, size, bg in targets:
        data = png(svg_text, size, bg)
        (OUT / name).write_bytes(data)
        print(f"  {name:24s} {size:4d}px  {len(data):8,d} bytes")

    # Multi-resolution .ico — browsers and Windows pick the size they need
    # rather than downscaling a 64px PNG badly.
    frames = [
        Image.open(io.BytesIO(png(svg_text, s))).convert("RGBA")
        for s in (16, 32, 48)
    ]
    frames[0].save(
        OUT / "favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48)],
        append_images=frames[1:],
    )
    print(f"  {'favicon.ico':24s} 16/32/48  "
          f"{(OUT / 'favicon.ico').stat().st_size:,d} bytes")

    # Legibility check, not decoration: at 16px an 11-strand translucent lattice
    # may collapse into a smudge. Count how much of the canvas carries usable
    # ink so the judgement is measured rather than eyeballed.
    for s in (16, 32):
        im = Image.open(io.BytesIO(png(svg_text, s))).convert("RGBA")
        alpha = im.getchannel("A")
        pixels = list(alpha.getdata())
        solid = sum(1 for p in pixels if p > 128)
        faint = sum(1 for p in pixels if 0 < p <= 128)
        print(
            f"  [{s:2d}px legibility] {solid:4d} solid px, {faint:4d} faint px "
            f"of {len(pixels)} — {100*solid/len(pixels):.1f}% carries the mark"
        )

    print(f"\nwritten to {OUT}")


if __name__ == "__main__":
    main()
