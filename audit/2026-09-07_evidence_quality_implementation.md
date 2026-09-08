# Evidence quality implementation — 7 September 2026

User authorised implementation of the hands-on improvement map, with a commit after each validated step. Baseline: `47664a1`. Branch: `codex/evidence-quality`. Existing uncommitted commercial assessment and register changes must not be included in implementation commits.

## Sequence and status

1. **Locally verified:** truthful Gaps coverage and review status. Contextual/disputed material remains visible; evidence presence never implies all questions are settled. Web suite: 151 passed; TypeScript check passed.
2. **Locally verified:** Compare relationship semantics and display identity. Context/directional pairs are contextual; identical directional mappings say “same direction”, not whole-source agreement. Selected A/B order preserves summaries, text receipts and one-sided rows while the cache remains canonical. Fresh-read versus saved-map distinction is visible; extraction is no longer labelled “full article”. All nine relationship combinations, missing mappings, live recomputation and reversed display covered: 20 backend tests and 4 web regressions passed; TypeScript passed. Existing API `aligned` responses containing context render honestly during rollout.
3. **Locally verified:** research completion explicitly fetches and replaces the client report with a fresh token; failures retain the old report and expose retry, and older overlapping responses cannot overwrite newer results. Compare reloads saved mappings after report changes. The source panel exposes each relationship and its saved reasoning as “System interpretation”, explicitly discloses unavailable exact passages, and receives focus/scroll on opening. Claim-wide explanations preserve their own claim/element descriptions. Web suite: 158 passed; TypeScript passed. Production UI acceptance remains outstanding.
4. **4a locally verified; 4b pending:** canonical stored-evidence round trip preserves tier/type, classification method, date/date provenance, content basis, context, archive, fact-check and independence metadata. Incoming URLs deduplicate within the batch and get stable IDs before mapping. Three helper tests plus one offline orchestrator integration test pass; the latter verifies primary metadata reaches mapping and saved IDs match the map. Full replay reproduces the exact documented baseline: **185 ok / 1 warn / 13 known fail / 2 unexercised, zero cassette drift**. Claim-level coordination, durable admission/refunds and signed revision history remain unbuilt (design constraints below).
5. Pending: passage/extraction provenance and mapping coverage.
6. Pending: temporal applicability, decomposition and source-role refinements.
7. Pending: operational reconciliation and end-to-end acceptance.

No production deployment, paid benchmark or production-log inspection has been performed. Local verification is not an 8/10 re-score; live evidence and reviewer evaluation remain separate acceptance gates.

## Resume checkpoint — 8 September 2026

- Completed commits: step 1 `4d68057`, step 2 `302b8cd`, step 3 `ba9df3d`.
- Web: all 158 tests passed, TypeScript passed. Backend Compare categories/prompt/budget plus evidence payload: 35 tests passed. Formatting completed for the prepared Python files.
- Step 4a files: `backend/app/services/evidence_payload.py`, `backend/app/pipeline/re_search.py`, `backend/tests/unit/test_evidence_payload.py`, `backend/tests/unit/test_re_search_payload_integration.py`. Existing unrelated `.gitignore`, commercial assessment and older OPEN_WORK additions remain separate.
- **Local test environment repaired:** the user restored Docker Desktop; `docker compose up -d postgres redis` started the existing project services successfully. No daemon reset, WSL shutdown, database deletion or production action was performed by this task.
- Test runtime: `tmp/quality-venv/Scripts/python.exe`. The initial replay after Docker recovery had drift across all ten claims. A diagnostic exposed missing `sentence_transformers` (fallback to word overlap) and `pdfplumber`; after installing the declared dependencies and caching MiniLM, the diagnostic reproduced 40/40 responses and the whole corpus returned to the exact accepted baseline. Do not mistake the initial environment failure for a code regression or regenerate cassettes to hide it.
- Reproduce from backend with process-local `HF_HOME=C:\Users\projects\Tru8\tmp\quality-hf-cache` and `HF_HUB_OFFLINE=1`, then `..\tmp\quality-venv\Scripts\python.exe scripts/replay_bench.py --all`. Model download is not needed for subsequent runs. Runtime package versions: `tmp/quality-test-requirements.txt`. Full replay log: `tmp/quality-replay-all.log`. No golden/cassette updates or paid model calls were made.
- Latest focused backend run: 36 tests passed (Compare categories/prompt/budget, payload helpers and re-search integration); prior web run remains 158 passed plus TypeScript. Whole step 4 and steps 5–7 are not complete.

## Step 4 design constraints recovered from the persistence path

1. Both bulk endpoints (`research-gaps`, `research-thin`) currently launch one whole-map writer per element. Replace with one operation that plans targeted retrieval for the selected elements, merges once, maps once and commits once. Single-element research must use the same path.
2. Protect against concurrent operations across processes, not just an asyncio lock. Admission/idempotency must happen before debit; use a durable operation identity for status, retries and refunds. Serialize writes or compare a stored revision, and test competing completions against PostgreSQL.
3. Preserve existing evidence metadata and assign candidate identities before mapping (prepared patch). Run the same extraction/distillation contract for fresh candidates; preserve claimant/jurisdiction metadata from the existing map.
4. **Signing issue confirmed by inspection:** `re_search.py` changes claim maps/evidence without archiving a prior revision or replacing `Check.manifest`. `/verify` hashes the current map/evidence, so a changed signed payload no longer matches its original manifest. Store an immutable prior snapshot and manifest, then sign the coherent updated report in the same transaction. Coordinate at check level because one manifest covers all claims. Never merely re-sign and erase the old record.
5. Bundle status and watchdog cancellation must terminate every selected element; counts must not multiply the same merged sources by the number of elements. Success is published only after commit. Failure rolls back evidence/map/signature together and refunds the operation's debit once, without failing the already-completed parent check.
6. Required acceptance: duplicate requests, simultaneous element runs, timeout/cancellation before commit, signing failure, preserved source weights/dates, signed prior snapshot verification and current revision verification. These remain to be implemented and tested; no claim-level concurrency or signature repair is represented as complete.

The detailed original proposal remains at `tmp/tru8-hands-on/tru8-route-to-eight.md`; steps 5–7 and human/live acceptance have not been completed.
