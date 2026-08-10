"""The small sibling: the same band, drawn solid, for nav and favicon.

Derived from the large one, never the other way round. `render5.py` fills the
band as a few opaque panels sorted by depth, which is exactly the property the
lattice lacks -- at 24px a translucent structure has nothing left to show, but
a solid shape still has a silhouette.

Three things have to be re-decided at this size, and none of them carry over
from the hero:

  aspect   The hero's core is 54 wide by 176 tall -- roughly 1:2.8. A nav slot
           is a horizontal band, and the mark it currently sits beside is
           1:1.34. Squaring up the figure-8 is not a style choice here, it is
           what makes the object fit the space it has to live in.

  palette  On white the two faces have to separate by VALUE, not by hue.
           Orange against pale orange collapses to one shape the moment the
           band is two pixels wide.

  detail   The light track costs a path and an animation for something that
           is sub-pixel at 24px. It earns its place around 44px and not
           before.

Run: python nav.py  ->  nav.html
"""

import re

import render5

ACCENT = "#EA580C"
INK = "#18181B"

# front face, back face. The back face is what you see through the twist, so
# it has to read as "the same object, turned away" -- not as a second colour.
PALETTES = {
    "ink + grey": dict(front=INK, back="#A1A1AA", glow=ACCENT, core="#FDBA74"),
    "brand": dict(front=ACCENT, back="#FDBA74", glow=ACCENT, core="#FFF7ED"),
    "ink + brand": dict(front=INK, back=ACCENT, glow=ACCENT, core="#FDBA74"),
    "brand + ink": dict(front=ACCENT, back="#9A3412", glow=ACCENT, core="#FFF7ED"),
}

# ax is the full width of the figure-8; ay is HALF its height, so the drawn
# aspect is roughly (ax + W) : (2*ay + W).
ASPECTS = {
    "hero 1:2.8": dict(ax=54.0, ay=88.0, lift=26.0, width=14.0),
    "1:2.0": dict(ax=58.0, ay=58.0, lift=22.0, width=14.0),
    "1:1.5": dict(ax=64.0, ay=48.0, lift=20.0, width=15.0),
    "1:1.34 (matches today)": dict(ax=68.0, ay=44.0, lift=19.0, width=16.0),
}

SIZES = (24, 32, 44, 64, 120)


def mark(size, pal, band, animate=None, uid="n"):
    """Animation earns its place around 44px and not before."""
    if animate is None:
        animate = size >= 44
    return render5.svg(size, pal=dict(pal), uid=uid, animate=animate, **band)


def aspect_of(band):
    """Height per unit width, read off the emitted SVG rather than
    re-derived -- the bounds come from the sampled rims, not from ax/ay."""
    s = render5.svg(1000, pal=dict(PALETTES["ink + grey"]), animate=False, **band)
    w = float(re.search(r'width="([\d.]+)"', s).group(1))
    h = float(re.search(r'height="([\d.]+)"', s).group(1))
    return h / w


def mark_h(height, pal, band, uid="n", animate=None):
    """Sized by HEIGHT. A nav bar constrains vertical space, so width is the
    free variable -- and a 1:2.8 mark 32px tall is only 11px wide, which the
    width-based grid hid completely."""
    width = max(1, round(height / aspect_of(band)))
    if animate is None:
        animate = height >= 44
    return render5.svg(width, pal=dict(pal), uid=uid, animate=animate, **band)


def grid_palettes(band_key="1:1.5"):
    band = ASPECTS[band_key]
    rows = []
    for i, (name, pal) in enumerate(PALETTES.items()):
        cells = "".join(
            f'<div class="c"><div class="mk">{mark_h(s, pal, band, uid=f"p{i}{s}")}'
            f"</div><span>{s}px</span></div>"
            for s in SIZES
        )
        rows.append(f'<tr><th>{name}</th><td><div class="row">{cells}</div></td></tr>')
    return (
        f"<h2>Palettes <em>at {band_key}, sized by height</em></h2>"
        f'<table>{"".join(rows)}</table>'
    )


