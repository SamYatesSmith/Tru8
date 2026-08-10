import math
from band import Band, project, TAU

LIGHT = dict(front="#18181b", back="#a1a1aa", glow="#EA580C", core="#FDBA74")
DARK  = dict(front="#fafafa", back="#52525b", glow="#EA580C", core="#FFF7ED")

def sample(b, tilt, n):
    rows = []
    for i in range(n + 1):
        t = TAU * i / n
        rp, rn = project(b.rim(t, +1), tilt), project(b.rim(t, -1), tilt)
        c, w = b.core(t), b.wvec(t)
        T = b.tangent(t)
        nrm = (T[1]*w[2]-T[2]*w[1], T[2]*w[0]-T[0]*w[2], T[0]*w[1]-T[1]*w[0])
        nz = project(nrm, tilt)[2] - project((0,0,0), tilt)[2]
        rows.append(dict(t=t, p=rp, q=rn, face=nz > 0, z=(rp[2]+rn[2])/2))
    return rows

def panels(rows, overlap=3):
    """Contiguous runs sharing facing and depth half -> a few filled panels.
    Neighbours overlap so no hairline can show between them."""
    out, cur = [], None
    for r in rows:
        key = (r["face"], r["z"] >= 0)
        if cur is None or cur["key"] != key:
            if cur: out.append(cur)
            tail = out[-1]["rows"][-overlap:] if out else []
            cur = dict(key=key, rows=list(tail))
        cur["rows"].append(r)
    if cur: out.append(cur)
    if len(out) > 1 and out[0]["key"] == out[-1]["key"]:
        out[0]["rows"] = out[-1]["rows"] + out[0]["rows"]; out.pop()
    elif len(out) > 1:
        out[0]["rows"] = out[-1]["rows"][-overlap:] + out[0]["rows"]
    for g in out:
        g["z"] = sum(r["z"] for r in g["rows"]) / len(g["rows"])
    return sorted(out, key=lambda g: g["z"])

def panel_d(g):
    f = " L ".join(f"{r['p'][0]:.2f},{r['p'][1]:.2f}" for r in g["rows"])
    b = " L ".join(f"{r['q'][0]:.2f},{r['q'][1]:.2f}" for r in reversed(g["rows"]))
    return f"M {f} L {b} Z"

def light_track(b, tilt, v, n=1400):
    pts, zs = [], []
    for i in range(n + 1):
        p = project(b.at(2 * TAU * i / n, v), tilt)
        pts.append(p); zs.append(p[2])
    cum = [0.0]
    for i in range(1, len(pts)):
        cum.append(cum[-1] + math.hypot(pts[i][0]-pts[i-1][0], pts[i][1]-pts[i-1][1]))
    total = cum[-1]
    d = "M " + " L ".join(f"{p[0]:.2f},{p[1]:.2f}" for p in pts)
    return d, [c / total for c in cum], zs

def vis(fracs, zs, near, op):
    vals, times = [], []
    for f, z in zip(fracs, zs):
        val = op if ((z >= 0) == near) else 0
        if not vals or val != vals[-1]:
            vals.append(val); times.append(f)
    if times: times[0] = 0.0
    return ";".join(str(x) for x in vals), ";".join(f"{x:.4f}" for x in times)

def light_layers(d, fracs, zs, near, pal, dur, tail, uid):
    P, out = 1000.0, []
    seg = P * tail
    for wid, op, col in [(6.0, 0.09, pal["glow"]), (4.0, 0.17, pal["glow"]),
                         (2.4, 0.40, pal["glow"]), (1.5, 0.95, pal["core"])]:
        ov, ot = vis(fracs, zs, near, op)
        out.append(
            f'<path d="{d}" pathLength="{P:.0f}" fill="none" stroke="{col}" '
            f'stroke-width="{wid}" stroke-linecap="round" opacity="0" '
            f'stroke-dasharray="{seg:.1f} {P-seg:.1f}">'
            f'<animate attributeName="stroke-dashoffset" from="0" to="{-P:.0f}" '
            f'dur="{dur}s" repeatCount="indefinite"/>'
            f'<animate attributeName="opacity" dur="{dur}s" repeatCount="indefinite" '
            f'calcMode="discrete" values="{ov}" keyTimes="{ot}"/></path>')
    return "".join(out)

def svg(size=320, tilt=14.0, phase=0.0, pal=None, uid="a", dur=9.0, tail=0.07,
        vfrac=0.5, n=300, animate=True, **bandkw):
    pal = pal or LIGHT
    b = Band(phase=phase, **bandkw)
    rows = sample(b, tilt, n)
    gs = panels(rows)
    far  = "".join(f'<path d="{panel_d(g)}" fill="{pal["front"] if g["key"][0] else pal["back"]}"/>'
                   for g in gs if g["z"] < 0)
    near = "".join(f'<path d="{panel_d(g)}" fill="{pal["front"] if g["key"][0] else pal["back"]}"/>'
                   for g in gs if g["z"] >= 0)
    lf = ln = ""
    if animate:
        d, fr, zs = light_track(b, tilt, vfrac * b.W / 2.0)
        lf = light_layers(d, fr, zs, False, pal, dur, tail, uid)
        ln = light_layers(d, fr, zs, True,  pal, dur, tail, uid)
    xs = [c for r in rows for c in (r["p"][0], r["q"][0])]
    ys = [c for r in rows for c in (r["p"][1], r["q"][1])]
    pad = 8
    x0, y0 = min(xs)-pad, min(ys)-pad
    w, h = max(xs)-min(xs)+2*pad, max(ys)-min(ys)+2*pad
    return (f'<svg width="{size}" height="{round(size*h/w)}" '
            f'viewBox="{x0:.1f} {y0:.1f} {w:.1f} {h:.1f}" fill="none">'
            f'{far}{lf}{near}{ln}</svg>')
