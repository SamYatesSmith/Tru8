# Möbius mark — geometry generators

**LIVE as of 2026-08-10.** `build_assets.py` emits the four SVGs in
`web/public/brand/`, which `web/components/brand/tru8-mark.tsx` and the hero
load. Never hand-edit those SVGs — change the geometry here, rerun the builder,
commit its output.

**There is ONE logo.** The nav mark is the hero mark rendered smaller: same
band, same lattice, same proportions, fewer sample points. Until 2026-08-10 they
were two different objects (1:1.39 against 1:2.15, 7 strands against 11), which
the founder rightly called out. `BAND` and `STYLE` in `build_assets.py` are now
shared by every asset, and the builder **asserts all four agree on aspect
ratio** — so they cannot silently drift apart again. The aspect it prints must
be mirrored into `ASPECT` in `tru8-mark.tsx`.

These are parameterised generators, not static artwork. Every proportion is an
input. Run them, open the emitted HTML, change numbers, run again.

```bash
cd design/mobius-mark
python -c "import holo; open('holo.html','w',encoding='utf-8').write(
  '<!doctype html><meta charset=utf-8><style>body{margin:0;background:#08080b;'
  'display:flex;justify-content:center;padding:30px}</style>' + holo.svg(560,
  strand_op=0.22, strand_w=0.55, edge_op=0.48, edge_w=1.0, rib_op=0.14))"
python strip.py                # the light's journey, frozen at 12 points
python compare.py              # old glow vs new, across three lattice weights
python probe_light.py          # the raw measurements the lighting is built on
python -m http.server 8123     # then open http://127.0.0.1:8123/holo.html
```

Open it in a browser, not an image viewer — everything here is animated.

---

## Where this landed (read this first)

The founder's reference is a **holographic light-lattice** — a translucent
ribbon structure with many strands of light flowing along it, of the kind used
for sci-fi UI. Not a flat vector logo. `holo.py` is built to that reference and
is **the live direction**. Everything else here is either a dependency of it or
a superseded approach kept for its geometry.

The single most important thing learned: **almost every problem in this session
came from drawing opaque shapes.** Occlusion, weave order, gaps at the crossing,
the glow popping in and out — none of them exist in a translucent structure,
because everything shows through everything and depth reads as brightness. Do
not re-solve them. If you find yourself cutting a strand to make a weave, stop.

## Files

| File | Role |
|---|---|
| `band.py` | **The object.** Möbius band as one unbroken surface: figure-8 core lifted in z, uniform half-twist per circuit, constant width. Verified: the two passes are 41 units apart in depth on a 14-unit band, so the surface NEVER touches itself. Nothing needs cutting. |
| `holo.py` | **Live direction.** Luminous lattice: N strands at constant lateral positions, cross-ribs, depth-graded brightness, travelling light pulses. Built against the founder's reference. |
| `render5.py` | Solid two-tone version of the same band (front face dark, back face grey). Structurally correct — no gaps, no notches — but it is the *flat mark* reading, which the founder moved away from. Keep as the basis for a future small-size/favicon sibling. |
| `light.py` | **How bright the light is, and what colour, at each point of its journey.** Four separately weighted physical terms — set any weight to 0 to see what it was contributing. |
| `strip.py` | Diagnostic: the pulse frozen at 12 points around its two laps, each labelled with its brightness and the terms that produced it. |
| `compare.py` | Diagnostic: old constant-paint glow against the new lighting, across three lattice weights. |
| `probe_light.py` | The raw measurements. Run it before changing any lighting weight. |
| `mark.py`, `ribbon.py` | Superseded 2-D constructed approach (bowls + tangent strands). `mark.py`'s construction is still the best source of an *evenly drawn* figure-8 core if a flat mark is ever needed. Its direction-sign bug is fixed (see below). |

## Properties that are verified, not assumed

Re-run these if you touch the geometry.

- **Surface never self-intersects** — closest approach of the two passes 41.42
  units against a 14-unit band width.
- **The light closes after TWO laps, not one** — a strand at constant lateral
  position `v` lands exactly `W/2` from its start after one lap (i.e. on the
  opposite side of the band) and 0.00 from it after two. The Möbius property
  arrives from riding the surface; it is not imposed.
- **No corners anywhere** — sharpest turn between samples on the light's route
  is 1.64°.

## Faults found and fixed — do not reintroduce

Every one of these was invisible until measured, and each was found only after
the founder pointed at a symptom. Measure, don't eyeball.

