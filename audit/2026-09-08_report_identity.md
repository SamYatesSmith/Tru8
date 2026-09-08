# Public and export evidence-snapshot identity

The original plan's local public/export identity implementation is complete.
Deployment and live acceptance remain open. This is not completion of the whole
pipeline/output-quality programme, and both experimental rollout switches stay OFF.

## Content identity, not the latest history row

Owner responses, detailed public responses and PDF exports now include an
`evidence_snapshot_v1` identity built from the same ORM rows already loaded for
their claims and evidence. No second content read is used to label the first read.
The canonical snapshot builder is shared with strengthening history and preserves
its existing field contract and stable claim/evidence ordering.

A retained revision ID is attached only when the stored JSON snapshot matches that
content. A newer, different revision cannot be used as its label. If multiple
identical retained snapshots exist, the newest matching record is selected. If
none matches, the response/export carries its content hash and explicitly reports
that no matching retained revision is available. No historical record is fabricated.

The SHA-256 identifies the existing retained-evidence snapshot contract, including
claim maps, evidence fields, manifest and selected check metadata. It is **not** a
hash of the PDF bytes, all page fields, videos or the entire API response. It is not
a signature or a truth assessment. Existing signature coverage is unchanged.

The public identity exposes no operation/account fields. Historical content reads
remain owner-authenticated; public verification still returns verification status
and identifiers only. The public page is still a live page, not a frozen historical
content viewer. A PDF downloaded later can represent newer content and carries its
own identity to make that visible.

## Verification and presentation

- Dashboard and public reports show the evidence hash and matching retained ID, or
  the absence of a match. Older responses without identity are disclosed.
- `/verify/{check}?revision={id}` uses the historical verification endpoint and
  checks the returned identities. It does not fall back to verifying current content
  when the requested revision is missing. Unsigned revisions are distinguished
  from connection failures.
- PDFs show the hash, retained ID and scope explanation. Matched revisions link to
  historical verification. Unmatched signed exports explicitly describe verification
  as verification of the mutable live report, not the exported historical content.
- An unconditional “Signed” PDF heading was corrected: unsigned PDFs no longer
  claim signing.
- PDF quality-note preparation now deep-copies the claim map. It previously added
  presentation-only notes to the ORM object, which could contaminate subsequent
  content comparisons in the same session.

## Validation

- **75 backend tests passed**, covering real PostgreSQL identity matching,
  owner/public/PDF parity, non-mutation, revision preservation, HTTP responses,
  PDF templates and existing date handling. Two Windows native-render tests skip
  because WeasyPrint is absent from the local Python environment.
- The sample was separately rendered with **WeasyPrint 62.3 / pydyf 0.10.0** in a
  disposable Linux container using the repository's allowed versions. Only the PDF
  review directory was mounted; no project services/configuration were changed.
  Both A4 pages were rasterized and visually inspected. The identity block was
  enlarged after the first review; final text fits without clipping.
- Sample artifact: `output/pdf/revision-identity-sample.pdf`. This uses the existing
  synthetic PDF fixture and an illustrative identity, not a real signed report.
- TypeScript and **186 full-suite frontend tests** passed. After preserving the
  missing-revision reason, all **4 affected verification/identity tests** passed.
- Replay: **185 ok / 1 warn / 13 known fail / 2 unexercised**, zero cassette drift
  (`tmp/quality-replay-report-identity.log`). No golden/cassette changes.

## Limits and next acceptance

Identity uses the already-loaded snapshot; it does not introduce a new transactional
read-isolation guarantee across concurrent writes. Content with no retained match
is disclosed rather than labelled with an unrelated revision. The additional lookup
compares JSON within a check's revision history; large-history performance has not
been load-tested. The existing research/revision migration must be present.

Next run live strengthening → owner history → public report → PDF acceptance,
including concurrent refresh and stale links. The broader unseen-source/date-language
tests, decomposition/source-independence refinements, operational investigation and
human end-to-end quality assessment remain open. No production access, deployment,
paid model calls, model changes or maintained fact values were introduced here.
