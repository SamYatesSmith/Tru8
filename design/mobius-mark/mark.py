"""Generate a constructed figure-8 mark: elliptical bowls + tangent strands.

Outputs the centreline as cubic beziers. Every property the critique named is
an input here, not an accident of hand-placed control points.
"""
import math

def ellipse_tangent_from_origin(a, b, cy, sign):
    """Tangency points of the two tangents from O to an ellipse (a,b) at (0,cy).

    Solved in the circle space (x/a, y/b), then mapped back.
    sign: +1 top bowl, -1 bottom bowl.
    """
    D = abs(cy) / b
    if D <= 1.0:
        raise ValueError(f"waist inside bowl: |cy|/b = {D:.3f} <= 1")
    beta = math.acos(1.0 / D)
    # circle-space touch points, then map back to real space
    tR = (a * math.sin(beta), cy - sign * b * math.cos(beta) * 1.0)
    tL = (-tR[0], tR[1])
    return tR, tL, beta

def ellipse_point(a, b, cy, th):
    return (a * math.cos(th), cy + b * math.sin(th))

def ellipse_tangent_dir(a, b, th):
    """Unit tangent of the ellipse at parameter th (direction of increasing th)."""
    dx, dy = -a * math.sin(th), b * math.cos(th)
    n = math.hypot(dx, dy)
    return (dx / n, dy / n)

def theta_of(a, b, cy, pt):
    return math.atan2((pt[1] - cy) / b, pt[0] / a)

def arc_beziers(a, b, cy, th0, th1, ccw=True):
    """Elliptical arc th0->th1 as cubic beziers, <=90 deg per segment."""
    if ccw:
        while th1 <= th0: th1 += 2 * math.pi
    else:
        while th1 >= th0: th1 -= 2 * math.pi
    span = th1 - th0
    n = max(1, math.ceil(abs(span) / (math.pi / 2)))
    step = span / n
    k = 4.0 / 3.0 * math.tan(step / 4.0)
    segs, th = [], th0
    for _ in range(n):
        p0 = ellipse_point(a, b, cy, th)
        p3 = ellipse_point(a, b, cy, th + step)
        d0 = ellipse_tangent_dir(a, b, th)
        d3 = ellipse_tangent_dir(a, b, th + step)
        s0 = math.hypot(-a * math.sin(th), b * math.cos(th))
        s3 = math.hypot(-a * math.sin(th + step), b * math.cos(th + step))
        p1 = (p0[0] + k * d0[0] * s0, p0[1] + k * d0[1] * s0)
        p2 = (p3[0] - k * d3[0] * s3, p3[1] - k * d3[1] * s3)
        segs.append((p1, p2, p3))
        th += step
    return segs

def connector(pA, dirA, pB, dirB, ease=0.28):
    """Cubic from pA to pB leaving along dirA and arriving along dirB.

    ease pulls the handles out along the bowl tangents so curvature blends out
    of the arc instead of snapping to zero -- the flat-spot cure.
    """
    L = math.hypot(pB[0] - pA[0], pB[1] - pA[1])
    p1 = (pA[0] + dirA[0] * L * ease, pA[1] + dirA[1] * L * ease)
    p2 = (pB[0] - dirB[0] * L * ease, pB[1] - dirB[1] * L * ease)
    return (p1, p2, pB)

