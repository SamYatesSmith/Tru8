"""How bright is the light, and what colour, at each point of its journey?

The route is not uniform, so a light riding it should not be either. Four
quantities vary along the way and each has a physical claim on brightness.
Every one is a separately weighted term, so any of them can be dialled to
zero to see what it was contributing.

  depth    Nearer is brighter. Measured swing is +-38 units on a band 14
           wide, so this is the largest signal available and the one the
           old constant-paint pulse threw away entirely.

  facing   The band is a surface, not a wire. Square-on it presents its
           full emitting area; edge-on it presents almost none, so the
           light narrows to a glint and dims. Measured range is a complete
           0.001 -> 1.000, twice per journey.

  side     A half twist per circuit turns the far face toward the viewer
           once per lap. Then you are seeing the light THROUGH a
           translucent band: dimmer, and pushed toward ember. Measured
           flips at 0.281 and 0.781 of the journey -- exactly half a
           journey apart, which is the Mobius property with a timestamp.

  speed    A constant emitter smears its output over whatever length it
           covers. Racing through the crossing it thins and dims; dwelling
           at the bowl ends it banks up and blazes. Measured 3.5x on the
           rims. This is the term that reads as gravity.

Brightness multiplies the terms, so each weight is an exponent: 0 disables
that term, 1 applies it as measured, >1 exaggerates it.
"""

import math
from band import Band, project, TAU


def normal(b, t, v):
    """Normal to the ruled surface at (t, v): tangent x width vector."""
    T, w = b.tangent(t), b.wvec(t)
    return (
        T[1] * w[2] - T[2] * w[1],
        T[2] * w[0] - T[0] * w[2],
        T[0] * w[1] - T[1] * w[0],
    )


def _clamp(x, lo=0.0, hi=1.0):
    return lo if x < lo else hi if x > hi else x


def _lerp(a, b, f):
    return a + (b - a) * f


def route(b, tilt, v, laps=2, n=720):
    """Sample the journey, carrying the raw physics at every point."""
    origin_z = project((0.0, 0.0, 0.0), tilt)[2]
    rows, prev = [], None
    for i in range(n + 1):
        t = laps * TAU * i / n
        p = project(b.at(t, v), tilt)
        nz = project(normal(b, t, v), tilt)[2] - origin_z
        step = 0.0 if prev is None else math.hypot(p[0] - prev[0], p[1] - prev[1])
        rows.append(dict(f=i / n, x=p[0], y=p[1], z=p[2], nz=nz, step=step))
        prev = p
    rows[0]["step"] = rows[1]["step"]
    return rows


def profile(
    b,
    tilt,
    v,
    laps=2,
    n=720,
    w_depth=1.0,
    w_facing=1.0,
    w_side=1.0,
    w_speed=0.6,
    depth_floor=0.32,
    facing_floor=0.25,
    through=0.60,
    speed_gain=0.85,
):
    """Brightness in 0..1 at each sample of the journey, plus the terms that
    made it, so a caller can inspect or plot any single contribution."""
    rows = route(b, tilt, v, laps, n)

    zs = [r["z"] for r in rows]
    zlo, zhi = min(zs), max(zs)
    zspan = (zhi - zlo) or 1.0

    nabs = [abs(r["nz"]) for r in rows]
    npeak = max(nabs) or 1.0

    steps = sorted(r["step"] for r in rows)
    ref = steps[len(steps) // 2] or 1.0  # median pace, not mean

    out = []
    for r in rows:
        depth = _lerp(depth_floor, 1.0, (r["z"] - zlo) / zspan)
        facing = _lerp(facing_floor, 1.0, abs(r["nz"]) / npeak)
        near = r["nz"] > 0
        side = 1.0 if near else through
        speed = _clamp((ref / (r["step"] or ref)) ** speed_gain, 0.35, 1.9)

        b_ = (depth**w_depth) * (facing**w_facing) * (side**w_side) * (speed**w_speed)

        out.append(
            dict(
                f=r["f"],
                x=r["x"],
                y=r["y"],
                depth=depth,
                facing=facing,
                side=side,
                speed=speed,
                near=near,
                bright=b_,
            )
        )

    peak = max(o["bright"] for o in out) or 1.0
    for o in out:
        o["bright"] = _clamp(o["bright"] / peak)
    return out


# --- colour -----------------------------------------------------------------
# A hot emitter run down through its own falloff: white-hot core, through the
# brand orange, into a deep ember as it recedes and turns away. Same family
# throughout, so it never stops reading as one light.
EMBER = (0x7C, 0x2D, 0x12)
GLOW = (0xF9, 0x73, 0x16)
CORE = (0xFF, 0xED, 0xD5)

DARK_STOPS = (EMBER, GLOW, CORE)

# On white the whole model inverts, and not by preference -- by physics.
#
# Against black, light is ADDITIVE: more energy means more photons, so bright
# runs toward white and the peak of the journey is the most luminous point on
# the page. Against white you cannot add light to light. The page is already
# at maximum, so a luminous object can only be rendered by what it SUBTRACTS.
# Brightness becomes ink: the peak is the most saturated, deepest mark, and
# the dim passages fade out toward the paper.
#
# So the ramp reverses end for end. Pale wash where the light recedes behind
# the band, brand orange through the middle, deep burnt orange at the blaze.
# The peak deliberately stops at #9A3412 rather than going near-black -- past
# that it stops reading as a hot thing and starts reading as ink.
WASH = (0xFF, 0xE4, 0xCC)
LIGHT_STOPS = (WASH, (0xEA, 0x58, 0x0C), (0x9A, 0x34, 0x12))


def shade(bright, stops=(EMBER, GLOW, CORE), knee=0.62):
    """Two-segment ramp. The knee sits high so most of the journey lives in
    the orange and only genuine peaks go white -- a light that is white
    everywhere has no journey."""
    a, b, c = stops
    if bright <= knee:
        f = bright / (knee or 1.0)
        lo, hi = a, b
    else:
        f = (bright - knee) / ((1.0 - knee) or 1.0)
        lo, hi = b, c
    r = round(_lerp(lo[0], hi[0], f))
    g = round(_lerp(lo[1], hi[1], f))
    bl = round(_lerp(lo[2], hi[2], f))
    return f"#{r:02X}{g:02X}{bl:02X}"


def decimate(prof, keys=96, shift=0.0):
    """Thin the profile to the number of keyframes actually worth emitting.

    `shift` moves the lookup along the route -- the visible dash has length,
    so the paint should describe its middle rather than its leading edge.
    """
    n = len(prof)
    out = []
    for k in range(keys + 1):
        f = k / keys
        j = int(round(((f + shift) % 1.0) * (n - 1)))
        out.append((f, prof[j]))
    return out