def grid_aspects(pal_key="ink + brand"):
    pal = PALETTES[pal_key]
    rows = []
    for i, (name, band) in enumerate(ASPECTS.items()):
        w = round(SIZES[0] / aspect_of(band))
        cells = "".join(
            f'<div class="c"><div class="mk">{mark_h(s, pal, band, uid=f"a{i}{s}")}'
            f"</div><span>{s}px</span></div>"
            for s in SIZES
        )
        rows.append(
            f"<tr><th>{name}<br><em>{w}px wide at 24 tall</em></th>"
            f'<td><div class="row">{cells}</div></td></tr>'
        )
    return (
        f"<h2>Aspect <em>in {pal_key} — every mark the same HEIGHT</em></h2>"
        f'<table>{"".join(rows)}</table>'
    )


def navbars(pal_key="ink + brand", band_key="1:1.5"):
    pal, band = PALETTES[pal_key], ASPECTS[band_key]
    out = []
    for i, s in enumerate((24, 28, 32)):
        out.append(
            f'<div class="navbar">{mark_h(s, pal, band, uid=f"nb{i}")}'
            "<strong>Tru8</strong><nav><span>How it works</span>"
            "<span>Pricing</span><span>Developers</span></nav>"
            '<a class="cta">Start free</a></div>'
        )
    return (
        f"<h2>In the bar <em>{pal_key}, {band_key}</em></h2>"
        f'<div class="nav">{"".join(out)}</div>'
    )


CSS = """
body{margin:0;background:#fff;color:#6B7280;padding:24px;
 font:12px/1.6 ui-sans-serif,system-ui,-apple-system,sans-serif}
h1{color:#111827;font-size:15px;font-weight:600;margin:0 0 4px}
h2{color:#111827;font-size:13px;font-weight:600;margin:30px 0 10px}
h2 em{color:#9CA3AF;font-style:normal;font-weight:400}
p.i{margin:0 0 6px;max-width:68ch}
table{border-collapse:collapse}
th{text-align:left;font-weight:500;color:#374151;font-size:12px;
 padding:0 18px 0 0;white-space:nowrap;vertical-align:middle}
td{padding:0}
tr+tr th,tr+tr td{border-top:1px solid #F3F4F6}
.row{display:flex;align-items:flex-end;gap:22px;padding:12px 0}
.c{display:flex;flex-direction:column;align-items:center;gap:5px}
.c span{font-size:10px;color:#9CA3AF}
.mk{display:flex;align-items:flex-end;min-height:120px}
.nav{border:1px solid #E5E7EB;border-radius:10px;overflow:hidden;max-width:820px}
.navbar{display:flex;align-items:center;gap:9px;padding:11px 16px;
 background:rgba(255,255,255,.8)}
.navbar+.navbar{border-top:1px solid #F3F4F6}
.navbar strong{color:#111827;font-size:15px;letter-spacing:-.01em}
.navbar nav{margin-left:auto;display:flex;gap:18px;color:#6B7280;font-size:13px}
.cta{margin-left:18px;background:#EA580C;color:#fff;font-size:12px;
 padding:6px 12px;border-radius:6px}
"""


def page():
    return (
        "<!doctype html><meta charset=utf-8><title>nav sibling</title>"
        f"<style>{CSS}</style>"
        "<h1>The small sibling — same band, drawn solid</h1>"
        '<p class="i">The lattice has nothing left to show at 24px; a solid '
        "shape still has a silhouette. Aspect, palette and whether the light "
        "track survives all have to be re-decided at this size — none of them "
        "carry over from the hero.</p>" + grid_aspects() + grid_palettes() + navbars()
    )


if __name__ == "__main__":
    open("nav.html", "w", encoding="utf-8").write(page())
    print("nav.html written")
