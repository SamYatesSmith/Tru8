# Adapter `prepare_query` audit — broad 0-yield investigation

**Status:** SCOPED, NOT STARTED (parked 2026-05-15)
**Trigger:** TRU-8723-1E97 + TRU-594B-0534 (2026-05-15) confirmed the Hansard/GOV.UK 0-yield pattern is not UK-specific. It's a broad `prepare_query` topic-phrase class spanning UK gov, US gov, academic, supranational, and weather adapters.
**Priority position:** Highest-leverage adapter quality work below the V1 line. Not blocking V1 ship.

## 2026-06-15 — UK-gov cluster DIAGNOSED + PARTIALLY FIXED (live wired probe)

**The doc's central hypothesis (`prepare_query`/`extract_topic_phrase` topic-phrase shaping) was WRONG for GOV.UK + Hansard.** A live wired probe (`scripts/probe_prepare_query.py`) found three different root causes:
1. **DOMAIN ROUTING (dominant).** GOV.UK & Hansard `is_relevant_for_domain` excluded `Finance` → fiscal/monetary claims (BoE, Autumn Statement) classify as Finance and self-excluded from the only UK primary adapters. PROVEN: same query, GOV.UK Finance=0 vs Politics=10. **FIXED + live-validated 0→10 (GOV.UK), 0→8 (Hansard).**
2. **Hansard discarded Contributions** when Debates=0 (real speech text binned). **FIXED — sentence query 0→4.**
3. **GOV.UK `NameError`** (`legal.py` undefined `targeted_query`) masking the empty-path diagnostic. **FIXED.**
- `extract_topic_phrase` is FINE for GOV.UK/Hansard (a clean single entity yields 4–10) — NOT touched.
- Tests: `tests/unit/adapters/test_legal_adapters_p2.py` (6, LLM-free). **Replay bench gate still owed (needs working LLM key).**

**BLOCKED on LLM key (rotated keys not updated locally → Google AI 400 / OpenAI 401 → rule-based fallback):**
- ONS + Companies House use the concept/entity path (`extract_concept_keyword` / `extract_entity_name`); their real query couldn't be probed (rule-based fallback starves entities). DEFER to working key.
- extract_topic_phrase entity-path validation (and Priority 2–4 clusters: PubMed/WHO/GovInfo, NOAA/WeatherAPI/Open-Meteo) likewise need a working LLM probe — re-confirm each adapter's real cause before assuming `prepare_query` shaping.

## Problem statement

API adapters across multiple domain classes return zero evidence on claims that obviously fall within their indexed corpus. Web search compensates when it works; when it doesn't (the Serper 2026-05-15 AM outage), affected checks crater to Poor.

## Evidence accumulated

| Check | Date | Claim shape | Domain/Jurisdiction | Adapters returning 0 | Adapters yielding |
|---|---|---|---|---|---|
| TRU-B56C-AF05 | 2026-05-12 | Nov 2023 Autumn Statement | Finance/UK | Hansard, GOV.UK Content API, ONS, Companies House | — |
| TRU-04E3-7F48 | 2026-05-12 | Aug 2016 BoE rate cut | Finance/UK | Hansard, GOV.UK Content API, ONS, Companies House | — |
| TRU-93AF-E2F0 | 2026-05-15 | JWST launch Dec 2021 | Science/Global | PubMed, Semantic Scholar | Wikipedia 5, OpenAlex 3, Internet Archive 7 |
| TRU-8723-1E97 | 2026-05-15 | Pfizer FDA approval Aug 2021 | Health/US | PubMed, WHO, GovInfo, Semantic Scholar | OpenAlex 3, Library of Congress 1 |
| TRU-594B-0534 | 2026-05-15 | 2024 Atlantic hurricane season | Weather/Global | NOAA CDO, WeatherAPI, Open-Meteo | — |

**Pattern:** 12 distinct adapters across 4 domain classes return 0 on claims that should hit. Only Wikipedia, OpenAlex, Library of Congress, and Internet Archive yield consistently — and those are crawl-based / OAI-PMH based adapters, not `prepare_query`-driven keyword search adapters.

## Hypothesised root cause

`prepare_query`-based adapters share a common shape: they call a Session B / NF-15 `_extract_topic_phrase` (or equivalent) to convert claim text + typed entities into a search-API-shaped query string. The hypothesis is that this shaping step is producing queries that the underlying API rejects or returns empty for, while the same claim text submitted to Google via Serper returns rich results.

Two sub-hypotheses to falsify:

**(A) Topic-phrase too narrow** — `_extract_topic_phrase` is producing fragments like "Pfizer" or "vaccine" instead of "Pfizer COVID-19 vaccine FDA approval", under-specifying the query.

**(B) Topic-phrase wrong shape for API contract** — the API expects a different parameter style than free-text keyword search. E.g., PubMed accepts MeSH terms; Hansard's `/search.json` expects member names + date ranges; NOAA CDO expects FIPS location codes (which the NF-18 fix addresses for location but not for storm-class keywords).

