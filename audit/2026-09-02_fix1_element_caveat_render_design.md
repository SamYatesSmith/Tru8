# Fix 1 — render the element caveat on `/r/` (design review, 2026-09-02)

**Status:** REVIEWED → BUILDING same day (founder: "Go on Fix 1, build it if you have properly design reviewed it").
**Supersedes:** the one-paragraph scoping in `OPEN_WORK.md` (2026-08-24, "design APPROVED by founder"), which fixed the *colour* and the *place* but never looked at the *words*.
**Why now:** four of the five send-week notes carry a "this caveat appears only in the downloadable PDF" disclaimer (TTE, Viglione, Tapper, McSweeney). The same error was made four times because the reader's page and the record's data differ on exactly this field.

## 1. What the field actually is (verified in code + stored records)

- The mapper prompt asks for `"uncertainty": "<one sentence or null>"` and says only *"optional (null if not applicable), max one sentence"* (`claim_map_analyzer.py:269`). **There is no definition of what the sentence is for.** The model decides.
- Backend Phase B (2026-08-17, `claim_map_analyzer.py:1168-1178`) appends `uncertainty` to the caveat channel **only when the element is `supported`** — the rationale being that a supported badge must not ship while the mapper's own note undercuts it. That rule already encodes the backend's view: the note matters most where it *limits* a positive badge.
- Frontend today: `uncertainty` renders in `UnknownElementCard` (Seeker, unresolved elements only, amber) and in the Track C `claim-map/element-list.tsx` (amber, only reachable through `ClaimMapView`). On `/r/` and the dashboard roster (`ElementList.tsx`, the "ELEMENTS EXAMINED" list) it renders **nowhere**. The PDF prints it under every element.

## 2. The finding this review adds: the field mixes caveats with verdicts

15 elements across the six outreach records (TTE, Viglione, Seymour, Tapper, McSweeney ×2), read from the live public payloads:

| kind | count | examples |
|---|---|---|
| genuine limit (scope / provenance / method) | 8 | "The £22 million figure is an estimated loss, not official outturn data" · "GWIS Europe totals include Russia…" · "aerosol reduction is an amplifying mechanism rather than the sole direct trigger" · "an unpublished internal NHS England evaluation" |
| adjudication restating the badge | 5 | "**The evidence consistently refutes this element**, demonstrating…" · "The available evidence **strongly suggests** that 2026 is not the quietest year…" · "There is **strong evidence challenging** the assertion…" |
| empty | 2 | — |

Pattern: the limits sit on `supported` elements; the adjudications sit on `disputed` ones (the model summarises the direction it just assigned). "Refutes" is verdict language under the D3 lock and invariant #7 ("describes evidential limit, never adjudicates"). **Rendering the field raw would print "consistently refutes this element" on the McSweeney record the morning it is sent to a Carbon Brief editor.** The 24 Aug approval did not know this, because no stored note had said it yet.

## 3. Options

| | what | outcome on the corpus | verdict |
|---|---|---|---|
| A | render raw, all elements | 5 adjudications printed | ✗ breaches D3 |
| B | render on `supported` elements only (mirror Phase B) | hides Viglione's two GWIS caveats (both elements are `disputed`) — the exact text her note apologises for | ✗ loses the motivating case |
| **C** | **render on all states through a fail-closed lexical gate** | **15/15 correct on the corpus: 8 shown, 5 suppressed, 2 empty** | **✓ build** |
| D | fix the prompt (define the field as a limit, forbid direction words) | right at source, but re-keys every mapping cassette → bench re-record (~£0.80) + the held-reframe protocol, and fixes nothing already stored (the five send records are signed) | follow-up, not this build |

## 4. The gate (`web/lib/element-caveat.ts`)

`elementCaveatNote(uncertainty)` returns the sentence to show, or `null`:
1. **Sentinels** — `null`/`none`/`n/a`/empty → null (the Seeker's existing filter, moved to one place).
2. **Verdict lexicon** — any of `refute·false·true·prove·proven·confirm·debunk·verdict·correct·incorrect·wrong·fact-check` as a word → null.
3. **Adjudication intensifier** — `evidence|sources|data` within a short window of `strongly·consistently·clearly·overwhelmingly·conclusively·decisively`, or `strong|overwhelming|conclusive evidence` → null. This is what separates *"The evidence indicates aerosol reduction is an amplifying mechanism"* (limit, shown) from *"The available evidence strongly suggests that 2026 is not…"* (adjudication, hidden).

**Fail direction is deliberate.** Hiding a genuine caveat leaves the page as it is today (no new harm). Printing an adjudication breaks a lock on a public page (real harm). So every rule errs towards hiding. **Known residual:** an adjudication phrased without a listed word passes (a blocklist cannot close an open set — the evaluative-head lesson). The permanent fix is option D; until then the gate is a presentation guard, and the 15-sentence corpus is pinned as the unit-test fixture so any drift in either direction fails a test.

## 5. Presentation

- **Where:** `ElementList.tsx` roster rows (shared by `/r/`, the dashboard check page and the overview card — one component, one behaviour), beneath the description, after `EvidenceQualityNote`. Not on gap rows.
- **How:** the grey note idiom — mono 10px `text-zinc-500`, `NOTE ·` prefix in `text-zinc-400` uppercase tracking, `line-clamp-2` with the full sentence in `title`. **No amber, no border, no fill** (no-verdict colour lock; the Seeker's amber box is pre-existing and out of scope).
- **Copy:** the model's sentence verbatim after the gate; we never rewrite it (no hidden curation — suppression is total or nothing, and the PDF still prints every note).

## 6. Reported, not built

- **F3 scope caveats render nowhere in the web app either** — `state_derivation.caveat` ("evidence covers Europe (1980-2020), narrower than 'Europe'") and `scopeReach` are in every payload and print only in the PDF. Mechanical, never verdict-shaped; a candidate for the same NOTE row later. Out of scope per the 24 Aug instruction.
- **Prompt definition of `uncertainty`** (option D) — owed as pipeline work with a bench re-record.
- **Seeker amber** on `UnknownElementCard` — colour-lock inconsistency, untouched.

## 7. Acceptance

1. `vitest`: the 15 corpus sentences classify exactly as the table in §2; sentinels null.
2. `tsc --noEmit` clean.
3. Live on `/r/e1e5de25` (McSweeney re-run): elements 01 and 02 show their NOTE rows; element 03 ("consistently refutes") shows nothing.
4. Live on `/r/441144ac` (Viglione): both GWIS notes visible. On `/r/fa08cff7` (Seymour): nothing new appears.
5. **Then rewrite the four "PDF-only" sentences in the send sheet** — after this ships they are false, and the whole point of the fix was to stop drafting from the data.
