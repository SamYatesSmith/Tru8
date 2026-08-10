"""What does the route actually do to a light riding it?

Measured, not assumed. Four quantities are available at every point of a
strand's two-lap journey, and each has a physical claim on how bright the
light should be there:

  depth    z after projection -- how near the viewer
  facing   |n.z| of the surface normal -- 1 square-on, 0 edge-on
  side     sign(n.z) -- which face of the band is turned toward you
  speed    screen arc length per unit t -- how fast it is travelling

Run: python probe_light.py
"""

import math
from band import Band, project, TAU


def normal(b, t, v):
    """Surface normal at (t, v). The band is ruled, so the normal is the
    cross product of the along-path tangent and the width vector."""
    T, w = b.tangent(t), b.wvec(t)
    return (
        T[1] * w[2] - T[2] * w[1],
        T[2] * w[0] - T[0] * w[2],
        T[0] * w[1] - T[1] * w[0],
    )


def sample(b, tilt, v, laps=2, n=720):
    rows = []
    prev = None
    for i in range(n + 1):
        t = laps * TAU * i / n
        p = project(b.at(t, v), tilt)
        nz = project(normal(b, t, v), tilt)[2] - project((0, 0, 0), tilt)[2]
        step = 0.0 if prev is None else math.hypot(p[0] - prev[0], p[1] - prev[1])
        rows.append(dict(i=i, f=i / n, t=t, x=p[0], y=p[1], z=p[2], nz=nz, step=step))
        prev = p
    rows[0]["step"] = rows[1]["step"]
    return rows


def span(vals):
    return min(vals), max(vals)


def main():
    b = Band()
    tilt = 14.0
    print(f"band ax={b.ax} ay={b.ay} lift={b.lift} W={b.W}  tilt={tilt}deg\n")

    for label, v in [("outer rim", +b.W / 2), ("centre", 0.0), ("inner rim", -b.W / 2)]:
        rows = sample(b, tilt, v)
        zs = [r["z"] for r in rows]
        nzs = [r["nz"] for r in rows]
        steps = [r["step"] for r in rows]
        zlo, zhi = span(zs)
        nabs = [abs(x) for x in nzs]

        # normalise facing against its own peak -- the raw magnitude depends on
        # the normal's length, which is not unit here.
        peak = max(nabs) or 1.0
        facing = [x / peak for x in nabs]

        slo, shi = span(steps)
        flips = sum(1 for a, c in zip(nzs, nzs[1:]) if (a > 0) != (c > 0))

        print(f"-- {label} (v={v:+.1f})")
        print(f"   depth z      {zlo:8.2f} .. {zhi:8.2f}   range {zhi-zlo:7.2f}")
        print(
            f"   facing       {min(facing):8.3f} .. {max(facing):8.3f}"
            f"   (0 = edge-on, 1 = square to viewer)"
        )
        print(
            f"   speed/step   {slo:8.3f} .. {shi:8.3f}   ratio {shi/(slo or 1):6.2f}x"
        )
        print(f"   face flips   {flips} over two laps")

        # where do the extremes fall through the journey?
        bright = max(rows, key=lambda r: r["z"])
        dark = min(rows, key=lambda r: r["z"])
        fast = max(rows, key=lambda r: r["step"])
        slow = min(rows, key=lambda r: r["step"])
        print(
            f"   nearest at   {bright['f']:.3f} of route,  farthest at {dark['f']:.3f}"
        )
        print(f"   fastest at   {fast['f']:.3f} of route,  slowest  at {slow['f']:.3f}")

        # face-flip positions -- these are the moments the light passes
        # through the surface turning edge-on
        fl = [
            round((rows[i]["f"] + rows[i + 1]["f"]) / 2, 3)
            for i in range(len(rows) - 1)
            if (nzs[i] > 0) != (nzs[i + 1] > 0)
        ]
        print(f"   flips at     {fl}")
        print()

    # does the route close after two laps, and only two?
    v = b.W / 2
    p0 = b.at(0.0, v)
    p1 = b.at(TAU, v)
    p2 = b.at(2 * TAU, v)
    d = lambda a, c: math.dist(a, c)
    print(
        f"closure: after 1 lap {d(p0,p1):.2f} units from start "
        f"(band width {b.W}), after 2 laps {d(p0,p2):.2f}"
    )


if __name__ == "__main__":
    main()
