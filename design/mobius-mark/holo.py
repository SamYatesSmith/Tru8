"""Luminous lattice, not a solid mark.

The whole class of problems that has dogged this -- occlusion, weave order,
gaps at the crossing, the glow popping in and out -- came from drawing opaque
shapes. A translucent structure has none of them: everything shows through
everything, depth reads as brightness, and nothing ever needs hiding.

Strands run at constant lateral positions across the band. Because the band
rolls, they converge where it turns edge-on and fan out where it faces you --
so the narrow point becomes the crossover, which is what it should always have
been.
"""

import math

import light
from band import Band, project, TAU


def depth_range(b, tilt, n=240):
    zs = []
    for i in range(n + 1):
        t = TAU * i / n
        for v in (-b.W / 2, 0, b.W / 2):
            zs.append(project(b.at(t, v), tilt)[2])
    return min(zs), max(zs)


def strand(b, tilt, v, laps=2, n=420):
    return [project(b.at(laps * TAU * i / n, v), tilt) for i in range(n + 1)]


def seg_paths(pts, chunks, zlo, zhi, colour, base_w, base_op, dim=0.32, prec=2):
    """One strand, split so brightness can follow depth. Nearer = brighter and
    a shade wider; farther recedes instead of being cut away."""
    out, step = [], max(1, len(pts) // chunks)
    for i in range(0, len(pts) - 1, step):
        seg = pts[i : i + step + 1]
        if len(seg) < 2:
            continue
        z = sum(p[2] for p in seg) / len(seg)
        f = (z - zlo) / ((zhi - zlo) or 1.0)
        op = base_op * (dim + (1 - dim) * f)
        w = base_w * (0.72 + 0.5 * f)
        d = "M " + " L ".join(f"{p[0]:.{prec}f},{p[1]:.{prec}f}" for p in seg)
        out.append(
            f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{w:.2f}" '
            f'stroke-opacity="{op:.3f}" stroke-linecap="round"/>'
        )
    return "".join(out)


def ribs(b, tilt, count, zlo, zhi, colour, op=0.28):
    out = []
    for i in range(count):
        t = TAU * i / count
        a, c = project(b.rim(t, -1), tilt), project(b.rim(t, +1), tilt)
        z = (a[2] + c[2]) / 2
        f = (z - zlo) / ((zhi - zlo) or 1.0)
        out.append(
            f'<path d="M {a[0]:.2f},{a[1]:.2f} L {c[0]:.2f},{c[1]:.2f}" '
            f'fill="none" stroke="{colour}" stroke-width="{0.5 + 0.5*f:.2f}" '
            f'stroke-opacity="{op * (0.3 + 0.7*f):.3f}"/>'
        )
    return "".join(out)


def _anim(attr, vals, times, dur, delay):
    return (
        f'<animate attributeName="{attr}" values="{vals}" keyTimes="{times}" '
        f'dur="{dur}s" begin="{delay}s" repeatCount="indefinite" '
        f'calcMode="linear"/>'
    )


def pulse(pts, prof, colour, core, dur, tail, delay, keys=96, stops=None, prec=2):
    """A light whose brightness follows the route it is on.

    A dashed stroke has ONE paint for the whole path, so brightness cannot
    vary along it directly. But the dash's position is a known linear
    function of time -- at time fraction T it covers path fraction
    [T, T+tail] -- so animating the paint in lockstep puts the right
    brightness on the pulse wherever it happens to be. The lookup is
    shifted by half a tail so the colour describes the middle of the
    visible pulse rather than its leading edge.
    """
    d = "M " + " L ".join(f"{p[0]:.{prec}f},{p[1]:.{prec}f}" for p in pts)
    P, seg = 1000.0, 1000.0 * tail
    frames = light.decimate(prof, keys, shift=tail / 2.0)
    times = ";".join(f"{f:.4f}" for f, _ in frames)
    bright = [o["bright"] for _, o in frames]

    out = []
    #  width   base   colour  hue-follows-brightness
    for w, op, col, hue in [
        (5.0, 0.10, colour, False),
        (3.0, 0.22, colour, False),
        (1.7, 0.50, colour, True),
        (0.9, 0.95, core, True),
    ]:
        # Never fully extinguish the halo -- a light that vanishes reads as
        # a fault. It recedes to a quarter and comes back.
        ops = ";".join(f"{op * (0.25 + 0.75 * b):.3f}" for b in bright)
        wds = ";".join(f"{w * (0.55 + 0.65 * b):.2f}" for b in bright)
        a = [
            _anim("stroke-opacity", ops, times, dur, delay),
            _anim("stroke-width", wds, times, dur, delay),
        ]
        if hue:
            cols = ";".join(
                light.shade(b, **({"stops": stops} if stops else {})) for b in bright
            )
            a.append(_anim("stroke", cols, times, dur, delay))
        out.append(
            f'<path d="{d}" pathLength="{P:.0f}" fill="none" stroke="{col}" '
            f'stroke-width="{w}" stroke-linecap="round" stroke-opacity="{op}" '
            f'stroke-dasharray="{seg:.1f} {P-seg:.1f}">'
            f'<animate attributeName="stroke-dashoffset" from="0" to="{-P:.0f}" '
            f'dur="{dur}s" begin="{delay}s" repeatCount="indefinite"/>'
            f'{"".join(a)}</path>'
        )
    return "".join(out)


def svg(
    size=560,
    tilt=14.0,
    phase=0.0,
    strands=11,
    rib_count=76,
    uid="h",
    glow="#F97316",
    core="#FFEDD5",
    bg="#08080b",
    dur=11.0,
    tail=0.11,
    pulses=(0.12, 0.42, 0.72),
    lightkw=None,
    stops=None,
    samples=420,
    chunks=46,
    keys=96,
    prec=2,
    strand_w=0.85,
    strand_op=0.50,
    edge_w=1.5,
    edge_op=0.85,
    rib_op=0.28,
    **bandkw,
):
    lightkw = dict(lightkw or {})
    b = Band(phase=phase, **bandkw)
    zlo, zhi = depth_range(b, tilt)
    lines, allpts = [], []
    for i in range(strands):
        v = (-b.W / 2) + b.W * i / (strands - 1)
        pts = strand(b, tilt, v, n=samples)
        allpts.append(pts)
        edge = i in (0, strands - 1)
        lines.append(
            seg_paths(
                pts,
                chunks,
                zlo,
                zhi,
                glow,
                edge_w if edge else strand_w,
                edge_op if edge else strand_op,
                prec=prec,
            )
        )
    # Each pulse rides one strand, so it gets that strand's own lighting --
    # the rims are half a journey out of phase in depth, which is why the
    # three pulses never blaze together.
    shots = []
    for k, f in enumerate(pulses):
        i = int(f * (strands - 1))
        v = (-b.W / 2) + b.W * i / (strands - 1)
        prof = light.profile(b, tilt, v, **lightkw)
        shots.append(
            pulse(
                allpts[i],
                prof,
                glow,
                core,
                dur,
                tail,
                k * dur / len(pulses),
                keys=keys,
                stops=stops,
                prec=prec,
            )
        )
    anim = "".join(shots)
    xs = [p[0] for s in allpts for p in s]
    ys = [p[1] for s in allpts for p in s]
    pad = 16
    x0, y0 = min(xs) - pad, min(ys) - pad
    w, h = max(xs) - min(xs) + 2 * pad, max(ys) - min(ys) + 2 * pad
    # bg=None leaves the mark transparent. Anything sitting on the nav's
    # bg-white/80 + backdrop-blur MUST be transparent -- an opaque white rect
    # punches a visible hole through the blur.
    plate = (
        ""
        if bg is None
        else f'<rect x="{x0:.1f}" y="{y0:.1f}" width="{w:.1f}" '
        f'height="{h:.1f}" fill="{bg}"/>'
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" '
        f'height="{round(size*h/w)}" viewBox="{x0:.1f} {y0:.1f} {w:.1f} {h:.1f}">'
        f"{plate}"
        f'{ribs(b, tilt, rib_count, zlo, zhi, glow, rib_op)}{"".join(lines)}{anim}</svg>'
    )