def build(a_top, b_top, a_bot, b_bot, d_top, d_bot, ease=0.28):
    """Return (segments, meta). Segments = ordered list of ('M'|'C', pts...)."""
    tTR, tTL, _ = ellipse_tangent_from_origin(a_top, b_top, d_top, +1)
    tBR, tBL, _ = ellipse_tangent_from_origin(a_bot, b_bot, -d_bot, -1)

    thTR = theta_of(a_top, b_top, d_top, tTR)
    thTL = theta_of(a_top, b_top, d_top, tTL)
    thBR = theta_of(a_bot, b_bot, -d_bot, tBR)
    thBL = theta_of(a_bot, b_bot, -d_bot, tBL)

    top_arc = arc_beziers(a_top, b_top, d_top, thTR, thTL, ccw=True)     # over the top
    bot_arc = arc_beziers(a_bot, b_bot, -d_bot, thBR, thBL, ccw=False)   # under the bottom

    dTR = ellipse_tangent_dir(a_top, b_top, thTR)
    dTL = ellipse_tangent_dir(a_top, b_top, thTL)
    dBR = ellipse_tangent_dir(a_bot, b_bot, thBR)
    dBL = ellipse_tangent_dir(a_bot, b_bot, thBL)

    # Strand 1: O -> TR -> (top arc) -> TL -> O    [the NE-going strand]
    # Strand 2: O -> BR -> (bottom arc) -> BL -> O [the SE-going strand]
    # Entering O the direction is TL->O; leaving it is O->BR. Straight-through.
    # Direction signs, corrected 2026-08-06. Two faults put EIGHT cusps in the
    # centreline -- the path stopped dead and reversed at every junction:
    #
    #  1. The bottom arc is traversed CLOCKWISE, so its travel direction at the
    #     touch points is the NEGATIVE of ellipse_tangent_dir (which is stated
    #     for increasing theta). The connectors were matching the un-negated
    #     tangent, so connector and arc met head-on.
    #  2. Arriving at the crossing, the direction of travel is toward the NEXT
    #     touch point, not away from it. The old code passed -tBR / -tTR, which
    #     is the direction pointing back where it came from.
    #
    # A cusp is invisible in the filled ribbon but not in the motion: anything
    # travelling the curve reverses through 180 degrees on the spot.
    dBRt = (-dBR[0], -dBR[1])
    dBLt = (-dBL[0], -dBL[1])
    up_in  = connector((0.0, 0.0), _unit(tTR), tTR, dTR, ease)
    dn_out = connector(tTL, dTL, (0.0, 0.0), _unit(tBR), ease)
    dn_in  = connector((0.0, 0.0), _unit(tBR), tBR, dBRt, ease)
    up_out = connector(tBL, dBLt, (0.0, 0.0), _unit(tTR), ease)

    meta = {
        "waist_deg": 2 * math.degrees(math.atan2(abs(tTR[0]), abs(tTR[1]))),
        "width": 2 * max(a_top, a_bot),
        "height": (d_top + b_top) + (d_bot + b_bot),
        "top": d_top + b_top, "bottom": -(d_bot + b_bot),
    }
    meta["aspect"] = meta["width"] / meta["height"]
    meta["min_sector"] = min(meta["waist_deg"], 180 - meta["waist_deg"])
    return dict(up_in=up_in, top_arc=top_arc, dn_out=dn_out,
                dn_in=dn_in, bot_arc=bot_arc, up_out=up_out), meta

def _unit(v):
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n)

def fmt(pts):
    return " ".join(f"{x:.2f},{y:.2f}" for x, y in pts)

def strand_paths(S):
    """Two strand paths (each a half of the 8) + the full continuous loop."""
    s1 = ["M 0.00,0.00", f"C {fmt(S['up_in'])}"] + \
         [f"C {fmt(s)}" for s in S["top_arc"]] + [f"C {fmt(S['dn_out'])}"]
    s2 = ["M 0.00,0.00", f"C {fmt(S['dn_in'])}"] + \
         [f"C {fmt(s)}" for s in S["bot_arc"]] + [f"C {fmt(S['up_out'])}"]
    loop = s1 + s2[1:]
    return " ".join(s1), " ".join(s2), " ".join(loop)

if __name__ == "__main__":
    for name, kw in {
        "compact":  dict(a_top=38, b_top=29, a_bot=40, b_bot=31, d_top=40, d_bot=42),
        "balanced": dict(a_top=36, b_top=31, a_bot=38, b_bot=33, d_top=45, d_bot=47),
        "tall":     dict(a_top=33, b_top=32, a_bot=35, b_bot=34, d_top=52, d_bot=54),
    }.items():
        S, m = build(**kw)
        print(f"{name:<10} {m['width']:.0f} x {m['height']:.0f}  aspect {m['aspect']:.2f}"
              f"  waist {m['waist_deg']:.0f}deg  min sector {m['min_sector']:.0f}deg")
