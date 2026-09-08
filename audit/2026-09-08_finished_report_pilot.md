# Finished-report pilot — 8 September 2026

The [competing-source mapping pilot](2026-09-08_competing_source_pilot.md) passed its bounded relationship checks after correction. This next phase tests the original plan's broader report requirements through the default local pipeline. It finds concrete remaining decomposition, clinical-scope and source-origin failures. Candidate activation and the minimum 8/10 assessment remain withheld.

## Method and execution

Three new variants of the original Venus, creatine and SELECT cases were fixed before execution. These are diagnostic cases, not an untouched held-out benchmark and not reruns of the original production checks. Actual ingestion, classification, decomposition, retrieval, distillation, mapping and local persistence ran with the configured models. No candidate flag or model setting changed. Owner/public service responses were saved and compared directly; browser rendering, HTTP routing, worker delivery, PDF export and strengthening were not exercised in this phase.

The initial restricted-network batch produced WinError 10013 socket failures, fallback decomposition and no retrieved sources. It was stopped and excluded from quality assessment. A separately saved network-enabled batch then completed all three cases. Never interpret the invalid zero-source reports as a quality regression or compare their counts with the successful batch.

| Case | Local check | Sources | Elements | Mapped relationships | Directional | Seconds |
|---|---|---:|---:|---:|---:|---:|
| Venus axial rotation versus orbit | `1a087b93-ffd5-4d8b-9551-5154b2262e3a` | 11 | 1 | 9 | 4 | 41 |
| Creatine preventing Parkinson's onset | `705c9a59-8ac3-46fb-9f5c-d848828513b8` | 21 | 3 | 14 | 7 | 64 |
| SELECT population and relative cardiovascular effect | `cb7ea7a2-076c-44db-bdb0-180b051afbfb` | 16 | 3 | 16 | 12 | 35 |

All 39 displayed relationship explanations were read against their element wording and available saved source payloads. This is an agent diagnostic review, not a knowledgeable-human adjudication of 200 relationships. Inaccessible full texts and snippet-only sources prevent universal source-level validation; no precision percentage or quality score is assigned. Single runs with different live retrieval do not establish improvement relative to another version, completion reliability or p95 latency.

Owner/public source URL sets and snapshot identities agree in all three reports. These initial reports have unretained snapshot hashes, not archived revision IDs; agreement is not a new historical-signature verification result. The tracked evaluation summary includes hashes of the saved inputs and responses.

## Findings against the original plan

### Venus: useful decomposition, access labelling still imperfect

The one element faithfully compares axial rotation and orbital period and is supported by the retrieved NASA material. This variant avoids the original unnecessary-premise failure. NASA's [Venus facts](https://science.nasa.gov/venus/venus-facts/) supports the distinction.

The unmapped YouTube source `ev-23a4375d9e53` is labelled `contentBasis=full`, while its saved text consists of site navigation/legal boilerplate. It does not affect this result's support count, but shows that successful extraction still need not mean usable source content. A Snopes source has no content-basis value. Both are access-contract issues to retain in the register, not reasons to erase the source ledger.

### Creatine: the original decomposition and endpoint problem recurs

Element e1 asserts successful ingestion and absorption, which is a vacuous prerequisite for the user's prevention question. E2 introduces a specific brain mechanism absent from the claim. The primary efficacy element e3 is labelled disputed and its uncertainty says trials contradict prevention or slowing, combining two distinct endpoints.