1. **Eight cusps in the constructed core** (`mark.py`). Two direction-sign
   errors: connectors met each bowl head-on because the bottom arc is traversed
   clockwise (so its travel direction is the *negative* of
   `ellipse_tangent_dir`), and arrival at the crossing pointed back the way it
   came. The path stopped dead and reversed 8×/lap. Anything travelling it
   turned through 180° on the spot — this was the "right angles" complaint.
   Fixed; verified 0 normal reversals, worst step 24× → 4×, sharpest turn 1.8°.
2. **Twist spread evenly round the loop starves every bowl.** Measured band
   width 2.5 → 16.7 units *within one bowl*. If you use apparent width to show a
   twist in 2-D, this is unavoidable — which is a reason not to.
3. **Wrapping distance-to-fold into ±½ and taking `tanh`** is smooth at the fold
   and has a hard step at the ANTIPODE. The light swapped rims 0.72 of a lap
   from any twist.
4. **Filling a self-crossing ribbon as one polygon** (outer rim forward, inner
   rim back) pinches where the strands overlap and fuses them at the waist. It
   is why there was no crossover and why there was a step at the foot.
5. **Flicker was page load, not the mark** — 92 concurrent SMIL animations and
   23 live Gaussian blurs re-rasterising per frame. `holo.py` uses **no filters
   at all**; the glow is stacked strokes. Preview ONE mark at a time.
6. **Dash tiling**: paths declare `pathLength="1000"` so the dash tiles exactly
   however the browser measures the geometry. Never compute the total yourself.

## The light is lit by its route (2026-08-07)

The pulse used to carry **one paint for the whole journey** — same hue, same
brightness, from start to finish — because a `stroke-dasharray` stroke has
exactly one colour and cannot vary along its own path. So the light was the
only part of the mark that ignored the geometry it was riding.

**Measured first** (`probe_light.py`), because none of this should be guessed:

| Quantity | Measured over two laps |
|---|---|
| depth | ±38 units, on a band only 14 wide — the largest signal available |
| facing | a complete 0.001 → 1.000; the band turns dead edge-on twice |
| side | flips at **0.281 and 0.781** of the journey — exactly half a journey apart |
| speed | **3.5×** on the rims; fastest through the crossing, slowest at the bowls |

Each earns a term in `light.profile()`, multiplied, so each weight is an
exponent and **0 disables that term**:

- **depth** — nearer is brighter.
- **facing** — the band is a surface, not a wire. Edge-on it presents almost no
  emitting area, so the light narrows to a glint. This is why the crossing now
  reads as a crossing.
- **side** — a half twist per circuit turns the far face toward you once per
  lap; then you are seeing the light *through* the band, so it dims and pushes
  toward ember. This is the Möbius property made visible.
- **speed** — a constant emitter smears its output over the length it covers.
  It thins racing through the crossing and banks up bright dwelling at the
  bowls. **This is the term that reads as gravity.**

**How it is drawn.** The dash's position is a known linear function of time — at
time fraction *T* it covers path fraction *[T, T+tail]* — so `stroke-opacity`,
`stroke-width` and `stroke` are animated in lockstep with `stroke-dashoffset`,
sampled half a tail ahead so the paint describes the pulse's middle rather than
its leading edge. One path per layer, **no filters**, 42 animations against the
92 that caused yesterday's flicker.

**Verified in the browser, not asserted:** on one element across a cycle the
stroke travels `rgb(148,58,19)` at 0.320 opacity → `rgb(254,212,174)` at 0.895
— a 2.8× brightness swing, a full ember-to-white hue traverse, and 1.83× on
width. The control case (all four weights 0) is constant 1.0, so the "as it was"
panel in `compare.py` is genuinely the old behaviour.

**The mark never goes unlit.** At every instant at least one of the three pulses
is at ≥0.386 brightness; 0% of the cycle falls below 0.35. 27% sits below 0.50,
which is the quiet passage, not a fault — a screenshot can easily catch one.

### This also settled the "more air" note
The frozen strip showed the lighting computed correctly and then *lost*, because
the strands it travels over were nearly as bright as it is. **The lattice and
the light were one problem.** `strand_op`/`strand_w`/`edge_op`/`edge_w`/`rib_op`
are now parameters; the preview ships at `0.22 / 0.55 / 0.48 / 1.0 / 0.14`.
`compare.py` shows that choice against a quieter one — an open call.

## On the light theme (2026-08-07) — the ramp must reverse

Run `python onwhite.py`. The live surface is `--surface: #FFFFFF` and the nav is
`bg-white/80`, so this is pure white, not a soft grey.

**The naive swap does not merely look weaker — it inverts.** Measured as WCAG
contrast against the page:

