# Owner revision history: local implementation checkpoint

The original plan requires strengthening to preserve a coherent, reviewable record.
The backend retained snapshots, but owners had no UI to inspect them. This step
adds that viewer and fixes a request-header defect found while wiring the API.

## Implemented

- Completed dashboard reports expose a **Revision history** control. Opening it
  fetches owner-authenticated history; no historical reads occur before opening.
- Owners can inspect retained before/after strengthening snapshots and their source
  ledgers, elements, relationships, explanations and stored quotations. Unlinked
  sources remain in the ledger. The live report below is never replaced or mutated.
- Selecting an after snapshot automatically compares with the before snapshot from
  the same operation. Owners can select another baseline or disable comparison.
  Comparison uses claim/element/source IDs, not array positions. It reports added
  or removed claims/elements/links, state and relationship changes, wording changes,
  uncertainty-note changes, and explanation/quotation changes.
- The comparison is explicitly limited to elements and relationships. It is not a
  full field-by-field report diff. Snapshots are labelled as retained strengthening
  records, not a complete edit history or a guaranteed current revision.
- Stored signature presence is distinguished from cryptographic verification. The
  viewer does not claim to verify signatures or every narrative word. Existing
  backend verification semantics and owner access checks are unchanged.
- Loading, retry, empty-history and stale-response paths are handled. A changed
  report refresh reloads the open history list. Mismatched snapshot check/revision
  IDs and unsupported snapshot versions are rejected. Unsafe URL schemes are not
  rendered as source links.

## Strengthening retry fix

`startElementResearch` supplied an `Idempotency-Key`, but the shared request helper
replaced all caller headers with its own Content-Type/Authorization object. The
backend therefore received no key and generated a fresh one. Its active-operation
guard still existed, but this broke the intended stable request identity across
retries, especially after an operation had reached a terminal state.

The helper now preserves caller headers using `Headers` and adds the authenticated
token and default content type. A regression checks that repeated research requests
carry the same explicitly supplied key, auth header and POST method. Existing
backend idempotency, debit/refund and revision persistence logic was not changed.

## Validation

- TypeScript passed.
- **183 web tests passed** (29 files), including new revision selection/comparison,
  missing history, failed-load retry, stale response, mismatched identity, safe-link,
  stable-identity diff and transmitted-header tests.
- **10 PostgreSQL integration checks passed** in `test_research_operations.py`,
  covering the existing revision preservation and research-operation contract.
- No backend pipeline, prompts, models, schemas or rollout settings changed. The
  replay baseline from `d715f65` remains the last pipeline validation; no replay or
  paid model evaluation was required for this frontend/API-client change.
- Live browser acceptance and live strengthening-to-history interaction have **not**
  been performed. No deployment or production access.

## Remaining plan status

This closes the local implementation of the owner-facing revision viewer, not the
whole improvement plan. Public/export revision identity and live revision acceptance
remain open. Broader source/date-language acceptance for the disabled mapping and
extraction candidates, decomposition/source-independence refinements, operational
investigation and full end-to-end/human output-quality acceptance also remain open.
