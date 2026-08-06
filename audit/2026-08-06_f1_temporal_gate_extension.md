# F1 temporal gate — closing the two misses it shipped with

**Date:** 2026-08-06
**Predecessor:** `audit/2026-08-05_agent_tier_quality_findings.md` (F1), shipped `656618b`
**Touches:** `app/utils/temporal_scope.py`, `app/pipeline/claim_map_analyzer.py`
(`_apply_temporal_scope` only), `app/core/config.py`

---

## Why this was the first thing to do today

F1 shipped as a mechanical rule that scopes evidence about a *different* period out
of an element's state count. It passed the replay bench at the documented
135 ok / 2 warn / 1 fail — **having fired zero times**. Two live checks (30p) also
failed to make it fire. So the day earned "no regression" and nothing more.

Production then supplied the proof it was still missing its own failure mode. Live
check `b0a720f8` retrieved *"UK **September-25** CPI Inflation Report"* (published
2025-10-22, snippet *"CPI increased by 3.8% YoY in September"*) and used it to
**challenge a September 2024 element** — the exact shape F1 exists to prevent,
twice over in one item.

Three nameable reasons, two of them mechanical:

| # | Miss | Kind |
|---|---|---|
| 1 | `September-25` — two-digit year behind a delimiter — was not parsed. Nor was `September-2025`: the month/year pattern required **whitespace** as the separator. | lexical |
| 2 | The snippet names a month with **no year anywhere**. Not parsed. | inference |
| 3 | The rule ignored `published_date` by design. | inference |

## The correction to an earlier belief

F1's docstring said inferring a period from silence is guessing. That still holds
for evidence that names **no** period. It does **not** hold for evidence that names
a **bare month**: `published_date` is a poor guide to the period a source *covers*,
but a good one for resolving a month the source itself *names*. A report published
22 Oct 2025 saying "in September" means September 2025.

The two halves are therefore separated, because their risk profiles differ:

- **Lexical half** — tightens parsing of a period the source **did** state. Rides
  the existing `ENABLE_TEMPORAL_SCOPE_GATE`.
- **Inferring half** — supplies a period the source **did not** state. Its own
  switch, `ENABLE_TEMPORAL_PUBLICATION_RESOLUTION`. Rolling back the riskier half
  must not take the safe half with it, and a test pins that.

## The three guards on the inferring half

Over-firing here would scope out genuine evidence and hide a real dispute —
invariant #7 breached from the other side. So:

1. **Provenance is an allowlist.** Only `page_metadata`, `engine`, `api_adapter`
   resolve anything. `url_inferred_suspect` is refused **by name** — F2 classified
   it as probably the host's upload path. Absent/unknown provenance is refused too:
   trust is opt-in.
2. **A temporal preposition must precede the month** ("in September", "to
   September"). This is what keeps the modal **"may"** out — by far the biggest
   collision in ordinary prose.
3. **The month must be capitalised.** The preposition alone still admits
   "began to march"; capitalisation alone still admits a sentence-initial "May".
   Both are required, and both are pinned by mutation.

`Month YY` with a **bare space** is deliberately NOT read as a year: "September 25"
is the 25th far more often than it is 2025, and reading a day as a year would place
the item in the wrong period and scope out on-period evidence.

The year is chosen as `published.year` when the month is at or before the
publication month, else `published.year - 1` — December named in an October report
is last December.

## Accepted residuals, recorded rather than hidden

- A **forward-looking** mention ("the target for December", published October)
  resolves to the previous December.
- A **year-only** `published_date` parses to 1 January, which skews the same
  comparison for every month after January.

Both are visible in the receipt: a scoping that rested on an inferred period
carries `period_from: "published_date"` and the `date_basis` it trusted, so a wrong
inference is auditable rather than silent (invariant #5, one level deeper). Neither
is worth a prompt or an LLM call to fix — NF-11 applies in reverse here too.

## What is proven, and what is not

**Proven:** 61 unit tests across the tagger and the wired seam, and **8/8
mutations killed** — including one for each guard above, one for each half's
rollback, and one for the receipt's provenance field. The pipeline suite is green
(1,199 passed / 44 skipped). The replay bench is a valid comparison here because
this change touches **no prompt** — cassette keys are request signatures, and only
response post-processing was altered.

**NOT proven:** that it fires in production. The same trap as yesterday is still
open — the replay corpus contains **no month-pinned claim at all**, so a green
bench cannot speak to this class either way.

## The corpus gap — closed for the GATE, still open for the EXTENSION

`TRU-C1A0-0005` was recorded live the same day (founder-approved spend): *"UK CPI
inflation was below 2% in September 2024."*, focused mode, the corpus's first and
only month-pinned claim. Two supporting pieces were needed for it to guard
anything at all:

- **`capture.py` learned to observe the gate** (`RE_TEMPORAL_SCOPE` →
  `temporal_scope_events` + a summary). Without this the bench cannot see the
  gate, so a fixture alone would still have reported green while the gate died.
- **`comparator.py` gained `temporal_scope_must_fire_on_periods`**, a hard
  invariant, because "did the gate act on a month-pinned element" is a boolean
  structural signal, not a drifting count.

**Proven at capture:** the gate fired on element `e2`, scoping 1 ref to context
on `2024-09` — F1's first observed action on a real retrieved pool rather than a
unit fixture. The guard **fails** under `ENABLE_TEMPORAL_SCOPE_GATE=False`, so it
pins real behaviour. Replay is deterministic (23 ok / 0 warn / 0 fail).

### ⚠️ What this fixture does NOT guard — measured, not assumed

Three mutation runs, all replays:

| Mutation | Result |
|---|---|
| two-digit/delimited short-year parsing disabled | claim still passes |
| month/year separator reverted to whitespace-only | claim still passes |
| `ENABLE_TEMPORAL_PUBLICATION_RESOLUTION=False` | claim still passes |

So the firing here comes from the **original** stated-period rule, and **neither
of today's halves is pinned by this fixture**. The substack *"September-25"*
report is in the pool (and pinned by URL) but is not the ref being scoped.

This is the honest position: the register's item — *"the corpus contains no
month-pinned claim at all, so the drift guard is blind"* — **is** closed, and the
gate is now guarded corpus-wide. Today's two additions remain covered by unit
tests only (61 tests, 8/8 mutations). A **second fixture whose off-period evidence
carries a two-digit year or a bare month** is owed to close that, and it needs
another `--record` run, i.e. another spend decision.

The trap worth remembering: the fixture went green, the gate genuinely fired, and
it would have been easy to write down "the extension is now covered by the bench".
Only mutating the two halves showed it is not.