| | peak of the journey | dim passage |
|---|---|---|
| dark theme, `#08080b` | **17.46 : 1** | 2.38 : 1 |
| naive swap onto `#FFFFFF` | **1.15 : 1** | 8.41 : 1 |
| re-derived on `#FFFFFF` | **7.31 : 1** | 1.33 : 1 |

On the naive panel the blaze is the *least* visible thing on the page and the
receding ember is the *loudest*. Every physical term still computes correctly;
the display simply runs them backwards.

**Why, and it is not a matter of taste.** Against black, light is **additive** —
more energy means more photons, so bright runs toward white. Against white you
cannot add light to light: the page is already at maximum, so a luminous object
can only be rendered by what it **subtracts**. Brightness has to become ink.
`LIGHT_STOPS` in `light.py` reverses the ramp end for end — pale wash where the
light recedes, brand orange through the middle, deep burnt `#9A3412` at the
blaze. It deliberately stops short of near-black: past that it stops reading as
a hot thing and starts reading as ink.

Re-derived, the light theme carries **5.5× dynamic range against the dark
theme's 7.3×** — about three quarters. Usable, but it is a drawing of a
luminous object rather than a luminous object. That is inherent to the white
page, not a tuning failure, and no amount of parameter work will recover it.

### The nav question is now answered, with evidence
`onwhite.py` ends with the mark in a real nav bar at 24 / 32 / 44 / 64px. **At
24 and 32px it is a pale orange smudge** — lattice, ribs and light all gone. It
only becomes legible around 64px wide, which at this 1:1.6 aspect is ~102px
tall and far beyond any nav. The README's earlier claim that this will not
reduce is now demonstrated rather than asserted. **A simplified sibling is
required**, derived from `render5.py` (solid two-tone), not from `holo.py`.

## WIRED INTO THE APP (2026-08-07)

**`web/components/brand/tru8-mark.tsx` is no longer hand-authored artwork.** It
loads generated files. Run `python build_assets.py` and commit its output;
never edit anything in `web/public/brand/` by hand.

| File | Where it goes |
|---|---|
| `tru8-mark.svg` / `-static.svg` | nav, mobile nav, dashboard nav, footer |
| `tru8-hero.svg` / `-static.svg` | landing hero, right column |

**Founder decisions taken here:** the nav keeps the luminous lattice rather than
a solid sibling; the hero mark **replaced** the illustrative record fragment;
both sit **straight on the white** with no dark panel.

**Files, not inline JSX** — the mark is static art, so it belongs in `public/`
where it is cached once rather than in the JS bundle where it is re-parsed per
page. **SMIL keeps running inside `<img>`** (browsers use "secure animated
mode": declarative animation allowed, script not) — verified by pixel-diffing
rendered frames rather than assumed: 687 pixels changed in 1.8s on the nav mark,
1709 on the hero, **0** on both static files.

**The nav mark is 1:1.39 by construction**, solved against the mark it replaced
so all five call sites keep their exact layout. Verified: emitted `40x56`, and
the old component computed `round(40 * 1.39) = 56`.

Two things must stay transparent and standalone-loadable, and both are asserted
in `build_assets.py` rather than trusted: **`bg=None`** (an opaque rect punches
a visible hole through the nav's `bg-white/80 backdrop-blur`) and **`xmlns`**
(without it an `.svg` file will not load via `<img>` at all).

⚠️ **Payload came from `samples`/`chunks`, and for a while the `keys`/`prec`
knobs were declared but never reached `pulse()` or `seg_paths()`** — a patch
that silently missed after the formatter reflowed the call sites. Numbers
quoted before that was fixed were mislabelled. Now wired: nav is **5.2KB
gzipped animated, 3.6KB static**, against 20KB at hero sampling.

Motion is refusable two ways — `prefers-reduced-motion` and the existing
`animated={false}` prop (the footer uses it) — and both resolve to a genuinely
frozen file, not a paused one.

## Open at close of play

- ✅ **Air — done**, and it turned out to be the same problem as the lighting.
- ⏳ **Triangulated bracing** rather than straight rungs — still open. The ribs
  currently read as hatching across the band, not as structure.
- ⏳ A call between the two air settings in `compare.py` ("with air" vs "mostly
  air"), and on strand count / pulse count / speed.
- ⏳ **The `#08080b` background is doing work.** Every setting here was judged
  against near-black. The live nav is the light theme — the lattice weights and
  the ember end of the ramp will both need re-deriving there, and ember on white
  is the part most likely to fail.
- **This is a hero object and will not reduce to 24px.** Nothing with this
  structure does. Expect it to live on the landing page and in-product, with a
  simplified sibling for nav and favicon — derive the small one from the large,
  not the other way round.
- Nothing is wired in, nothing is committed, and `tru8-mark.tsx` is untouched.
