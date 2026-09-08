# Source preservation acceptance — 2026-09-08

The four-source PDF shown previously was a synthetic layout fixture, not a live research result. It cannot establish a reduction from forty sources or an improvement in retrieval quality.

Added `test_strengthening_preserves_large_source_ledger_across_outputs` to the PostgreSQL report identity integration suite. It seeds 42 explicitly synthetic sources in an isolated local schema, signs the baseline, admits strengthening through the real operation service, and supplies one synthetic new source at the research boundary. Real persistence retains all 43 sources. Repeating delivery does not duplicate the addition. Before/after retained snapshots contain exactly the original 42 and resulting 43 respectively. Owner and public responses retain the same complete URL sets and identify the after revision. The actual PDF template input includes all 43 URLs and the matching snapshot hash.

Validation: 13 integration tests passed across report identity and research operations, including existing race/failure/refund checks. The PDF renderer is stubbed in this test; this checks export content wiring, not native rendering or pagination. Research retrieval/mapping is stubbed: this does not prove model relevance, relationship preservation, unseen-source recall, or live search volume. No runtime behavior, model configuration, candidate flags, or production state changed.

Full replay returned the accepted baseline: 185 ok / 1 warn / 13 known failures / 2 unexercised. Log: `tmp/quality-replay-source-preservation.log`. No cassette or golden changes.

Next acceptance remains a real local research/strengthening run followed through owner history, public sharing and rendered export. Live retrieval comparisons require repeated unchanged controls because search results naturally vary. The original semantic, decomposition, independence and operational work remains open.
