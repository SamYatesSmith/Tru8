# Scope correction — 8 September 2026

Continues the [finished-report pilot](2026-09-08_finished_report_pilot.md). The decomposition change passes this bounded diagnostic set. The expanded mapping instructions do **not** pass the real-source acceptance gate. Both remain behind `ENABLE_PASSAGE_MAPPING=False`; there is no deployment or 8/10 claim.

## Implementation

Candidate decomposition now preserves population, intervention, comparator, outcome, named study, time window, effect measure and asserted precision. It avoids ingestion/existence/mechanism prerequisites unless asserted and keeps simple claims atomic. These are general instructions, with no drug, disease, institution, date, rate or source-domain exceptions.

An initial addendum alone was insufficient: one repeated creatine decomposition still added a prerequisite. The base prompt explicitly instructed the model to split cause and effect. Candidate prompt construction now replaces that exact legacy instruction, in both single and batch paths, before appending the scope instructions. Default prompts remain byte-for-byte unchanged. Unit checks cover both paths and rollback.

Candidate mapping instructions explicitly distinguish onset prevention from progression/treatment, association from causation, and a source's original study from another study it cites. An accurately attributed cited trial result may remain relevant; it is not automatically independent replication. These instructions reach initial, batch, completion, recovery and passage-review calls. They are experimental semantic guidance, not a deterministic certification or an implemented study-identity system.

The candidate fingerprint advances from v7 to v8. No sources are removed and no previously persisted reports are rewritten. Application changes are confined to prompt construction, candidate instructions and fingerprinting.

## Repeated evaluation

The full saved evidence pools from the previous local pilot were held fixed: 21 creatine and 16 SELECT source records, retaining IDs, snippets, classification and passage provenance. No new retrieval, distillation, classification, persistence or source pruning was performed. Mapping used a fixed single faithful assertion for each claim to isolate mapping from decomposition. This does not test retrieval against newly decomposed elements or constitute an end-to-end final-candidate run.

Each sweep ran two repeats of single-claim decomposition for Venus, creatine and SELECT, plus two repeats of mapping each medical claim against its full pool. Baseline was the existing v7 disabled candidate; the first v8 attempt added rules; final v8 removed the contradictory split instruction as well. There were no model changes. Because sweeps were sequential rather than interleaved ABBA, model/provider time variation remains a limitation.

| Check | Existing v7 | Initial v8 attempt | Final v8 |
|---|---|---|---|
| Venus decomposition | Three elements in both repeats, including inserted quantities | One faithful element twice | One faithful element twice |
| Creatine decomposition | Four elements twice, including prerequisites/mechanisms | One clean result; one result with extra prerequisites | One prevention element twice |
| SELECT decomposition | Three elements twice, adding exactly/precisely | One element preserving relative effect twice | One element preserving relative effect twice |

Two additional real batch calls produced the same substantive one-element shape for all three claims (six outputs), with the named trial/population/relative effect preserved. These are repeated outputs for three diagnostic claims, not twelve independent held-out claims or a universal decomposition guarantee. The user's causal claim remains an assertion to investigate, not a finding made by decomposition.

Two synthetic mapping repeats used a fictional intervention/condition with four sources: direct randomized incidence reduction, a contrary adequately powered incidence result, progression-only evidence and a confounded observational association. All **8/8** expected relationships passed, including support and challenge. This guards against merely labelling everything context, but the real-source results take precedence.

## Real-source mapping failures remain

The initial v8 sweep improved several primary-source relationships and correctly scoped the Wiley observational snippet in both repeats. The final sweep did not retain that result: the Wiley record `ev-1b3f9af549a3` was again counted as support in both repeats. Its explanation promoted an association to support for the SELECT trial assertion without establishing the trial identity, design and effect measure. Do not describe the early successful repeats as a reliable fix.

In both final creatine repeats, four challenge relationships remained whose explanations used progression/symptom findings or added prevention language. At least `ev-4977ed90d311` and `ev-07ed2917d107` still rest on progression evidence. A later explanation also widened the retained evidence into occurrence/prevention. The eight synthetic passes do not offset these failures.

The stored passage receipts identify a concrete limitation: in final repeat 0, `ev-bf877b9d39b4` was proposed as context with an exact progression-related quote, but the existing conflict-preservation policy kept its earlier challenge. Another pair was invalid; several problematic sources, including the Wiley snippet, have no retained passages and therefore cannot receive this passage review. This does not prove that blindly replacing earlier mappings with later model answers would be safe. Existing gates can also legitimately demote a source, and a proposed support conflict must not undo them.

The PMC SCORE article retains an exact passage reporting SELECT's result, and candidate explanations identify SELECT. This improves attribution at that relationship, but its source-level primary classification and study-independence treatment are not corrected by the new prompt. No claim of solved study deduplication follows.

**Decision:** retain the tested decomposition improvement and experimental scope instructions under the disabled candidate flag. The full candidate fails clinical mapping acceptance. Next work must trace which initial/completion decisions survive and design a bounded scope-resolution policy for snippet-only and conflicting-passage cases. Preserve both interpretations and evidence; do not silently discard sources or overwrite signed history. More prompt-only repeats of this same set are not an adequate acceptance strategy.

## Validation and artifacts

- 105 focused tests passed: candidate provider wiring/rollback, single/batch split-rule removal, passage mapping, date applicability, temporal explanations and fingerprint stability.
- Final replay `tmp/quality-replay-scope-correction-final.log`: 185 ok / 1 warn / 13 known fail / 2 unexercised, zero cassette drift; expected exit 1. Goldens and cassettes unchanged.
- Local frozen runs: `tmp/scope-correction-eval/{baseline,candidate,final,batch,positive-controls}.json`. All full outputs remain there, including failures.
- Tracked diagnostic summary: `backend/tests/evaluation/passage_quality/scope_correction_results.json`, including input/output hashes, decomposition outputs, selected failure relationships and synthetic expectations.
- No production access, model change, deployment or candidate activation. The current default therefore does not yet benefit from this candidate decomposition correction.
