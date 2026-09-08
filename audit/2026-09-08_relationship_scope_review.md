# Final relationship scope review — 8 September 2026

Continues the [scope correction](2026-09-08_scope_correction.md). The candidate now has a bounded final applicability review after initial mapping, source completion and passage review. It addresses relationships left directional when a passage proposed context, and relationships based on snippets with no retained passages. No source-removal rule, maintained factual value, publisher exception or scheduled AI trigger was introduced.

## Policy and auditability

Only existing support/challenge references are eligible. The stage never promotes context to a directional label or flips support into challenge. It reviews at most 12 pairs per mapping invocation, round-robin across elements, using up to 1,800 characters of the mapping payload and two existing retained passages per pair. Input without passages remains labelled by its actual content basis; a copied snippet/generated payload is not manufactured into a verified full-source citation. Coverage recovery also reviews its merged pool before orientation is recomputed. A recovery invocation can therefore add another bounded review; the added end-to-end latency remains to be measured. The logical review has a 25-second outer deadline and 4,800-output-token limit; provider fallback can occur within that deadline.

The model returns compatible, mismatch or unknown. A mismatch or unestablished scope can become context only with a permitted scope dimension, nonempty claim/source scope, explanation, and a 12–600-character exact excerpt of a supplied block. Malformed, duplicated, missing or failed responses preserve earlier mappings and expose incomplete coverage. A structurally valid model decision is not an entailment certificate.

The record retains the original relationship, explanation, citations, uncertainty, the review's explanation, payload basis and input hash. Element state and uncertainty are recomputed; the source record remains unchanged. Earlier gate receipts survive. Historical reports are not retroactively rewritten. The new reference does not reuse an old citation as the basis of new wording: prior citations are retained in the audit receipt, while the reviewed payload excerpt is clearly distinct from a source-linked citation.

An initial review still accepted the Wiley observational snippet as support for SELECT. More explicit instructions alone did not resolve this. A narrow structural guard now recognises the grammar `In/Within [the] ACRONYM trial/study` in an element. If that acronym is absent from the supplied title and text, the source's applicability to the named study is unestablished. The guard records that it overrode the model, and the source stays as context. It matches case-insensitively against supplied content, with word boundaries, and contains no actual study names or factual answers. Tests cover missing identifiers, case differences and near-matches. It does not resolve aliases, full-name references, arbitrary study wording or verify that a present name establishes a study's design; it is intentionally conservative about absent identity.

The frontend displays reviewed/uninspected counts, failure status and reasons for sources scoped to context. A passage-conflict notice no longer says the earlier label was retained if the final scope review changed it. Existing source-detail relationship explanations receive the updated wording. Old records without this metadata retain their prior presentation. Browser interaction and production rollout were not tested or performed in this phase.

## Frozen-source evaluation

All 21 creatine and 16 SELECT source inputs from the report pilot are retained. Decomposition and mapping are tested separately: the mapping uses the same fixed faithful one-element claim and complete frozen pool, with no fresh retrieval, classification, distillation, database writes or rewritten source material. This is not an end-to-end live candidate report or a new human quality score.

The initial final-review sweep corrected progression/prevention errors but retained the Wiley snippet as support twice. Tightening unknown-scope wording still retained it twice. Both unsuccessful sweeps remain recorded. The final sweep adds the generic absent-study-identifier guard and repeats both complete mapping cases twice.

Both final repeats pass the targeted gate: all creatine directional references become context for the prevention assertion; SELECT retains six supports, while the observational snippet without the named trial is context. All 21 and 16 source inputs remain. The actual records scoped differ with upstream model variation, so this is not a guarantee for unseen evidence. The original claim is neither confirmed nor refuted merely because available sources are contextual.

The synthetic controls passed 8/8 across two repeats after unknown-scope handling was added: direct randomized incidence reduction remains support, a contrary incidence result remains challenge, progression-only and confounded-association evidence remain context. These controls do not contain a named-study claim, so the later identifier guard does not apply; separate unit tests exercise it. This is evidence against indiscriminate abstention, not a general precision estimate.

Source-role accuracy and study-level independence remain separate open work: a paper reporting another study in its background can contain a relevant quotation without becoming an independent replication. This review does not deduplicate alternate publication hosts or reclassify source roles. The 12-pair bound also leaves larger pools partly unreviewed; coverage is disclosed rather than claimed complete.

## Validation and next gate

- 124 focused backend tests passed, including symmetric scope handling, malformed/failed output, exact-payload checks, absent study identity, preservation of earlier uncertainty, no context promotion, provider schema, default rollback, coverage-recovery wiring, passage persistence and existing mapping gates.
- 190 web tests passed; TypeScript passed. New UI coverage verifies scoped-source disclosure and superseded-conflict wording.
- Final full replay `tmp/quality-replay-scope-review-recovery-final.log`: 185 ok / 1 warn / 13 known fail / 2 unexercised, zero cassette drift; expected exit 1. Cassettes/goldens unchanged.
- Candidate fingerprint v9; both experimental flags remain OFF. No deployment or default model/prompt changes.
- Raw sweeps: `tmp/scope-correction-eval/scope-review.json`, `scope-review-final.json`, `scope-review-identity.json`; controls: `scope-review-final-controls.json`. Tracked summary: `backend/tests/evaluation/passage_quality/relationship_scope_review_results.json`.

After this bounded gate, the next acceptance step is an integrated candidate run and broader held-out source/scope cases, including legitimate aliases and thin but relevant sources, plus added latency/cost measurement. The original human-review and finished-report requirements for an 8/10 re-score remain unmet.
