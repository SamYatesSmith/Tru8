# Removing passage mapping and structured extraction (2026-10-07)

**Why:** both are Track Q "candidate" features, default OFF, judged not ready on 2026-09-09 (Bank Rate `context_only`, wrong-direction passage supports on SQLite) and never switched on. Production sets no `ENABLE_*` override (Railway variables read 2026-10-07). The architecture review (2026-10-06) recommends deletion. Inventory: independent read-only pass, spot-checked (fingerprint, passage-helper callers, review tests).

**Invariant for this change:** with both flags at their current default (False), behaviour, prompts, cassette signatures, the pipeline fingerprint and the evidence cache key are byte-identical before and after. Proof gates: unit suite drops by exactly the deleted cases; replay bench equals the control arm claim by claim.

## Build A — remove the writers and the flags (this commit)
1. **Config:** delete `ENABLE_PASSAGE_MAPPING`, `ENABLE_STRUCTURED_EXTRACTION`; reword the two comments that mention PM; regenerate `audit/FLAGS.md`.
2. **Whole modules:** delete `services/structured_extraction.py`, `services/fact_applicability.py`, `services/mapping_applicability.py`.
3. **`passage_mapping.py`:** delete `PASSAGE_RESPONSE_SCHEMA`, `passage_relationship_rules`, `plan_pairs`, `complete_passage_pairs`, `MAX_PAIRS`. KEEP `rank_passages`, `valid_passages` (review, distiller, PDF), and `validate_citations`, `cited_context`, `MAX_PASSAGES_PER_PAIR` (legacy readers, Build B decides; see M4).
4. **`claim_map_analyzer.py`:**
   - shared conditions `PM or ENABLE_RELATIONSHIP_REVIEW` → `ENABLE_RELATIONSHIP_REVIEW` (timeout, review call, echo re-review, recovery review); production value unchanged because the review flag is True;
   - delete PM-only: decomposition/mapping prompt addenda, `passage_review` schema label, `fact_applicability` gate append, the temporal-gate reasoning rewrite (`original_reasoning`), the `fact_applicability` reasoning branch, `complete_passage_pairs` call, completion-prompt addendum, `allow_reported_results=` argument;
   - the `cited_context` block in `_apply_scope_gates` reads stored `citations`: KEPT for Build B (review M4);
   - KEEP the three-pass split in `_apply_scope_gates` and `_SCOPE_RECEIPT_KEYS` unchanged for now: gate structure belongs to architecture-review Phase 3 (gate registry), and the extra key only preserves legacy receipts on re-merge.
5. **`recital_scope.py`:** delete the `allow_reported_results` exemption and parameter plumbing; `recital_match` / `claim_restatement_match` unchanged.
6. **`evidence_distiller.py:263`:** `if settings.ENABLE_DISTIL_PASSAGE_INPUT and len(raw) > MAX_ARTICLE_CHARS:` (flag-off branch identical).
7. **`evidence.py`, `cache.py`, `manifest_signer.py`:** delete the SE/PM `if`s (no effect while off: verified the fingerprint dict and cache key only change when True).
8. **`models/claim_map.py`:** KEEP `ClaimMapMetadata.passage_review` and `EvidenceRef.citations` in models + schemas until Build B (legacy records; see the build note).
9. **Scripts:** delete `run_passage_evaluation.py`, `prepare_passage_evaluation.py`, `audit_structured_extraction.py`, `score_passage_regressions.py`, `evaluate_result_fidelity.py` (it measured the review under PM's prompt rules, a configuration that no longer exists; recoverable from git). KEEP fixtures `tests/evaluation/passage_quality/` read by `test_relationship_scope_review.py`.
10. **Tests:** delete whole PM/SE files; split mixed files keeping default-path halves (`rank_passages`, textProvenance mojibake, recital `enabled=False`, temporal wiring `candidate=False`); rewrite `test_relationship_scope_review.py` cases that drive the review through PM to use `ENABLE_RELATIONSHIP_REVIEW`; drop every `setattr(settings, "ENABLE_PASSAGE_MAPPING"/…)` line (they would raise once the attribute is gone).

## Build B — legacy readers (separate, needs one production read)
Readers of `citations`, `passage_review`, `fact_applicability` (PDF `_element_passage_basis` + template, `_SCOPE_NOTE_LABELS`, the `_SCOPE_RECEIPT_KEYS` entry, `relationship_scope_review` `pop("citations")`, `_sanitize_strings` exemptions, frontend ReadingTable citations, `PassageReviewNotice` passage section, `FactApplicabilityNotice`, Seeker `reviewIncomplete`, revision citation diff, shared types). All render nothing when the field is absent. **Remove them once a read-only production query confirms no stored check carries these fields**; until then they are harmless.

## Out of scope
- Simplifying the three-pass gate split (Phase 3).
- `PassageReviewNotice` stays (renamed `SourceScopeNotices` in Build B) (default-on concentration and scope-review notices); `PassageCitation` + `passage-citation.ts` stay (temporal provenance uses them).

## Independent review (2026-10-07) — taken in full
Verdict: plan holds; every flag-off site stays byte-identical (prompts, schemas, fingerprint, cache key). Corrections:
- **H1** three tests load deleted scripts by path at import (`test_passage_evaluation_pack.py`, `test_passage_regression_score.py`, `test_passage_factorial_evaluation.py`) → delete whole files.
- **H2** `test_evidence_distiller.py:517` reads `settings.ENABLE_PASSAGE_MAPPING` (not a setattr) → delete the line.
- **H3** `test_reported_result_recital.py` passes `allow_reported_results=True` → keep the `enabled=False` case and the two tests that still hold without the keyword; delete the one that relies on the exemption.
- **M2** also delete the exemption's helpers in `recital_scope.py` (`_STUDY_FRAME`, `_RESULT_VERB`, `_FINDING_DETAIL`, `_NON_RESULT`, `_reports_overlapping_result`).
- **M3** (follow-up, not this build) the review-flag-False branches in `relationship_scope_review.py` become unreachable from the pipeline.
- **M4** the `cited_context` block reads STORED `citations`: moved to Build B with the other legacy readers (removal waits on the production read).
- **Build note:** `ClaimMapMetadata.passage_review` (a TypedDict key) also moves to Build B: if a Pydantic model validates against it, removing the key could strip the field from legacy responses.
- **L1** drop the now-unused imports in `passage_mapping.py`; **L2** fix `tests/evaluation/passage_quality/README.md`; **L3** update CLAUDE.md / OPEN_WORK at ship.

## Build B gate — production read (2026-10-07, read-only transaction, counts only)
| Table / column | Rows | `"citations":` | `"passage_review":` | `"fact_applicability":` | control `"evidence_refs":` |
|---|---|---|---|---|---|
| `claim.claim_map` | 406 | 0 | 0 | 0 | 301 |
| `report_revision.snapshot` | 0 | 0 | 0 | 0 | 0 |

The positive control matches, so the zeros are real: **no production record carries a field Build B's readers read.** Build B is unblocked (local/eval databases may still hold flag-on records; they would simply stop rendering those fields).
