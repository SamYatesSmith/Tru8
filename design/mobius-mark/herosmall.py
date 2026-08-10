"""Option B: keep the luminous lattice, shrink it honestly.

The earlier "it will not reduce" verdict was reached at 24 and 32px. That was
the wrong test -- the desktop nav and the dashboard both ask for 40px wide, and
only the footer uses 24. So this re-runs it at the sizes actually called for.

Two things have to move together, and neither is a style choice:

  aspect   The hero band is 1:2.37, so at 40px wide it is 95px tall and simply
           does not fit a nav bar. `ay` is solved to put h/w at 1.39, matching
           the live mark's slot exactly.

  density  Eleven strands and seventy-six ribs are tuned for 560px. At 40px
           the strands land ~1.4px apart, so they merge into a single band and
           the lattice reads as noise. Fewer, further apart, is not a
           simplification of the idea -- it is the same idea at a size where
           you can still see between the strands.

Run: python herosmall.py  ->  herosmall.html
"""

import re

import holo
import light

WHITE = "#FFFFFF"
ACCENT = "#EA580C"

# The nav is white, so the ramp is the reversed one -- see light.LIGHT_STOPS.
ONWHITE = dict(bg=WHITE, glow=ACCENT, core="#9A3412", stops=light.LIGHT_STOPS)

HERO_BAND = dict(ax=54.0, ay=88.0, lift=26.0, width=14.0)
# Solved below; h/w = 1.39 so it drops into the live mark's slot.
NAV_BAND = dict(ax=62.0, ay=56.2, lift=21.0, width=17.0)

CALL_SITES = (24, 32, 40)


def aspect_of(**kw):
    s = holo.svg(1000, **kw)
    w = float(re.search(r'width="([\d.]+)"', s).group(1))
    h = float(re.search(r'height="([\d.]+)"', s).group(1))
    return h / w


def solve_ay(target=1.39, ax=62.0, lift=21.0, width=17.0, **kw):
    lo, hi = 12.0, 90.0
    for _ in range(34):
        mid = (lo + hi) / 2
        a = aspect_of(ax=ax, ay=mid, lift=lift, width=width, **kw)
        if a < target:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 1)


def mark(
    size, band, strands=11, rib_count=76, pulses=(0.12, 0.42, 0.72), uid="h", **kw
):
    o = dict(ONWHITE)
    o.update(kw)
    return holo.svg(
        size, strands=strands, rib_count=rib_count, pulses=pulses, uid=uid, **band, **o
    )


# Weights that suit a small mark: the structure has to carry on white at a few
# dozen pixels, so it cannot be as faint as the hero's.
SMALL = dict(strand_op=0.34, strand_w=0.75, edge_op=0.62, edge_w=1.5, rib_op=0.22)


def _row(cells):
    return f'<div class="row">{cells}</div>'


def _cell(svg, label):
    return f'<div class="c">{svg}<span>{label}</span></div>'


def sec_aspect():
    a_hero = aspect_of(**HERO_BAND)
    a_nav = aspect_of(**NAV_BAND)
    hero = "".join(
        _cell(mark(s, HERO_BAND, uid=f"ah{s}"), f"{s}px") for s in CALL_SITES
    )
    navb = "".join(
        _cell(mark(s, NAV_BAND, uid=f"an{s}", **SMALL), f"{s}px") for s in CALL_SITES
    )
    return (
        f"<h2>1 · The aspect has to move first</h2>"
        f'<p class="i">Hero proportions are <b>1:{a_hero:.2f}</b> — at 40px wide '
        f"that is {round(40*a_hero)}px tall, which no nav bar has room for. "
        f"Re-proportioned to <b>1:{a_nav:.2f}</b> it occupies the same slot as "
        f"the mark you have today.</p>"
        f'<div class="lbl">hero proportions, unchanged</div>{_row(hero)}'
        f'<div class="lbl">re-proportioned for the slot</div>{_row(navb)}'
    )