Likely answer: a mix of (A) and (B) per adapter. Each adapter needs its own probe.

## Investigation plan (when work resumes)

Follow the Session 7 4-step probe pattern, multiplied across adapters in priority order.

### Priority 1 — UK gov cluster (4 adapters)

Already named in the Hansard row of OPEN_WORK. Highest impact because UK Politics+Finance is a marketed claim domain and the affected adapters are the only primary anchors.

1. **Hansard** — `services/api_adapters/government.py` `prepare_query` / `_extract_topic_phrase`
2. **GOV.UK Content API** — same module
3. **ONS Economic Statistics** — `services/api_adapters/economic.py`
4. **Companies House** — `services/api_adapters/government.py`; also blocked by SC-16 missing API key

### Priority 2 — Academic cluster (2 adapters)

Highest cross-domain impact because Health/Science/Climate all hit these.

5. **PubMed** — `services/api_adapters/health.py`. Probe MeSH term mapping.
6. **Semantic Scholar** — `services/api_adapters/academic.py`. Note: also subject to 429 rate limits; separate concern.

### Priority 3 — US gov cluster (2 adapters)

7. **GovInfo** — `services/api_adapters/government.py`. US federal regulations + agency publications. Should hit FDA approvals.
8. **WHO** — `services/api_adapters/health.py`. International health data.

### Priority 4 — Weather cluster (3 adapters)

Narrower domain class, lower priority than the above.

9. **NOAA CDO** — `services/api_adapters/climate.py`. NF-18 fix landed for location/date routing 2026-04-30 + 2026-05-12. Storm-class queries are likely a separate `prepare_query` gap.
10. **WeatherAPI** — `services/api_adapters/climate.py`. Same family as Open-Meteo post-NF-18.
11. **Open-Meteo** — `services/api_adapters/climate.py`.

## 4-step probe per adapter

For each adapter, in priority order:

1. **Capture today's query** — `print(prepare_query(claim_text, entities))` on a known-failing claim. Log the actual outgoing HTTP request.
2. **Hand-craft a working query** — visit the adapter's web UI, find a query that returns the expected primary source. Note the parameter shape.
3. **Diff the two** — what's different between (1) and (2)? Topic phrase too narrow? Wrong parameter? Missing required field?
4. **Patch `prepare_query`** — adjust the shaping logic. Add a regression test that asserts the corrected query shape against a captured response fixture.

## Expected effort

- Per-adapter: 0.5-1 day with tests (probe + patch + regression test against a fixture)
- Full priority 1 cluster (4 UK gov adapters, probable shared root cause): 2-3 days
- Priority 2 academic (2 adapters, likely independent): 1-2 days
- Priority 3 US gov (2 adapters, may share root cause with UK gov): 1-2 days
- Priority 4 Weather (3 adapters, probable shared root cause): 1-2 days
- **Total budget: 6-9 days** of focused adapter work

## Acceptance criteria per priority cluster

- The reference live claim that surfaced the 0-yield now returns ≥3 evidence items from the affected adapter
- Replay bench corpus does not regress on V3 quality signals
- Regression test in `tests/unit/adapters/test_{adapter}_prepare_query.py` pins the corrected query shape

## Out of scope for this work

1. **New adapters** (Track P P0a ECB SDW, P2 SEC EDGAR, P3 Eurostat, P5 Tech/Industry) — separate workstream. Adding adapters doesn't fix broken existing ones.
2. **Scorer / classifier changes** — pool quality fixes upstream of mapper. Doesn't address `prepare_query` shaping.
3. **Web search provider changes** (Exa.ai etc.) — separate decision; user has elected not to pursue Exa for cost reasons (2026-05-15).
4. **Wikipedia / OpenAlex / Internet Archive / Library of Congress** — these adapters work. Don't touch.

## Why this is high leverage but parked

- High leverage: when the adapters work, V3 quality jumps from Mediocre to Excellent on Health, US gov, and UK gov claims. Today's TRU-8723 hit Excellent only because Serper carried the entire load — fragile.
- Parked: V1 ship can complete without this. The Step 7 marketing copy already frames Tru8 as best-quality on 1-3 claims; adapter coverage gaps don't break that promise.
- Right time to start: post-V1-ship, in parallel with I-07 MCP publication and post-launch observability.

## Cross-references

- `audit/OPEN_WORK.md` — Hansard/GOV.UK/ONS row, Weather-domain row, Health/US row
- `audit/pipeline-issues/2026-04-22_remediation-plan.md` §S8 — NF-14, NF-17 historical context
- `audit/pipeline-issues/2026-05-06_v1_quality_plan.md` — V3 framework, V1 ceiling decision
- Memory: `feedback_test_wired_prepare_query_path.md` — NF-18 lesson, applies to all adapter probes
- Memory: `feedback_nf11_prompt_only_failed.md` — do not use prompt-only fixes for adapter query shaping; always mechanical
