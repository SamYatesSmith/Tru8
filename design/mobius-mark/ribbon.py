"""The mark drawn, not rendered.

Centreline: the bowls-and-tangents construction (even bowls, resolved waist).
Twist:      theta(s) = pi*s/L + phase  -> one half twist per circuit.
Width:      the ribbon's APPARENT half-width is (W/2)*cos(theta) -- signed, so
            past the pinch the two edges swap sides. That swap IS the twist, and
            it is why the edge is one curve of double length.

No 3-D projection, so no accidental foreshortening: every proportion is chosen.
"""
import math
from mark import build as build_core

def bez(p0, p1, p2, p3, t):
    u = 1 - t
    return (u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0],
            u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1])

def sample_core(kw, per_seg=90):
    """Dense samples of the constructed figure-8 centreline, in order."""
    S, meta = build_core(**kw)
    order = [S['up_in']] + list(S['top_arc']) + [S['dn_out']] + \
            [S['dn_in']] + list(S['bot_arc']) + [S['up_out']]
    starts = [(0.0, 0.0)]
    pts = []
    cur = (0.0, 0.0)
    for seg in order:
        p1, p2, p3 = seg
        for i in range(per_seg):
            pts.append(bez(cur, p1, p2, p3, i / per_seg))
        cur = p3
    return pts, meta

def arclen(pts):
    cum = [0.0]
    for i in range(1, len(pts)):
        cum.append(cum[-1] + math.dist(pts[i-1], pts[i]))
    total = cum[-1] + math.dist(pts[-1], pts[0])
    return cum, total

def normals(pts):
    n = []
    N = len(pts)
    for i in range(N):
        a, b = pts[(i-1) % N], pts[(i+1) % N]
        dx, dy = b[0]-a[0], b[1]-a[1]
        L = math.hypot(dx, dy) or 1.0
        n.append((-dy/L, dx/L))
    return n

class Ribbon:
    def __init__(self, core_kw, width=17.0, pinch_at=0.0, spine=5.2, per_seg=90):
        self.pts, self.meta = sample_core(core_kw, per_seg)
        self.cum, self.total = arclen(self.pts)
        self.nrm = normals(self.pts)
        self.W, self.pinch_at, self.spine = width, pinch_at, spine

    def theta(self, i):
        """Edge-on at the seam, full width opposite it.

        theta runs -pi/2 -> +pi/2 over one circuit, so cos(theta) -- the signed
        apparent half-width -- is ZERO at both ends. The face must swap there,
        and it does so where the band has no width, which is why the swap is
        invisible. A linear 0 -> pi twist instead swaps the face at FULL width
        and lays a hard seam across the ribbon.
        """
        f = ((self.cum[i] / self.total) - self.pinch_at) % 1.0
        return math.pi * f - math.pi / 2.0

    def half(self, i):
        return (self.W / 2.0) * math.cos(self.theta(i))

    def edge(self, i, side=+1):
        c, n, h = self.pts[i], self.nrm[i], self.half(i)
        return (c[0] + side*h*n[0], c[1] + side*h*n[1])

    def face_front(self, i):
        return math.cos(self.theta(i)) >= 0

    def pinch_indices(self):
        out = []
        for i in range(len(self.pts)):
            j = (i+1) % len(self.pts)
            if self.face_front(i) != self.face_front(j):
                out.append(j)
        return out

    def waist_indices(self, tol=3.0):
        """Where the centreline passes through the crossing (near the origin)."""
        out, inside = [], False
        for i, p in enumerate(self.pts):
            near = math.hypot(*p) < tol
            if near and not inside: out.append(i); inside = True
            elif not near: inside = False
        return out
