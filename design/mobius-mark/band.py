"""The Mobius band as one unbroken surface. No cuts, no folds, no gaps.

Corrections to everything before this:
  * The surface is CONTINUOUS. Where it appears to cross itself nothing
    touches -- the core is lifted in z so the two passes are far apart in
    depth. The nearer simply hides the farther. Nothing is trimmed.
  * The band has CONSTANT width. It looks narrower where it turns edge-on to
    you; that is foreshortening, not a fold. Nothing necks to a point.
  * The twist is UNIFORM: exactly pi per circuit, spread evenly. Smooth
    everywhere, so no corner can exist anywhere on the surface or on any path
    across it.
  * The view is very nearly straight-on, so the proportions are the ones drawn
    rather than whatever a camera angle did to them. The small tilt exists only
    so the band never becomes literally zero-width.
  * The light sits ON the surface at a constant lateral coordinate. Because the
    band's parametrisation flips that coordinate each circuit, its route closes
    after TWO laps -- the Mobius property arrives as a consequence of riding
    the surface, not as something imposed.
"""
import math

TAU = 2 * math.pi

def _n(v):
    m = math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2]) or 1.0
    return (v[0]/m, v[1]/m, v[2]/m)

def _x(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])

class Band:
    def __init__(self, ax=54.0, ay=88.0, lift=26.0, width=14.0, phase=0.0):
        self.ax, self.ay, self.lift, self.W, self.phase = ax, ay, lift, width, phase

    def core(self, t):
        return (0.5*self.ax*math.sin(2*t), self.ay*math.cos(t), self.lift*math.sin(t))

    def tangent(self, t, h=1e-6):
        a, b = self.core(t-h), self.core(t+h)
        return _n((b[0]-a[0], b[1]-a[1], b[2]-a[2]))

    def frame(self, t):
        T = self.tangent(t)
        B = _n(_x(T, (0.0, 0.0, 1.0)))     # lies in the xy plane
        N = _n(_x(B, T))
        return B, N

    def wvec(self, t):
        B, N = self.frame(t)
        th = t/2.0 + self.phase           # uniform half twist per circuit
        c, s = math.cos(th), math.sin(th)
        return (c*B[0]+s*N[0], c*B[1]+s*N[1], c*B[2]+s*N[2])

    def at(self, t, v):
        """Point on the surface at lateral coordinate v in [-W/2, +W/2]."""
        c, w = self.core(t), self.wvec(t)
        return (c[0]+v*w[0], c[1]+v*w[1], c[2]+v*w[2])

    def rim(self, t, side=+1):
        return self.at(t, side*self.W/2.0)

def project(p, tilt=14.0):
    """Near enough straight-on that the drawn proportions survive: 14 degrees
    costs 3% of the height and stops the band ever being exactly edge-on."""
    a = math.radians(tilt)
    x, y, z = p
    return (x, -(y*math.cos(a) - z*math.sin(a)), y*math.sin(a) + z*math.cos(a))
