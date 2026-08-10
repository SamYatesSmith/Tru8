"""The light's journey, laid out flat.

Freezing the pulse at points around its two laps shows in one image what the
animation only reveals over eleven seconds: where it blazes, where it recedes
behind the band, and where it narrows to a glint as the surface turns edge-on.

Run: python strip.py   ->  strip.html
"""

import light
from band import Band
from holo import depth_range, ribs, seg_paths, strand


def frozen_pulse(pts, prof, f, colour, core, tail=0.11):
    """One pulse standing still at fraction f, painted as the route says."""
    d = "M " + " L ".join(f"{p[0]:.2f},{p[1]:.2f}" for p in pts)
    P, seg = 1000.0, 1000.0 * tail
    n = len(prof)
    o = prof[int(round(((f + tail / 2.0) % 1.0) * (n - 1)))]
    b = o["bright"]
    out = []
    for w, op, hue in [
        (5.0, 0.10, False),
        (3.0, 0.22, False),
        (1.7, 0.50, True),
        (0.9, 0.95, True),
    ]:
        col = light.shade(b) if hue else colour
        out.append(
            f'<path d="{d}" pathLength="{P:.0f}" fill="none" stroke="{col}" '
            f'stroke-width="{w * (0.55 + 0.65 * b):.2f}" stroke-linecap="round" '
            f'stroke-opacity="{op * (0.25 + 0.75 * b):.3f}" '
            f'stroke-dasharray="{seg:.1f} {P-seg:.1f}" '
            f'stroke-dashoffset="{-f * P:.1f}"/>'
        )
    return "".join(out), o


def cell(b, tilt, v, prof, f, size, glow, core, strands, rib_count):
    zlo, zhi = depth_range(b, tilt)
    lines, allpts = [], []
    for i in range(strands):
        vv = (-b.W / 2) + b.W * i / (strands - 1)
        pts = strand(b, tilt, vv)
        allpts.append(pts)
        edge = i in (0, strands - 1)
        lines.append(
            seg_paths(
                pts, 46, zlo, zhi, glow, 1.5 if edge else 0.85, 0.85 if edge else 0.5
            )
        )
    ride = strand(b, tilt, v)
    shot, o = frozen_pulse(ride, prof, f, glow, core)
    xs = [p[0] for s in allpts for p in s]
    ys = [p[1] for s in allpts for p in s]
    pad = 16
    x0, y0 = min(xs) - pad, min(ys) - pad
    w, h = max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad
    svg = (
        f'<svg width="{size}" height="{round(size*h/w)}" '
        f'viewBox="{x0:.1f} {y0:.1f} {w:.1f} {h:.1f}">'
        f'{ribs(b, tilt, rib_count, zlo, zhi, glow)}{"".join(lines)}{shot}</svg>'
    )
    return svg, o


def page(
    frames=12,
    size=200,
    tilt=14.0,
    strands=11,
    rib_count=76,
    glow="#F97316",
    core="#FFEDD5",
    lightkw=None,
):
    b = Band()
    v = b.W / 2  # outer rim, where the swing is largest
    prof = light.profile(b, tilt, v, **(lightkw or {}))
    cells = []
    for k in range(frames):
        f = k / frames
        svg, o = cell(b, tilt, v, prof, f, size, glow, core, strands, rib_count)
        face = "near" if o["near"] else "far (through the band)"
        cells.append(
            f'<figure><div class="m">{svg}</div><figcaption>'
            f"<b>{f:.2f}</b> of the journey<br>"
            f'brightness <b>{o["bright"]:.2f}</b> '
            f'<span class="sw" style="background:{light.shade(o["bright"])}"></span>'
            f'{light.shade(o["bright"])}<br>'
            f'depth {o["depth"]:.2f} &middot; facing {o["facing"]:.2f} &middot; '
            f'speed {o["speed"]:.2f}<br>{face}'
            f"</figcaption></figure>"
        )
    return (
        "<!doctype html><meta charset=utf-8><title>the light's journey</title>"
        "<style>body{margin:0;background:#08080b;color:#a1a1aa;"
        "font:12px/1.5 ui-sans-serif,system-ui,sans-serif;padding:24px}"
        "h1{color:#fafafa;font-size:15px;font-weight:600;margin:0 0 4px}"
        "p{margin:0 0 20px;max-width:60ch}"
        ".g{display:flex;flex-wrap:wrap;gap:14px}"
        "figure{margin:0;background:#0e0e12;border:1px solid #1c1c22;"
        "border-radius:8px;padding:10px}"
        ".m{display:flex;justify-content:center}"
        "figcaption{margin-top:8px;text-align:center;font-size:11px}"
        "b{color:#fafafa;font-weight:600}"
        ".sw{display:inline-block;width:9px;height:9px;border-radius:2px;"
        "vertical-align:middle;margin:0 4px}</style>"
        "<h1>The light's journey, frozen</h1>"
        "<p>Same mark, same pulse, stopped at twelve points around its two laps. "
        "Brightness is the product of four measured terms: how near it is, how "
        "square the band is to you, which face is turned toward you, and how "
        "fast it is travelling.</p>"
        f'<div class="g">{"".join(cells)}</div>'
    )


if __name__ == "__main__":
    open("strip.html", "w", encoding="utf-8").write(page())
    print("strip.html written")
