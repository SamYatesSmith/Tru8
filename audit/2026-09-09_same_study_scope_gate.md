# Same-study scope gate — 9 September 2026

Track Q phase 2, source-role and study-independence work (Astra finding 10: "group multiple URLs describing one study or observation before aggregating independence … adding duplicate URLs does not strengthen a state by arithmetic alone"). **Default-on** (`ENABLE_SAME_STUDY_SCOPE_GATE`, rollback without redeploy), because it is a correctness rule about arithmetic, not a model-input change; the bench result below is the default-path evidence.

## The failure class

The state function weighs each directional reference by tier (primary 3, reporting 2, commentary 1). A trial retrieved as its journal article, its PubMed abstract and its PMC full text is three primary items, weight 9, for one observation. Astra's SELECT check showed the original NEJM paper twice in the ledger; the creatine check counted alternate publications of one 20-person pilot as if they were separate trials. The existing echo gate (2026-08-17) covers a *derivative* of a primary, via the corroboration engine's derivation chains; it has nothing to say about two primaries that are the same paper.

## The rule

An evidence item's **study identity** is a persistent identifier only (`app/utils/study_identity.py`): a DOI read from the URL, then a DOI printed in the text (`doi:` or `doi.org/`), then a PubMed id or PMC id read from the URL. A trial acronym, a title match or a matching number is never identity: two papers about one trial are two papers, and the honest failure mode for an identity rule is to miss a duplicate, not to merge two studies.

The gate (`same_study_scope`, in `_armed_scope_gates`) fires on a directional reference when another reference on the **same side** of the same element carries the same study identity and is the counted carrier: highest tier weight, then earliest in the element's references. The carrier keeps its direction; every other host becomes `context` with a receipt naming it (`counted_as`) and the identity. Symmetric by construction. A host mapped to the *other* side is left alone: that is a mapping disagreement to show, never a duplicate to hide. Placed immediately before the echo gate so echo stays last; the receipt key is registered in `_SCOPE_RECEIPT_KEYS` so both post-mapping merge paths keep it.

## Evidence

- `tests/unit/pipeline/test_same_study_scope.py` drives the real mapping parser: three hosts of one DOI count once (state derived from two supports, not four; nothing deleted); the primary journal article carries even when a reporting-tier full text is listed first; the receipt names the carrier and the identity; symmetric for challenges; other-side host untouched; a news report with no identifier untouched; flag off leaves every host directional; receipt key registered and echo still last. Identifier extraction cases cover DOI in URL, DOI resolver with a query string, PubMed and PMC URLs, DOI in text, and a PMID cited in passing (deliberately `None`).
- Default replay bench with the gate on: **185 ok / 1 warn / 13 known fail / 2 unexercised, zero cassette drift — and the gate fired 0 times** across the ten corpus claims (`tmp/quality-replay-same-study-2026-09-09.log`, no `[SAME STUDY]` line). The corpus holds no two hosts of one DOI, so ⚠️ **the bench cannot verify this gate**; the unit tests through the real parser are its evidence, and the first live firing should be read in the Railway logs (`[SAME STUDY] elem=…`). Whole backend suite: in the commit message.

## Not done here

Grouping by trial *name* across distinct papers (a systematic review and the trial it reviews are different evidence roles, not duplicates) and exposing a distinct-study count in `source_concentration` metadata. Both remain open under source roles.
