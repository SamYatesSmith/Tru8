# Evidence quality implementation — 7 September 2026

User authorised implementation of the hands-on improvement map, with a commit after each validated step. Baseline: `47664a1`. Branch: `codex/evidence-quality`. Existing uncommitted commercial assessment and register changes must not be included in implementation commits.

## Sequence and status

1. **Locally verified:** truthful Gaps coverage and review status. Contextual/disputed material remains visible; evidence presence never implies all questions are settled. Web suite: 151 passed; TypeScript check passed.
2. **Locally verified:** Compare relationship semantics and display identity. Context/directional pairs are contextual; identical directional mappings say “same direction”, not whole-source agreement. Selected A/B order preserves summaries, text receipts and one-sided rows while the cache remains canonical. Fresh-read versus saved-map distinction is visible; extraction is no longer labelled “full article”. All nine relationship combinations, missing mappings, live recomputation and reversed display covered: 20 backend tests and 4 web regressions passed; TypeScript passed. Existing API `aligned` responses containing context render honestly during rollout.
3. **Locally verified:** research completion explicitly fetches and replaces the client report with a fresh token; failures retain the old report and expose retry, and older overlapping responses cannot overwrite newer results. Compare reloads saved mappings after report changes. The source panel exposes each relationship and its saved reasoning as “System interpretation”, explicitly discloses unavailable exact passages, and receives focus/scroll on opening. Claim-wide explanations preserve their own claim/element descriptions. Web suite: 158 passed; TypeScript passed. Production UI acceptance remains outstanding.
4. Pending: coherent strengthening with preserved evidence metadata.
5. Pending: passage/extraction provenance and mapping coverage.
6. Pending: temporal applicability, decomposition and source-role refinements.
7. Pending: operational reconciliation and end-to-end acceptance.

No production deployment, paid benchmark or production-log inspection has been performed. Local verification is not an 8/10 re-score; live evidence and reviewer evaluation remain separate acceptance gates.
