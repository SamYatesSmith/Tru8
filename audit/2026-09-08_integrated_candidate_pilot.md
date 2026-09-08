# Integrated candidate and broader scope pilot — 8 September 2026

Continues the [final scope review](2026-09-08_relationship_scope_review.md). This assessment runs the candidate through live local research and persistence, rather than only remapping frozen material. All three reports complete, but broader evidence-fidelity acceptance still fails. No application code, default flag, model setting or deployment changed in this phase.

## Integrated runs

The candidate flag was enabled only inside the evaluation process. Actual extraction, decomposition, retrieval, classification, distillation, mapping, passage review and eligible final scope review ran, followed by local persistence and direct owner/public service reads. Existing benchmark-user reports were created locally. This is not browser, HTTP-delivery or worker-process acceptance; it does not exercise production or historical revision verification.

| Case | Check | Sources | Useful elements | State | Wall time | Final scope model time |
|---|---|---:|---:|---|---:|---:|
| Venus axial rotation versus orbit | `f6f414d8-4085-40b3-8d79-a5b9133d8470` | 16 | 1 | supported | 39.67s | 1.61s |
| Creatine preventing Parkinson's onset | `2f109e16-38b5-4e23-acba-0d1418fe6b88` | 19 | 1 | contextual | 47.25s | no eligible directional refs |
| SELECT relative MACE effect | `1682893b-b3ac-4a0c-b2ba-c5767daac3a5` | 19 | 1 | supported | 44.76s | 2.50s |

Owner/public source URL sets and snapshot hashes agree in all three. These are unretained initial snapshot identities, not archived revision IDs. All 54 source records remain in their ledgers; counts are not independent-study counts, and tracking-parameter URL variants can still occur.

The prior default pilot had different live source pools and 41/64/35-second durations. These are **not controlled timing or retrieval comparisons**. The recorded stage durations measure the two actual scope-review calls, not a statistical latency effect. Creatine had no directional references to review; its recovery invocation also did not require a scope model call. Three cases do not establish p95, reliability or performance under load.

Reported pipeline token usage totals are 120,512 input, 17,280 output and 4,771 thinking tokens across these three reports. These are the pipeline's reported fields, not an invoice, and thinking should not automatically be added to output for billing. The output groups analyzer stages together; it does not isolate per-scope-call token cost. Raw per-case counters and model receipts are retained. No model-price assumptions were introduced.

## Quality findings

The three decompositions each retain one substantive element. SELECT preserves its named trial, relative effect, composite endpoint and population. Creatine's fourteen mapped references remain contextual, with the explanation distinguishing treatment/progression in diagnosed patients from prevention of onset. It no longer claims that a progression trial disproves prevention in this run.

The SELECT report still contains an overclaim: PDF source `ev-9a4a90c5321b` at `mediacenteratypon.nejmgroup-production.org/NEJMoa2307563.pdf` is represented by a short methods/background fragment. Its support explanation merely says the excerpt references the trial and population; it does not establish the asserted 20% result. The saved payload begins with an unrelated 2% fragment and then randomisation/methods text. Study-identity compatibility is not sufficient evidence for the complete quantitative assertion. Other SELECT sources can support the report's overall state, but that does not justify this individual label. This is a source-fragment fidelity failure, not a claim about the actual trial's result.

Passage review remains incomplete: Venus 7/13 assessed pairs, creatine 10/12 and SELECT 9/15; each carries `needs_review`, including conflicts or invalid responses. Final scope review inspected all eligible directional pairs in these particular runs, but its `complete` status means the bounded process finished, not that every relationship is justified. The remaining PDF overclaim demonstrates this limit directly. Source-role accuracy, source identity and study independence remain open.

## Broader frozen synthetic controls

Four new cases, each with three fixed fictional source snippets, were defined before execution and run twice. They test named-study identity, population boundaries, observational association as the actual claim, and mortality versus hospital-admission endpoints. The expectations were not changed after observing results.

Strict expected-relationship checks: **20/24**.

- Two failures discard genuine synthetic direct-trial support as context. The existing recital gate's substring-overlap rule marks it as “restates the claim” even though the supplied fixture reports the claimed randomized finding. An offline invocation of the real parser reproduces this with both default and candidate flags. It is not introduced by final scope review; that review deliberately cannot promote an already contextual reference.
- Two failures are absent expected context references (a child-population source and a different named study, each once). They are mapping omissions, not false directional support. The source inputs remain present. They remain failures of the predeclared exact-label test; the scoring was not weakened to accept omission after the fact.
- The direct observational association stays support when association is what the claim asserts. Correct-population null findings retain challenges. The population and endpoint cases pass all their checks. The wrong-study text deliberately mentions that it does not report the target trial, so simple identifier occurrence alone cannot certify applicability.

These are synthetic diagnostic cases, not a knowledgeable-human held-out benchmark. The existing recital exclusion should not be disabled just to make the set green: its purpose is to prevent a claim being repeated from counting as independent evidence. The next correction must distinguish an actually reported result from mere repetition and preserve explicit attribution protections.

## Next bounded work and validation

The next priority is result-level evidence fidelity: a directional label must address the complete assertion, including effect measure, while a direct finding must not be discarded merely for resembling the claim. Freeze the PDF-fragment failure and recital counterexample together with genuine attribution/recitation controls. Preserve ledger sources, original interpretations and receipt history. Do not equate exact text occurrence, study-name occurrence or a completed review with entailment.

This is directly within the original plan's requirement that report structure faithfully reflect material actually read. The candidate stays OFF until these broader failures and integrated acceptance are resolved. The original human-review and 8/10 gates are not satisfied by successful execution.

- Local reports and timing: `tmp/integrated-candidate-pilot/{venus,creatine,select}/`.
- Frozen broader protocol/results and default/candidate recital isolation: `tmp/broader-scope-pilot/`.
- Tracked summaries: `backend/tests/evaluation/passage_quality/integrated_candidate_results.json` and `broader_scope_results.json`, with source-output hashes, counts, timing and all failed expectations.
- Full default replay `tmp/quality-replay-integrated-candidate.log`: 185 ok / 1 warn / 13 known fail / 2 unexercised, zero cassette drift; expected exit 1. No goldens or cassettes changed. No application changes or new activation in this assessment phase.
