# Jurisdiction scope gate — the mechanical analogue of F1

**Date:** 2026-08-06
**Cause:** production check `757f02c2`, recorded in
`audit/2026-08-06_f1_temporal_gate_extension.md` § "Live proof attempt"
**Touches:** new `app/utils/jurisdiction_scope.py`, `app/pipeline/claim_map_analyzer.py`
(`_apply_jurisdiction_scope`), `app/pipeline/runner.py` (`attach_claim_jurisdiction`),
`app/core/config.py`

---

## The failure this exists for

A 15p live check meant to prove the F1 temporal gate fires instead found a
different way for a settled fact to read as contested:

```
claim:   "UK consumer price inflation fell to 1.7 percent in the twelve
          months to September 2024."          [TRUE — ONS says exactly this]
state:   disputed  (close_split, weighted 5 supports vs 3 challenges)
challenge: cso.ie — the IRISH Central Statistics Office
           "CPI rose by 2.7% between September 2024 and September 2025"
```

**F1 was right not to touch it.** The temporal gate fires only when none of the
evidence's periods match the element's, and that snippet names September 2024
repeatedly. No period mismatch exists. The mismatch is jurisdictional.

### Why this cannot be a prompt rule

The decisive detail, and the reason NF-11 applies in its original form:

> **the snippet never says "Ireland", or "Irish", or anything else locating it.**

Only the *domain* reveals the country. The mapper was given a title, tier, type and
snippet — nothing in that payload identifies the jurisdiction, so no instruction
could have been obeyed. This is the same structure as F1 itself, where the payload
carried no date and the prompt had forbidden cross-period support for months.

## The rule

Where a claim is scoped to ONE country-level jurisdiction and an evidence item is a
**national official source of a different country**, the relationship is re-labelled
`context` — never deleted — before the state is derived, with a receipt in
`basis.jurisdiction_scope`.

**Symmetric**, exactly as F1 is: it scopes `supports` as readily as `challenges`.
Another country's national statistics bear on a UK figure in neither direction, and
a gate that only removed challenges would be a sycophancy mechanism — the thing
invariant #7 exists to forbid. A mutation that narrows it to `challenges` only is
killed by a test.

### Three limits, each holding the false-positive rate down

| Limit | Why |
|---|---|
| **Official sources only** — statistics offices, central banks, government hosts | An Irish newspaper reporting ON UK inflation is legitimate evidence. Foreign **press** is not a jurisdiction mismatch and is never touched. |
| **Country-level claims only** — `UK` and `US` | `VALID_JURISDICTIONS` is UK/US/EU/Global. `EU` is excluded because a member state's figures are partly in scope for an EU-wide claim — a composition problem, not a jurisdiction one. `Global` because any country's data can be an instance of a global claim. |
| **The mention guard** — if the item's own text names the claim's jurisdiction, leave it alone | A foreign statistics office publishing an international comparison that includes the United Kingdom *is* talking about the United Kingdom. Mirrors F1's "one matching mention is enough". |

**Supranational bodies are deliberately absent from the map** — World Bank, IMF,
OECD, WHO, UN, Eurostat all report on many countries including ours, so their data
about the UK is legitimate and must never be scoped on domain alone.

`.gov` as a bare TLD resolves to US; `gov.uk`, `gov.au` and `govt.nz` end in their
own ccTLDs and are matched explicitly first, so they cannot fall through to it.

The "US" mention pattern matches `US` case-sensitively and excludes the bare
pronoun "us" — a case-insensitive match would fire on ordinary prose and suppress
the gate everywhere. Safe, but useless.

## The seam, and why it is a named function

The gate needs the claim's jurisdiction, which lives on
`claim["article_classification"]["jurisdiction"]` — already written by the runner in
both article mode (`runner.py:902`) and focused mode (`:911`), and re-attached on
Phase-2 reload (`:1369`). Nothing new to classify.

It is carried onto `claim_map["metadata"]["jurisdiction"]` because **every** mapping
path already receives that object — batch, single-claim and grounds alike — so there
is **one writer** rather than a new parameter threaded through four signatures.

`attach_claim_jurisdiction()` is a module-level function rather than four inline
lines for one reason: **a reader whose key nobody writes is the defect that hid in
`retrieve.py` for months** (it read `claim["elements"]` while decompose wrote
`claim["claim_map"]["elements"]`, so a documented stage silently never ran). The
writer is now unit-testable, and `test_jurisdiction_wiring_writer.py` also pins that
the two sides agree on the value vocabulary — if `VALID_JURISDICTIONS` ever gains a
value, that test is where the mismatch surfaces.