def sec_strands():
    rows = []
    for n in (5, 7, 9, 11):
        cells = "".join(
            _cell(
                mark(s, NAV_BAND, strands=n, rib_count=28, uid=f"s{n}{s}", **SMALL),
                f"{s}px",
            )
            for s in CALL_SITES + (64,)
        )
        rows.append(f"<tr><th>{n} strands</th><td>{_row(cells)}</td></tr>")
    return (
        "<h2>2 · How many strands survive</h2>"
        '<p class="i">Eleven are tuned for 560px. At 40px they land about '
        "1.4px apart and merge into one band — the lattice stops being a "
        "lattice and becomes noise.</p>"
        f'<table>{"".join(rows)}</table>'
    )


def sec_ribs(strands=7):
    rows = []
    for n in (0, 16, 28, 48, 76):
        cells = "".join(
            _cell(
                mark(
                    s, NAV_BAND, strands=strands, rib_count=n, uid=f"r{n}{s}", **SMALL
                ),
                f"{s}px",
            )
            for s in CALL_SITES + (64,)
        )
        lab = "no ribs" if n == 0 else f"{n} ribs"
        rows.append(f"<tr><th>{lab}</th><td>{_row(cells)}</td></tr>")
    return (
        f"<h2>3 · Ribs, at {strands} strands</h2>"
        '<p class="i">The cross-ribs are the first thing to become '
        "hatching when the band is a few pixels wide.</p>"
        f'<table>{"".join(rows)}</table>'
    )


def sec_pulses(strands=7, ribs=28):
    rows = []
    for name, p in [
        ("3 pulses", (0.12, 0.42, 0.72)),
        ("2 pulses", (0.2, 0.7)),
        ("1 pulse", (0.5,)),
    ]:
        cells = "".join(
            _cell(
                mark(
                    s,
                    NAV_BAND,
                    strands=strands,
                    rib_count=ribs,
                    pulses=p,
                    uid=f"u{len(p)}{s}",
                    **SMALL,
                ),
                f"{s}px",
            )
            for s in CALL_SITES + (64,)
        )
        rows.append(f"<tr><th>{name}</th><td>{_row(cells)}</td></tr>")
    return (
        "<h2>4 · How many lights</h2>"
        '<p class="i">Three pulses at 560px read as a lattice carrying '
        "traffic. At 40px they may just read as flicker.</p>"
        f'<table>{"".join(rows)}</table>'
    )


def sec_bar(strands=7, ribs=28):
    bars = "".join(
        f'<div class="navbar">'
        f'{mark(s, NAV_BAND, strands=strands, rib_count=ribs, uid=f"b{s}", **SMALL)}'
        "<strong>TRU<i>8</i></strong>"
        "<nav><span>How it works</span><span>Pricing</span>"
        "<span>Developers</span></nav>"
        '<a class="cta">Start free</a></div>'
        for s in CALL_SITES
    )
    return (
        f"<h2>5 · In the bar <em>{strands} strands, {ribs} ribs</em></h2>"
        f'<div class="nav">{bars}</div>'
    )


