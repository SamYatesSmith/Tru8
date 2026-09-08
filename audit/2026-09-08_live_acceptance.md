# Live local acceptance — 2026-09-08

## Run and scope

At commit `9016871`, ran the real configured pipeline and one element-strengthening operation against local PostgreSQL, using real search, document fetches and model calls. Input: “SQLite write-ahead logging means SQLITE_BUSY errors cannot occur.” No frozen retrieval fixtures, cassette responses or model stubs. Both passage mapping and structured extraction candidates remained disabled. This single run is not a controlled before/after quality comparison or an estimate of web recall.

Check: `49cec0a3-8b93-48de-a526-54be33390e8f`; operation: `8cbdb5f0-c877-4549-ae28-eb6fc56c3c21`. Raw results and response snapshots are in `tmp/live-quality-acceptance-network/`. The harness uses a local bench account, invokes real service/route functions, and does not exercise browser authentication, HTTP transport or worker dispatch. No production access or deployment.

The initial sandbox-blocked attempt could not reach model providers. The subsequent network-enabled run completed. The abandoned local check was marked failed; no user report was modified.

## Passed in this run

- Initial relevance scoring retained 19 of 20 candidates. Strengthening added 13 unique URLs, producing 32. All original URLs survived. Owner/public responses exposed identical URL sets and snapshot identity.
- Before and after revisions were retained. Public revision verification returned valid signatures for both. This verifies the existing signed field scope, not factual correctness or every report field.
- After revision: `3866978c-897c-4d18-b2c4-1df435542202`. Snapshot hash: `69458692eaefbba9aafc0ad641aad702e4d201571e5332699f41ed989273e7d8`.
- Export generated from the real local report using the application template and WeasyPrint 62.3. All four pages visually inspected; the report shows 32 sources and the matching revision/hash. No live hosted link is implied by this local report.

## Failures and limitations found

The original mapping failure remains reproducible with candidate features off. The official `https://www.sqlite.org/wal.html` page is present. Its retained passage beginning at offset 20607 contains the explicit caveat that WAL queries can return SQLITE_BUSY. Its distilled snippet contains only the concurrency explanation. The final map uses this source to support the concurrency premise, but does not map its exception to challenge the “cannot occur” elements. Other sources challenge those elements, so the overall direction is useful while decisive official evidence remains inadequately used.

The same official documentation is labelled `commentary` / `analysis` with `classificationMethod=domain_concentration_cap`. This is a concrete source-role versus publisher-concentration problem; it belongs to the original independence/classification work. Adding more sources alone does not fix it.

PDF layout acceptance is incomplete: source 17 splits across pages 2–3, and the footer alone occupies page 4. The generated PDF remains a local review artifact, not a polished deliverable.

## Next work

1. Use this captured real-source case to assess the passage-aware candidate against its default control, preserving exact inputs and checking the official exception's mapping. Do not enable the candidate based on one case.
2. Separate source role from concentration/independence treatment without domain-specific overrides.
3. Fix PDF source-entry pagination, then complete browser interaction acceptance for owner history, public sharing and historical verification.

No runtime code changed in this checkpoint. Earlier regression results are not presented as fresh tests of this live run. The full original plan remains incomplete.