Seven challenge explanations on e3 cite progression, treatment or clinical outcomes in people already diagnosed. At minimum, the JAMA trial (`ev` identified by its URL in the saved ledger) and Cochrane review explanations explicitly address progression/function in patients, not incidence among initially unaffected people. They do not by themselves establish that prevention fails. The original [NET-PD trial publication](https://pubmed.ncbi.nlm.nih.gov/25668262/) concerns clinical progression; the [NINDS trial description](https://www.ninds.nih.gov/health-information/clinical-trials/national-institute-neurological-disorders-and-stroke-ninds-parkinsons-disease-neuroprotection-trial) likewise distinguishes that research question. This is an evidence-scope assessment, not medical advice or an assertion that creatine prevents disease.

The report does correctly keep rat/preclinical material contextual for the human mechanism element. That partial success does not cure the prevention/progression conflation. Fourteen of 21 source records are snippet-only; the report cannot be assessed as though all papers were read in full.

### SELECT: meaningful answer, imprecise decomposition and study attribution

The population element preserves established cardiovascular disease and absence of diabetes. The effect element retains the composite MACE endpoint. However, the magnitude element drops the user's explicit relative-effect wording and adds **exactly**. The uncertainty restores relative/absolute information and a confidence interval, but a caveat should not have to repair an overprecise element. The [original trial abstract](https://www.nejm.org/doi/abs/10.1056/NEJMoa2307563) defines the trial population and composite endpoint; direct full-text access during this review returned 403.

The original NEJM record `ev-986f2f5c57ae` is snippet-only and contains introductory background about patients with diabetes. Its context relationship is appropriate for the text actually retained, but the decisive source's result was not recovered there.

The PMC SCORE article `ev-6633542995a2` is a distinct real-world study whose retained facts quote SELECT in its background. It is mapped as primary academic support for the SELECT causal element. The Wiley SCORE record `ev-1b3f9af549a3` is also mapped as primary support; its explanation explicitly promotes an association to causal support for that trial. The source title names SCORE, while the element names SELECT. These are concrete study-design/provenance failures visible from the saved records, not a claim that SCORE is poor research. The two records appear to be alternate hosts of the same publication; DOI identity should be verified before a deterministic deduplication rule is implemented.

Existing echo gates demote some derivative sources, but the basis still counts both SCORE-hosted items as primary support. Publisher concentration correctly says independence is not established; that disclosure does not itself correct study-level aggregation or distinguish a paper's original result from a cited trial in its introduction.

## Next bounded correction

1. Correct decomposition generically: preserve population, endpoint, comparator, effect measure and asserted precision; omit ingestion/existence/mechanism prerequisites unless the user actually asserts them. Test both single and batch decomposition. Keep simple atomic claims simple.
2. Enforce the same scope when mapping: progression is not onset prevention, association is not a named trial's causal result, and a paper's background citation is not its own original finding. Keep contextual evidence visible. Use frozen sources and repeated controls, including reverse/synthetic cases; no drug, institution, disease, value or domain-specific answer rules.
3. Verify study identity and original-versus-cited-result handling separately before changing independence weighting. Retain all source records and distinguish duplicate publication locations from independent evidence.

This returns directly to original plan items on decomposition, population/endpoint fidelity and independence. It is not another SQLite-only tuning phase. The candidate mapping gains are retained in their existing commits, with both experimental flags still OFF.

## Artifacts and validation

- Local successful outputs: `tmp/report-quality-pilot-network/{venus,creatine,select}/`: pipeline, owner, public, status and generated review Markdown. Invalid restricted batch: `tmp/report-quality-pilot/` (excluded).
- Tracked protocol/results: `backend/tests/evaluation/passage_quality/finished_report_pilot_results.json`. It records diagnostic findings and artifact hashes, not an automated pass certificate.
- Full replay: `tmp/quality-replay-report-pilot.log`: **185 ok / 1 warn / 13 known fail / 2 unexercised**, zero cassette drift; expected exit 1. No goldens/cassettes changed.
- No application code, production data, deployment, candidate activation or model change in this assessment phase. Local benchmark reports were created by the authorized tests. No source-removal change was made.

The original broader requirements still include a knowledgeable-human relationship review, representative held-out claims, operational fault testing, reviewer usefulness, annotations and portable evidence notes. Three reports do not satisfy those gates.
