# Feature flags (generated — do not edit by hand)

Regenerate with `cd backend && python -m scripts.flag_register`. `tests/unit/test_flag_register.py` fails when this file is stale.

Defaults are the code's. **Railway can override any flag with an env var of the same name; this file cannot see that.** Check Railway when a live value matters.

**51 flags: 43 on, 8 off by default.**

| Flag | Default | Read in | Why (from config.py) |
|---|---|---|---|
| `ENABLE_CITED_SOURCE_GAP_NOTE` | **OFF** | 1 file | Build B, the gap note (2026-10-06, design §§11.8, 12.2, 12.6, 17). |
| `ENABLE_DERIVATION_CHAINS` | **OFF** | 1 file | The grey "echo" sourcing note's reader. OFF 2026-10-01 (founder): the unconfirmed links were real relays 24% of the time. |
| `ENABLE_ECHO_LINK_CONFIRMATION` | **OFF** | 1 file | Echo link confirmation (2026-10-05). |
| `ENABLE_ECHO_SCOPE_GATE` | **OFF** | 2 files | Echo scope gate (2026-08-17, quality-first Phase B). OFF 2026-10-01 (founder): the link it reads is wrong more often than right. |
| `MANIFEST_SIGNING_ENABLED` | **OFF** | 3 files | M-04: Manifest signing |
| `SKYFIRE_ENABLED` | **OFF** | 1 file | ========== SKYFIRE KYAPay (L-06) ========== |
| `SUBSCRIPTIONS_ENABLED` | **OFF** | 1 file | When False, subscription endpoints return "coming soon" message Set to True when ready to accept paid subscriptions |
| `X402_ENABLED` | **OFF** | 1 file | ========== x402 USDC Payment (L-05) ========== |
| `ENABLE_ABSENCE_OF_EVIDENCE_GATE` | ON | 1 file | Absence-of-evidence gate (2026-09-09, Track Q — Astra finding 3). |
| `ENABLE_API_RETRIEVAL` | ON | 2 files | Phase 5 - Government API Integration |
| `ENABLE_ARTICLE_CLASSIFICATION` | ON | 1 file | ========== ARTICLE-LEVEL CLASSIFICATION ========== LLM-based article classification (runs once per check, not per claim) Replaces per-claim spaCy NER domain detection with ~95% accuracy |
| `ENABLE_CLAIM_CLASSIFICATION` | ON | 1 file | Phase 2 - User Experience & Trust |
| `ENABLE_CLAIM_LANE_UNWINDOWED_TWIN` | ON | 1 file | Build A (2026-09-02): the claim lane's unwindowed twin. |
| `ENABLE_COPY_DEDUP` | ON | 1 file | A− Build C ENFORCE (2026-09-28), main retrieval site only: collapse each copy group to its survivor BEFORE the fetch budget is sliced, so a copy never takes a second fetch slot. |
| `ENABLE_COPY_DEDUP_SHADOW` | ON | 1 file | A− Build C SHADOW (2026-09-25): log `[COPY DEDUP] would_drop=… survivor=…` for pre-fetch candidates that are copies of one article. |
| `ENABLE_DATE_SCOPE_GATE` | ON | 1 file | Day-level date scope gate (2026-09-09, blind review). |
| `ENABLE_DIRECTION_REPAIR` | ON | 1 file | Direction fidelity (2026-09-10): a causal element that names the outcome without the claim's direction ("primary driver of its mortality outcome" for "caused LOWER mortality") is readable either way — five of seven blind-reviewer misreads that day sat on th... |
| `ENABLE_DISTIL_PASSAGE_INPUT` | ON | 1 file | Read a document longer than MAX_ARTICLE_CHARS by its retained element windows instead of a leading slice (2026-09-22). |
| `ENABLE_ELEMENT_ATOMICITY` | ON | 2 files | Phase 3a (2026-07-29): element atomicity. |
| `ENABLE_ELEMENT_RETRIEVAL` | ON | 1 file | Phase 2 (2026-07-27): element-level retrieval. |
| `ENABLE_EMAIL_NOTIFICATIONS` | ON | 1 file |  |
| `ENABLE_EVALUATIVE_HEAD_SIGNAL` | ON | 1 file | F-VERDICT / P13 (2026-07-26): the "normative" hint above is an LLM judgement and under-fires on two witnessed shapes — an IDEA/PROPOSITION as subject ("The learning-styles theory is indefensible" → returned +SUPPORTED by 11 sources, a verdict on a value jud... |
| `ENABLE_EVIDENCE_DISTILLATION` | ON | 2 files | Evidence distillation |
| `ENABLE_FACTCHECK_API` | ON | 1 file | Phase 1.5 - Semantic Intelligence |
| `ENABLE_FACTCHECK_SIGNAL` | ON | 1 file | Item 7 stage 1 (2026-08-28): the factcheck signal. ON 2026-08-28 (founder-approved) after measurement: 200 stored-ledger URLs → zero false positives, 10/10 flagged were genuine (7 by content judgement beyond the domain list); probed on /r/fa08cff7's own poo... |
| `ENABLE_FETCH_PHASE_DEADLINE` | ON | 1 file | Fetch-phase deadline (2026-09-02). |
| `ENABLE_FIGURE_SCOPE_GATE` | ON | 1 file | Figure scope gate (F2, 2026-09-23). |
| `ENABLE_INTERESTED_PARTY_GATE` | ON | 1 file | Interested-party gate (2026-08-13): check TRU-018F-44AA badged "Donald Trump stopped 6 wars" supported-all-4, with whitehouse.gov's own "I've solved six wars" weighing primary-3 against PolitiFact at commentary-1. |
| `ENABLE_JURISDICTION_SCOPE_GATE` | ON | 1 file | Jurisdiction gate (2026-08-06): the mechanical analogue of F1. |
| `ENABLE_LLM_RELEVANCE_SCORER` | ON | 2 files | ========== LLM RELEVANCE SCORER ========== Replaces embedding-based ranking with LLM-based understanding of evidential value Uses GPT-4o-mini to score evidence 1-5 based on how well it helps verify/refute claims |
| `ENABLE_MEASURE_SCOPE_GATE` | ON | 1 file | Measure gate (2026-08-06): the third mismatch in check 757f02c2. |
| `ENABLE_OPINION_REFRAME` | ON | 3 files | ========== OPINION DECOUPLING (Phase 1a, 2026-07-16) ========== Extraction KEEPS main-predicate evaluative claims (reframed affirmative, type_hint="normative") instead of dropping them under Rule 6; the grounds stage then rebuilds their elements as neutral ... |
| `ENABLE_ORIGINATOR_REVIEW` | ON | 2 files | Originator review (A− H4 class D, 2026-09-30). ON 2026-09-30 (founder): held-out eval on 3. |
| `ENABLE_QUERY_PLANNING` | ON | 1 file | ========== QUERY PLANNING AGENT ========== LLM-powered batch query planning for semantic claim understanding Generates targeted queries based on claim type (squad, stats, contract, etc.) |
| `ENABLE_RANGE_PERIOD_GATE` | ON | 1 file | Range-period gate (A− option 3, 2026-09-24): an aggregate element over a closed past year range cannot be established by a source published before 1 December of the range's end year (trusted dates only). |
| `ENABLE_READABLE_TEXT_GATE` | ON | 1 file | Unreadable-text floor (A− M2, 2026-09-24). |
| `ENABLE_RECITAL_DIRECTION_RELEASE` | ON | 1 file | Recital direction release, R6 (2026-09-25): a CHALLENGE never rests on its subject restating the claim — a fact-check reciting "Trump says he's ended eight wars" to rebut it stays a challenge (TRU-018F-44AA: four fact-checks were demoted). |
| `ENABLE_RECITAL_EVIDENCE_NARROWING` | ON | 1 file | Recital evidence-text narrowing (A− recital review, 2026-09-24): R0–R5 stop the recital gate firing on a sentence the support does not rest on (self-reference, declined speech, passive voice, an ORG's own publication, an actor announcing their own transacti... |
| `ENABLE_RECITAL_INSTRUMENT_SKIP` | ON | 1 file | Recital instrument skip, A1′ (2026-09-29): a subject-anchored match whose speaker is an unowned document ("According to the toplines, Democrats hold…", "…, the poll said") is not a recital by anyone. |
| `ENABLE_RECITAL_SCOPE_GATE` | ON | 1 file | Recital gate (2026-08-13): the same check's load-bearing failure — "states Trump claimed to have 'settled six wars'" was mapped `supports`. |
| `ENABLE_RECOVERY_ENRICHMENT` | ON | 1 file | ========== PIPELINE EVIDENCE QUALITY (Track N Phase 2) ========== Coverage recovery enrichment: fetch full page content for recovery evidence |
| `ENABLE_RECOVERY_QUERY_PLANNING` | ON | 1 file |  |
| `ENABLE_RELATIONSHIP_REVIEW` | ON | 3 files | Relationship review on the DEFAULT path (A− M1, 2026-09-24). |
| `ENABLE_SAME_STUDY_SCOPE_GATE` | ON | 1 file | Same-study scope gate (2026-09-09, Track Q — Astra finding 10). |
| `ENABLE_SEARCH_CLARITY` | ON | 2 files | Search Clarity Feature (MVP) |
| `ENABLE_SEMANTIC_SNIPPET_EXTRACTION` | ON | 1 file | Semantic Snippet Extraction |
| `ENABLE_TEMPORAL_CONTEXT` | ON | 1 file |  |
| `ENABLE_TEMPORAL_PUBLICATION_RESOLUTION` | ON | 1 file | F1 extension (2026-08-06): resolve a bare month ("in September") against the item's published_date, so an undated-year source is placed in time. |
| `ENABLE_TEMPORAL_SCOPE_GATE` | ON | 1 file | F1 (2026-08-05): scope evidence about a DIFFERENT period out of the state count. |
| `ENABLE_TITLE_RECOVERY` | ON | 1 file | 2026-08-25: recover headlines the search provider handed us pre-cut. |
| `ENABLE_UNSTATED_QUANTITY_REPAIR` | ON | 1 file | Decomposition specificity (2026-09-10): a grounds question that demands a figure the claim never stated ("What is the TOTAL lifecycle emission VOLUME…" for "electric cars are cleaner") cannot be answered by a source that answers the claim, so its labels rea... |