If the key ever stops being written the gate goes **quiet rather than crashing**,
which is safe but silent — hence the writer test.

Signing is unaffected: the manifest canonicalises claim_map **elements** (including
`basis`, so the receipt *is* signed, as F1's is), not claim_map `metadata`.

## Verification

- **57 unit tests** — tagger, wired reader seam, and the writer seam.
- **10/10 mutations killed**, one per guard: mention guard, same-country check,
  EU/Global exclusion, the `.gov` rule, the US-pronoun exclusion, the parser call,
  the receipt, the flag, **`supports` scoping (the sycophancy dial)**, and the writer.
- **1,197 pipeline tests pass** with no collateral damage. (The 42 + 2 failures in a
  full run are the two HELD test files whose fixes were taken out of the tree for
  benching — `test_society_journal_tiers.py` and `test_mapping_model_metadata.py` —
  exactly as `OPEN_WORK.md` predicts.)
- **Bench: 158 ok / 2 warn / 1 fail** — the documented pass state, sole failure the
  known-flaky `TRU-82CF-2F81`. Valid as a comparison because this changes no prompt.
- Rollback: `ENABLE_JURISDICTION_SCOPE_GATE=False`.

### The seam is PROVEN WIRED, which F1 never managed

The gate fired **zero times** across the corpus, and zero firings has two very
different causes: the gate ran and had nothing to scope, or the jurisdiction never
reached the claim_map and the gate is silently dead — the `retrieve.py` failure mode.
Absence cannot distinguish them, and today's standing lesson is that a rule which
does not fire proves nothing. So it was instrumented and replayed (free):

```
JURDEBUG elem=e1 raw_jurisdiction='UK' target='UK'
JURDEBUG   ref=…  rel=supports country='UK'   ons.gov.uk/…/consumerpriceinflation
JURDEBUG   ref=…  rel=supports country='UK'   ons.gov.uk/releases/…september2024
JURDEBUG   ref=…  rel=supports country=None   cnbc.com/2024/10/16/uk-inflation…
JURDEBUG elem=e2 raw_jurisdiction='UK' target='UK'
JURDEBUG   ref=…  rel=challenges country=None x.com/elerianm/status/…
```

Two things are established rather than assumed:

1. **The writer runs in the real pipeline path** — `raw_jurisdiction='UK'` on both
   elements. The bench drives `run_pipeline` / `run_pipeline_phase2`, the same entry
   points production uses, so `attach_claim_jurisdiction` is genuinely wired.
2. **The gate was correct to stay quiet.** Every directional ref was either our own
   country (`ons.gov.uk`, `bankofengland.co.uk`) or `None` — press and commentary
   (CNBC, a solicitors' blog, x.com), which the design deliberately never touches.
   `bls.gov` US CPI data was in the retrieval ledger but **never mapped as a
   directional ref**, so there was nothing to act on.

This is a better position than F1 reached: F1's firing was observed only via the
corpus fixture and never at the seam, whereas here the seam is confirmed live and
the silence is explained.

### Still owed
- **A corpus fixture carrying foreign official evidence**, and a
  `capture.py` matcher for `[JURISDICTION SCOPE]` to go with it. Deliberately NOT
  added yet: with no claim that exercises the gate, a matcher could only ever record
  zero, and by today's own standard a guard that cannot fail on the known break is
  decoration. Add both together.
- **Production proof.** Unit- and bench-verified only.

## Known limits, stated rather than discovered later

- **Coverage-recovery mapping is not covered.** `map_evidence_to_specific_elements`
  does not share `_parse_mapping_response`, so neither this gate nor F1 applies
  there. Matched deliberately rather than silently differing from F1.
- **The domain map is incomplete by construction**, exactly as the evidence
  classifier's academic allowlist is. It covers the national offices that actually
  surface in retrieval for UK/US economic claims. An absent domain means the gate
  does not fire — the safe direction. The structural fix would be a publisher-country
  registry, not a longer list.
- **The measure mismatch in `757f02c2` is still unaddressed.** A
  Sept-2024→Sept-2025 annual change is not "the 12 months to Sept 2024" even from
  the right country. This gate removes the item for being Irish, so the observed
  check is fixed — but a UK source making the same period-pair error would still be
  counted. Not built; noted.
- **Not yet proven in production.** Unit-verified and bench-checked only. The corpus
  claim `TRU-C1A0-0005` does carry `bls.gov` US CPI data for a UK claim, so the bench
  may exercise it; whether it does is recorded with the bench result, not assumed.
