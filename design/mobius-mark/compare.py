"""Same lighting, three lattices -- and the old constant-paint glow for contrast.

The frozen strip showed the new lighting is being computed correctly and then
lost, because the strands it travels over are nearly as bright as it is. That
is one problem wearing two hats: the lattice needs air BEFORE the glow can
show its journey.

Run: python compare.py  ->  compare.html
"""

import holo

CASES = [
    (
        "As it was",
        "strands at full weight, and the glow with one paint for "
        "the whole route -- what the mark did yesterday",
        dict(strand_op=0.50, strand_w=0.85, edge_op=0.85, edge_w=1.5, rib_op=0.28),
        True,
    ),
    (
        "Lit, same lattice",
        "brightness now follows the route, but the lattice "
        "is still loud enough to bury it",
        dict(strand_op=0.50, strand_w=0.85, edge_op=0.85, edge_w=1.5, rib_op=0.28),
        False,
    ),
    (
        "Lit, with air",
        "strands dropped and thinned, ribs quietened -- the "
        "structure recedes and the light becomes the subject",
        dict(strand_op=0.22, strand_w=0.55, edge_op=0.48, edge_w=1.0, rib_op=0.14),
        False,
    ),
    (
        "Lit, mostly air",
        "further still: the band is implied by its rims and "
        "the light does nearly all the work",
        dict(strand_op=0.13, strand_w=0.45, edge_op=0.34, edge_w=0.9, rib_op=0.08),
        False,
    ),
]


def page(size=330):
    cells = []
    for i, (title, note, kw, flat) in enumerate(CASES):
        # `flat` reproduces the old behaviour by disabling every physical
        # term, which leaves brightness constant at 1.0 -- exactly the
        # single paint the pulse used to carry.
        lightkw = dict(w_depth=0, w_facing=0, w_side=0, w_speed=0) if flat else None
        svg = holo.svg(size, uid=f"c{i}", lightkw=lightkw, **kw)
        cells.append(
            f'<figure><div class="m">{svg}</div>'
            f"<figcaption><b>{title}</b><br>{note}</figcaption></figure>"
        )
    return (
        "<!doctype html><meta charset=utf-8><title>lattice vs light</title>"
        "<style>body{margin:0;background:#08080b;color:#a1a1aa;"
        "font:12px/1.6 ui-sans-serif,system-ui,sans-serif;padding:24px}"
        "h1{color:#fafafa;font-size:15px;font-weight:600;margin:0 0 4px}"
        "p.i{margin:0 0 20px;max-width:66ch}"
        ".g{display:flex;flex-wrap:wrap;gap:16px;align-items:flex-start}"
        "figure{margin:0;background:#0e0e12;border:1px solid #1c1c22;"
        "border-radius:10px;padding:14px;width:360px}"
        ".m{display:flex;justify-content:center}"
        "figcaption{margin-top:10px;font-size:11px;min-height:3.2em}"
        "b{color:#fafafa;font-weight:600;font-size:12px}</style>"
        "<h1>The lattice and the light are one problem</h1>"
        '<p class="i">All four are the same geometry. The first has the old '
        "constant-paint glow; the rest carry the new route-driven lighting and "
        "differ only in how loud the lattice is. Watch one pulse all the way "
        "round -- it should dim as it passes behind the band, narrow to a glint "
        "where the surface turns edge-on, and bank up bright where it slows at "
        "the bowls.</p>"
        f'<div class="g">{"".join(cells)}</div>'
    )


if __name__ == "__main__":
    open("compare.html", "w", encoding="utf-8").write(page())
    print("compare.html written")
