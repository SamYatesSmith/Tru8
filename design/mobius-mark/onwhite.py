"""The mark on the light theme -- naive, then re-derived.

The live surface is #FFFFFF (globals.css --surface; the nav is bg-white/80),
so this is the hardest case there is, not a soft grey.

The naive panel is the honest answer to "what does it look like": the dark
palette with the background swapped. It fails, and it fails in a specific and
predictable way -- the BRIGHTEST moment of the journey disappears, because
the ramp peaks at #FFEDD5 against a #FFFFFF page. Everything the lighting work
was for is exactly what you cannot see.

The rest re-derive it for subtractive rendering. See LIGHT_STOPS in light.py.

Run: python onwhite.py  ->  onwhite.html
"""

import holo
import light

WHITE = "#FFFFFF"
ACCENT = "#EA580C"

CASES = [
    (
        "Naive — dark palette, white page",
        "the honest answer. The blaze peaks at #FFEDD5 against #FFFFFF, so the "
        "brightest moment of the journey is the one you cannot see",
        dict(
            bg=WHITE,
            glow="#F97316",
            core="#FFEDD5",
            strand_op=0.22,
            strand_w=0.55,
            edge_op=0.48,
            edge_w=1.0,
            rib_op=0.14,
        ),
    ),
    (
        "Re-derived — brightness as ink",
        "ramp reversed end for end: pale wash where it recedes, deep burnt "
        "orange at the blaze. Lattice weights lifted, because pale orange on "
        "white carries far less than orange on black",
        dict(
            bg=WHITE,
            glow=ACCENT,
            core="#9A3412",
            stops=light.LIGHT_STOPS,
            strand_op=0.30,
            strand_w=0.60,
            edge_op=0.55,
            edge_w=1.1,
            rib_op=0.20,
        ),
    ),
    (
        "Re-derived, quieter lattice",
        "same lighting, structure pulled back so the light carries more of it",
        dict(
            bg=WHITE,
            glow=ACCENT,
            core="#9A3412",
            stops=light.LIGHT_STOPS,
            strand_op=0.18,
            strand_w=0.50,
            edge_op=0.38,
            edge_w=0.95,
            rib_op=0.11,
        ),
    ),
    (
        "Re-derived on the raised surface",
        "#F9FAFB rather than pure white — what it looks like on a card rather "
        "than the nav bar",
        dict(
            bg="#F9FAFB",
            glow=ACCENT,
            core="#9A3412",
            stops=light.LIGHT_STOPS,
            strand_op=0.30,
            strand_w=0.60,
            edge_op=0.55,
            edge_w=1.1,
            rib_op=0.20,
        ),
    ),
]


def page(size=330):
    cells = []
    for i, (title, note, kw) in enumerate(CASES):
        svg = holo.svg(size, uid=f"w{i}", **kw)
        cells.append(
            f'<figure><div class="m">{svg}</div>'
            f"<figcaption><b>{title}</b><br>{note}</figcaption></figure>"
        )
    return (
        "<!doctype html><meta charset=utf-8><title>the mark on white</title>"
        "<style>body{margin:0;background:#FFFFFF;color:#6B7280;"
        "font:12px/1.6 ui-sans-serif,system-ui,sans-serif;padding:24px}"
        "h1{color:#111827;font-size:15px;font-weight:600;margin:0 0 4px}"
        "p.i{margin:0 0 20px;max-width:66ch}"
        ".g{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-start}"
        "figure{margin:0;background:#fff;border:1px solid #E5E7EB;"
        "border-radius:10px;padding:14px;width:360px}"
        ".m{display:flex;justify-content:center}"
        "figcaption{margin-top:10px;font-size:11px;min-height:4.2em}"
        "b{color:#111827;font-weight:600;font-size:12px}"
        ".nav{margin:28px 0 0;border:1px solid #E5E7EB;border-radius:10px;"
        "overflow:hidden}"
        ".navbar{display:flex;align-items:center;gap:10px;padding:10px 16px;"
        "border-bottom:1px solid #F3F4F6;background:rgba(255,255,255,.8)}"
        ".navbar strong{color:#111827;font-size:15px;letter-spacing:-.01em}"
        ".navbar nav{margin-left:auto;display:flex;gap:18px;color:#6B7280;"
        "font-size:13px}"
        ".pad{padding:26px 16px;color:#9CA3AF;font-size:12px}</style>"
        "<h1>The mark on the light theme</h1>"
        '<p class="i">The live surface is pure #FFFFFF and the nav is '
        "bg-white/80, so this is the hardest case, not a soft grey. Against "
        "black, light is additive and bright runs toward white. Against white "
        "you cannot add light to light — the page is already at maximum — so "
        "brightness has to become ink instead, and the ramp reverses end for "
        "end.</p>"
        f'<div class="g">{"".join(cells)}</div>'
        f"{navstrip()}"
    )


def navstrip():
    """At the size it would actually be used. This is the whole question --
    the hero reading and the nav reading are different objects, and 28px is
    where you find out which one this is."""
    kw = dict(
        bg=WHITE,
        glow=ACCENT,
        core="#9A3412",
        stops=light.LIGHT_STOPS,
        strand_op=0.30,
        strand_w=0.60,
        edge_op=0.55,
        edge_w=1.1,
        rib_op=0.20,
    )
    rows = []
    for n, px in enumerate((24, 32, 44, 64)):
        mark = holo.svg(px, uid=f"n{n}", **kw)
        rows.append(
            '<div class="navbar">' + mark + "<strong>Tru8</strong>"
            "<nav><span>How it works</span><span>Pricing</span>"
            "<span>Developers</span></nav></div>"
            f'<div class="pad">{px}px wide — the mark is ~1.6x taller '
            "than it is wide, so this is the nav-height question</div>"
        )
    return (
        '<h1 style="margin-top:34px">At nav size</h1>'
        '<p class="i">Same mark, same lighting, at the widths a nav bar '
        "would really ask for. Eleven strands and seventy-six ribs have to "
        "survive being drawn a few dozen pixels across.</p>"
        f'<div class="nav">{"".join(rows)}</div>'
    )


if __name__ == "__main__":
    open("onwhite.html", "w", encoding="utf-8").write(page())
    print("onwhite.html written")
