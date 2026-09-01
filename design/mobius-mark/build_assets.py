"""Emit the brand SVGs the web app actually loads.

These are generated artefacts, not hand artwork -- rerun this and commit the
output whenever the geometry or lighting changes. Nothing in `web/` should be
edited by hand.

Why files rather than inline JSX: the mark is static generated art, so it
belongs in `public/` where the browser caches it once, rather than in the JS
bundle where it is re-parsed on every page. SMIL keeps running inside an
`<img>` (browsers use "secure animated mode" there -- declarative animation
allowed, script not), so the pulse still travels.

Two builds of each, because motion has to be refusable: `prefers-reduced-motion`
and the existing `animated={false}` prop both switch to the static file.

Run: python build_assets.py
"""

import pathlib
import re

import holo
import light

OUT = pathlib.Path(__file__).resolve().parents[2] / "web" / "public" / "brand"

ACCENT = "#EA580C"

# On white the ramp is reversed -- see light.LIGHT_STOPS. Brightness becomes
# ink, because you cannot add light to a page already at maximum.
ONWHITE = dict(bg=None, glow=ACCENT, core="#9A3412", stops=light.LIGHT_STOPS)

# --- THE MARK ----------------------------------------------------------------
# There is ONE logo. The nav mark is the hero mark rendered smaller -- not a
# sibling, not a simplified cousin. Founder instruction, 2026-08-10, after a
# build in which nav and hero carried different band geometry (1:1.39 against
# 1:2.15) and different strand counts, i.e. two different objects wearing the
# same name.
#
# So BAND and STYLE below are shared by every asset and must stay that way.
# Anything that changes the object's proportions or its lattice belongs here,
# once, where both sizes inherit it.
BAND = dict(ax=54.0, ay=88.0, lift=26.0, width=14.0)

STYLE = dict(
    strands=11,
    rib_count=76,
    strand_op=0.30,
    strand_w=0.60,
    edge_op=0.55,
    edge_w=1.1,
    rib_op=0.20,
    **ONWHITE,
)

# Sampling is the ONLY thing allowed to differ between sizes, because it is a
# rendering-fidelity knob rather than a design one: the curve is the same curve,
# described with fewer points when it is drawn 40px wide. Keep `prec` low on the
# nav -- two decimal places on a 40px render is bytes on every page for detail
# no display can resolve.
NAV_FIDELITY = dict(samples=140, chunks=18, keys=48, prec=1)
HERO_FIDELITY = dict(samples=300, chunks=34, keys=72, prec=2)

ASSETS = [
    ("tru8-mark.svg", 64, NAV_FIDELITY, (0.5,)),
    ("tru8-mark-static.svg", 64, NAV_FIDELITY, ()),
    ("tru8-hero.svg", 520, HERO_FIDELITY, (0.12, 0.42, 0.72)),
    ("tru8-hero-static.svg", 520, HERO_FIDELITY, ()),
]

# --- ON DARK ------------------------------------------------------------------
# The homepage claim field uses the mark as its go button, on a near-black tile
# (founder decision 2026-09-01, chosen from four lightings of the SAME object:
# "T2 — orange, strands lifted"). The on-white ramp tops out at stroke-opacity
# ~0.55 because ink on white cannot go brighter than the ink; on black the same
# strands read as mud. The dark build is therefore the on-white build with every
# strand's opacity remapped linearly from its own [min, max] onto
# [DARK_FLOOR, 1.0] — geometry, widths, colours and pulses untouched, so it is
# still one logo. Derived from the same-named light asset, never drawn apart.
DARK_FLOOR = 0.30
DARK_ASSETS = [
    ("tru8-mark-dark.svg", "tru8-mark.svg"),
    ("tru8-mark-dark-static.svg", "tru8-mark-static.svg"),
]


def lift_for_dark(svg: str, floor: float = DARK_FLOOR) -> str:
    ops = [float(o) for o in re.findall(r'stroke-opacity="([\d.]+)"', svg)]
    lo, hi = min(ops), max(ops)

    def sub(m):
        o = float(m.group(1))
        return f'stroke-opacity="{min(1.0, floor + (o - lo) / (hi - lo) * (1.0 - floor)):.3f}"'

    return re.sub(r'stroke-opacity="([\d.]+)"', sub, svg)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    aspects = {}
    for name, size, fidelity, pulses in ASSETS:
        svg = holo.svg(size, pulses=pulses, uid=name[:-4], **BAND, **STYLE, **fidelity)
        assert "<rect" not in svg, f"{name} must be transparent"
        assert svg.startswith(
            "<svg xmlns="
        ), f"{name} needs an xmlns to load standalone"
        w = float(re.search(r'width="([\d.]+)"', svg).group(1))
        h = float(re.search(r'height="([\d.]+)"', svg).group(1))
        # Ratio comes from the viewBox, not the width/height attributes: the
        # latter are rounded to whole pixels, so a 64px render and a 520px
        # render of the SAME object disagree in the third decimal place.
        vb = [float(n) for n in re.search(r'viewBox="([^"]+)"', svg).group(1).split()]
        aspects[name] = vb[3] / vb[2]
        (OUT / name).write_text(svg, encoding="utf-8")
        print(f"  {name:24s} {len(svg):8,d} bytes   {w:.0f}x{h:.0f}")

    for name, source in DARK_ASSETS:
        svg = lift_for_dark((OUT / source).read_text(encoding="utf-8"))
        (OUT / name).write_text(svg, encoding="utf-8")
        print(f"  {name:24s} {len(svg):8,d} bytes   (lifted from {source})")

    # One logo means one aspect ratio. If these ever diverge the nav and the
    # hero have become different objects again -- which is exactly the fault
    # this file was restructured to make impossible.
    lo, hi = min(aspects.values()), max(aspects.values())
    assert hi - lo < 0.005, f"assets disagree on aspect ratio: {aspects}"
    print(
        f"\n  ASPECT = {hi:.4f}  <- mirror this in web/components/brand/tru8-mark.tsx"
    )
    print(f"\nwritten to {OUT}")


if __name__ == "__main__":
    main()