def sec_chip():
    """Option C: stop fighting the white page -- bring the dark with it.

    The luminous treatment needs a dark ground; that is physics, not taste.
    On a chip it keeps the EXACT hero palette and ramp, reads strongly at
    24px because it is light against dark again, and is the same shape an
    app icon is. Nothing is simplified away.
    """

    def chip(px, strands=7, ribs=28, radius=None):
        # Fill the chip properly: aim the mark's HEIGHT at 0.78 of the chip,
        # so width follows from the 1.39 aspect. At 0.62 it sat in a sea of
        # black and read as an empty tile.
        inner = round(px * 0.78 / 1.39)
        m = holo.svg(
            inner,
            strands=strands,
            rib_count=ribs,
            pulses=(0.2, 0.7),
            uid=f"c{px}",
            bg="#0B0B0F",
            glow="#F97316",
            core="#FFEDD5",
            **NAV_BAND,
            **SMALL,
        )
        r = radius if radius is not None else round(px * 0.26)
        return (
            f'<div class="chip" style="width:{px}px;height:{px}px;'
            f'border-radius:{r}px">{m}</div>'
        )

    sizes = "".join(_cell(chip(px), f"{px}px") for px in (24, 32, 40, 56))
    bars = "".join(
        f'<div class="navbar">{chip(px)}'
        "<strong>TRU<i>8</i></strong>"
        "<nav><span>How it works</span><span>Pricing</span>"
        "<span>Developers</span></nav>"
        '<a class="cta">Start free</a></div>'
        for px in (28, 32, 40)
    )
    return (
        "<h2>6 · Option C — bring the dark ground with it</h2>"
        '<p class="i">The luminous look needs a dark ground; that is '
        "physics, not preference. On a chip it keeps the <b>exact hero "
        "palette and ramp</b> — nothing simplified away — and reads "
        "strongly at 24px because it is light against dark again. It is "
        "also the shape every app icon already is.</p>"
        f"{_row(sizes)}"
        f'<div class="nav">{bars}</div>'
    )


CSS = """
.chip{display:flex;align-items:center;justify-content:center;overflow:hidden;
 background:#0B0B0F;flex:none}
.chip svg{display:block}
body{margin:0;background:#fff;color:#6B7280;padding:26px;
 font:12px/1.6 ui-sans-serif,system-ui,-apple-system,sans-serif}
h1{color:#111827;font-size:15px;font-weight:600;margin:0 0 4px}
h2{color:#111827;font-size:13px;font-weight:600;margin:32px 0 6px}
h2 em{color:#9CA3AF;font-style:normal;font-weight:400}
p.i{margin:0 0 10px;max-width:70ch}
b{color:#111827;font-weight:600}
.lbl{font-size:11px;color:#9CA3AF;margin-top:10px}
table{border-collapse:collapse}
th{text-align:left;font-weight:500;color:#374151;font-size:12px;
 padding:0 18px 0 0;white-space:nowrap;vertical-align:middle}
tr+tr th,tr+tr td{border-top:1px solid #F3F4F6}
.row{display:flex;align-items:flex-end;gap:26px;padding:10px 0}
.c{display:flex;flex-direction:column;align-items:center;gap:6px}
.c span{font-size:10px;color:#9CA3AF}
.nav{border:1px solid #E5E7EB;border-radius:10px;overflow:hidden;max-width:840px}
.navbar{display:flex;align-items:center;gap:10px;padding:12px 18px;
 background:rgba(255,255,255,.8)}
.navbar+.navbar{border-top:1px solid #F3F4F6}
.navbar strong{color:#111827;font-size:20px;font-weight:700;
 letter-spacing:-.03em;text-transform:uppercase}
.navbar strong i{color:#A1A1AA;font-weight:400;font-style:normal}
.navbar nav{margin-left:auto;display:flex;gap:20px;color:#6B7280;font-size:13px}
.cta{margin-left:20px;background:#EA580C;color:#fff;font-size:12px;
 padding:7px 13px;border-radius:6px}
"""


def page():
    return (
        "<!doctype html><meta charset=utf-8><title>hero at nav size</title>"
        f"<style>{CSS}</style>"
        "<h1>Option B — the same luminous mark, shrunk honestly</h1>"
        '<p class="i">Not a different object: the identical lattice, '
        "lighting and Möbius geometry, re-proportioned and re-tuned for "
        "the size it has to live at. On white, so the reversed ramp "
        "applies.</p>"
        + sec_aspect()
        + sec_strands()
        + sec_ribs()
        + sec_pulses()
        + sec_bar()
        + sec_chip()
    )


if __name__ == "__main__":
    print("solving aspect ...", solve_ay())
    open("herosmall.html", "w", encoding="utf-8").write(page())
    print("herosmall.html written")
