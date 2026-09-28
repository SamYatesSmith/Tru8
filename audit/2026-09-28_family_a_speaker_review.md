# Family A (speaker resolution + measurer release): independent review (2026-09-28)

**Reviews:** `audit/2026-09-28_family_a_speaker_design.md`.
**Method:** read-only. I read `recital_scope.py`, `interested_party.py`, the gate wiring (`claim_map_analyzer.py:2932-3091`), `runner.attach_claim_subjects`, the 018F golden, and the recital, narrowing, R6, interested-party and wiring tests. I wrote an offline prototype of A1 and A2 as the design states them. The prototype plugs into the real `recital_match` (through its `release` hook, with real R0–R6 still applied) and the real `released_subjects` / `interested_party_match`. Scripts: `a1proto.py`, `a2proto.py`, `probes1-3.py`, `corpus_diff.py` in the session scratchpad. No model calls, no network, no spend. Baseline: the 9 relevant test files pass, 178 passed.
**Caveat:** the prototype is my reading of the design. Where the design is ambiguous I say so, and show both readings.

**Overall: the two faults are real, but both fixes need rework before build.** A1 changes what the recital gate is for, and loses genuine self-recitals by the claim's own subject. A2 does not fix its own motivating record as written, and it widens the recital gate's R3 release onto third-party sayings.

| Part | Verdict |
|---|---|
| §1 diagnosis A1 (#7 marker is not the subject speaking) | **APPROVE** for #7; the "general class" framing is wrong (F1) |
| §1 diagnosis A2 (element restriction withholds #10) | **APPROVE**, with one missing half (F8) |
| §2 A1 speaker resolution | **REWORK** (F1–F5) |
| §2 A2 measurer release | **REWORK** (F6–F11) |
| §2 place-name token fix | **REWORK** (F12) |
| §3 guards | **APPROVE WITH CHANGES** (F3, F10, F11) |
| Invariant #7 | both parts tilt (F13) |
| Gate order / one owner / receipts | **APPROVE WITH CHANGES** (F14) |
| §5 verification | **APPROVE WITH CHANGES** (F15) |

---

## Findings on A1

Probe results read `old → new`: does the recital gate fire today, and would it fire under A1.

**F1. A1 changes the gate's purpose. The subject anchor was a proxy, not the rule.** The founding design says a recital is a claim made "by the claim's subject **or anyone else**" (`2026-08-13_assertion_evidence_design.md` §3a). The subject token was only how the machine found attribution. A1 turns "anchored near the subject" into "spoken by the subject". Third-party recitals that fire today stop firing:

| Sentence (claim "Donald Trump stopped 6 wars", supports) | old → new |
|---|---|
| Trump's spokesman said the president has ended six wars. | True → **False** |
| The Trump administration claims six wars have ended. | True → **False** |
| Trump has ended six wars, his spokesman said. | True → **False** |
| According to administration officials, Trump has ended six wars. | True → **False** |
| Trump ended six wars, Rubio said. He said the talks took months. | True → **False** |
| Trump's aides said he never claimed six wars. (challenges) | True → **False** |

The design's possessive/office rule covers the `according` form only. The same speakers in the `verb` form are lost. For an ORG subject, "According to the company, Tesla delivered a record 500,000 cars" and "According to its spokesperson, Tesla…" also go True → False (`its` is not in the design's possessive list).

**F2. A1 loses the subject's own self-recitals when any adverbial intervenes. This is the TRU-018F class itself.** `_SPEAKER_BRIDGE` accepts only auxiliaries and `-ly` adverbs:

| Sentence (supports) | old → new |
|---|---|
| Trump on Tuesday claimed he had ended six wars. | True → **False** |
| Trump last week said he had ended six wars. | True → **False** |
| Trump in a Truth Social post claimed he had ended six wars. | True → **False** |
| Trump, who has repeatedly boasted of ending six wars, spoke at the UN. | True → **False** |
| Tesla on Thursday announced a record 500,000 deliveries. | True → **False** |

These are the most common way news prose reports a politician's boast. Losing them lets a press recital support the boast again. The subject-free restatement path does not backstop them: it needs 60% of the claim contiguous, and on a multi-part claim it catches almost nothing. On #7's 250-character claim, "Democrats lead 49-47 on the generic ballot…" and even a verbatim copy of its second half both return `None`. The design's line "a source that merely recites 'Democrats lead 49–47' is still scoped" is false.

**F3. The pinned tests cannot see F1 or F2.** I ran all 29 fire-expected sentences from `test_recital_scope.py`, `test_recital_narrowing.py` and `test_recital_direction_release.py` through the prototype: **0 of 29 lost.** Every pin uses a tight form ("Trump said", "President Trump has repeatedly claimed"). So "every existing test passes" is no evidence that A1 is safe.

**F4. A1 still fires wrongly on the forms it targets.**

| Sentence (Cook claim, subjects cook / democrats / trump) | old → new |
|---|---|
| According to the poll Democrats hold a two-point advantage. (no comma) | True → **True** |
| Democrats hold a two-point lead, it said. | True → **True** |
| Reform UK polled 29%, it said. (subject reform uk) | True → **True** |

The according-phrase has no end without a comma. The pronoun branch takes `it`/`they`, which usually refer to the poll or outlet, not the subject. The R6 review already required `he|she|I|we` for a person and `it|they` only for an ORG; A1 drops that.

**F5. Sharing one speaker function with R6 inverts the R6 review's rule.** That review said: "for release, count only matches whose token is the grammatical head … **Firing keeps the loose anchor.**" A strict test is safe for a release and dangerous for a fire, and vice versa. If A1 widens the shared function (pronoun branch, appositive removal, office terms), R6 releases more challenges. I found no concrete harmful release in a short probe, because `classify` reads only the tail after the match. But the coupling must be explicit, and R6's own probes must run against the shared function.

**What #7 actually needs.** #7's marker is Cook's own page naming its own document: "According to the September 2026 toplines". That is R1's family (the source naming itself), not a speaker problem. A narrower rule fixes #7 and "the poll said" without touching F1 or F2:
- **`according` kind:** skip when the according-phrase names no subject token and its head is a document or instrument noun (`toplines|poll|survey|data|figures|results|study|research|report|bulletin|index|estimates|analysis`), with or without a following comma.
- **`verb` kind:** skip when the verb's own subject is "(the|this|that|its|our|latest) + instrument noun" ("the poll said", "the survey says").
- Every person or agent speaker keeps firing, whoever it is.

## Findings on A2

Probe results read "gate fires": today → A2. For `interested_party_match` on the org's own domain.

**F6. As written, A2 does not fix #10.** "The org's token appears after the finding head" is ambiguous. #10's claim is "Central Bank of Ireland research … shows multinational activity has been key to **Ireland's** economic outperformance". `ireland` is one of the subject's two distinctive tokens.
- Any-token reading: centralbank.ie **still fires** (True → True).
- First-token reading (`central`): released. But "…research shows multinational activity has been **central** to Ireland's growth" then withholds again (A2 fires), because the first token is a common word.

The rule must name what counts: the whole subject phrase, or its acronym, not a single token.

**F7. A2 releases interested measurers on their own product, leader or campaign.** The gate fires on each today; A2 releases each:

| Claim | Domain | today → A2 |
|---|---|---|
| Tesla data show Autopilot is ten times safer than human drivers. | tesla.com | True → **False** |
| Vote Leave analysis shows EU membership costs Britain 350 million pounds a week. | voteleavetakecontrol.org | True → **False** |
| Labour analysis shows Conservative tax plans would cost families 2,000 pounds. | labour.org.uk | True → **False** |
| Reform UK poll shows Nigel Farage will be the next prime minister. | reformparty.uk | True → **False** |
| Pfizer trial data show the vaccine is 95% effective. | pfizer.com | True → **False** |
| An Exxon study shows **the company's** emissions fell 20%. | exxonmobil.com | True → **False** |
| Exxon's emissions fell 20% last year, an Exxon analysis published in March estimated. | exxonmobil.com | True → **False** |

The last two defeat the "refers back" rule: "the company's" is not in `its|their|our|own`, and a finding placed before the act has no head to search after. The Vote Leave and Reform rows are the TRU-018F shape (a campaign's own say-so on its own cause) in ORG form. A government department on gov.uk is not exposed, because prong 1 cannot match `gov.uk`; "DHSC data show waiting lists fell" fires neither today nor under A2. "NHS England data show waiting lists fell" (england.nhs.uk) goes True → False.

**F8. A2 opens the recital gate on third-party sayings, through R3.** R3 releases by token on every source's text, not only on the org's own domain, and for every match kind, including saying verbs. Claim "Vote Leave analysis shows … £350m a week", element "EU membership costs Britain 350 million pounds a week", a news source filed supports:
- "Vote Leave has repeatedly claimed that Britain sends the EU 350 million pounds every week." Today: fires ("vote leave has repeatedly claimed"). A2 via R3: **silent.** A news report of a campaign's claim now supports the bare element.

That is a support-tilting hole that did not exist before, and no test in §3 covers it.

**F9. A2 alone still leaves #10 open on the reasoning path.** I simulated A2 by disabling interested-party and ran #10's text through the real wired parser. The ref falls through to the recital gate on "according to Central Bank of Ireland research":

| e2 wording | mapper reasoning | result |
|---|---|---|
| "MNE activity added 1.2 per cent to annual growth since 2022." | "States MNEs added 1.2 pp…" | context (recital, evidence, "according to central") |
| same | "States that, according to Central Bank of Ireland research, MNEs added 1.2 pp a year." | context (recital, **reasoning**) |
| "…to growth in Ireland since 2022." | "States MNEs added 1.2 pp…" | supports (released only by the place-name token) |

A2 feeds R3, which fixes row 1. R3 is evidence-path only, so row 2 stays context. A1 makes this worse, because it confirms the Central Bank is the speaker. Whether #10 is fixed depends on the stored reasoning string, which the design has not read.

**F10. A2 flips a pinned test, and the design does not say so.** `test_the_element_can_withhold_a_release` (`test_assertion_evidence_wiring.py:728`) asserts Cook's page stays context on "Democrats lead Republicans in competitive districts." A2 makes it supports. That may be right, but the design must name it and replace it with the case the element restriction was guarding.

**F11. A2 closes a hole the design does not know it has.** The §3 guard "Exxon's own study shows its emissions fell 20%: exxonmobil.com stays gated on every element" **fails today** when the element names the company. With element "Exxon's emissions fell 20%.", `released_subjects` releases Exxon, because the current element test is "names the subject or the act". Naming the subject is exactly the self-interested case. A2's claim-level "its" check gates it. Pin this, because it is the strongest argument for A2.

## Other findings

**F12. The place-name fix does not do what it says.** "The org's first distinctive token" is not a place-name filter:
- `nhs england` → only token `england`.
- `bank of england` → `england` (`bank` is stop-listed).
- `government of ireland` → `ireland`.
- `central bank of ireland` → `central`, a common word ("central to").

It fixes #10 by accident of word order. Thirlwall (`8d66d41a`) is unaffected: its element is released by the act word ("specified"), not by a token. The saying-branch tests all still pass on my reading, but no test pins a place-name case in either direction.

**F13. Invariant #7.**
- **A1 is symmetric in mechanism, not in exposure.** The fires it loses (F1, F2) are mostly the subject's own boasts and its allies' repetitions. On a boast claim they are supports. So on the flagship 018F class A1 tilts toward supports. On an accusation claim ("Biden caused inflation") the lost fires are denials, so it tilts toward challenges. Neither is acceptable.
- **A2 tilts toward supports by construction.** A measurer's own page almost always agrees with a claim that reports its finding. That is correct for Cook and the Central Bank. It is sycophantic for Vote Leave, Labour, Reform and Tesla (F7), and F8 extends it to third-party texts.

**F14. Gate order, one owner, receipts.**
- **Interested-party → recital fall-through is real (F9).** A ref interested-party owned today is now judged by recital. The design says the two gates "stay consistent" through R3. That is true for the evidence path only.
- **A1 fall-through.** A ref recital no longer owns now reaches absence-of-evidence, same-study and echo. That is harmless as far as I can see, but it is unmeasured.
- **`_SCOPE_RECEIPT_KEYS`.** No new gate key is added, so no change is needed there. But a release is invisible: the interested-party summary lists `released_subjects` with no reason. A2 should write why ("claim reports this organisation's own research"), so the reader can see the support comes from the measurer itself (invariant #5).
- **R6.** See F5.

**F15. The verification plan has no power where the risk is.**
- **Corpus:** I ran A1 over every directional reasoning string in the 10 cassettes: 145 strings, **1 fire today, 0 changed.** The 018F golden pins recital at 0/0 (all 21 directional refs are challenges). The corpus cannot see F1, F2 or F8. The bench step checks cassettes and pins only.
- **19 payloads:** the design says fetching them needs the founder. Public payloads carry `textProvenance` without a key. Check whether the public payload also carries ref reasoning. If it does, the fire-diff needs no founder step.
- **Missing population:** a fire-diff over stored refs only finds fires that exist. F1, F2, F7 and F8 are about fires that would be lost on sources not in these 29 records. The adversarial sentences in this review must become tests, in both directions.
- **Missing measurement:** read #10's stored e2 description, `subject_kinds` and the CBI ref's reasoning string (F9), and #7's `subject_kinds` (is `democrats` an ORG?), before building.

## Required changes, in priority order

1. **Replace A1 with an instrument-speaker skip (F1–F4).** Skip an `according` match whose phrase names no subject token and whose head is a document or instrument noun, with or without a comma. Skip a `verb` match whose immediate subject is an instrument noun phrase. Every person or agent speaker keeps firing. Pin every F1 and F2 sentence as "still fires", both directions.
2. **If any speaker logic ships, do not share R6's function for firing (F5).** Keep a loose test for firing and a strict one for release. Run R6's full probe set against whatever changes.
3. **Define "refers back" on the subject phrase, not a token (F6).** Match the whole subject name, its acronym, or `its|their|our|own|the (company|firm|group|party|campaign|organisation|bank|charity)'s`. Require the act to come before the finding, and withhold when there is no finding head. Pin #10 verbatim, plus the "central to" variant.
4. **Decide the interested-measurer question before build, as a founder call (F7).** The only signal available without an org list is weak: withhold A2 when the subject is also the claim's `claimant`. Parties and campaigns are typed plain `ORG` (`extract.py:496`), so nothing else separates Vote Leave from the Central Bank. The honest options are (a) accept and disclose the release on the element, or (b) add a subject-kind for parties and campaigns at extraction, which is a prompt change and re-keys cassettes. Pin Vote Leave, Labour, Reform and Tesla either way, so the choice is visible.
5. **Do not feed A2 into R3 as it stands (F8).** R3 should release only `according`-kind matches whose phrase names the organisation's measurement noun ("according to Central Bank of Ireland research"), never saying verbs ("Vote Leave claimed"). Pin the Vote Leave news-report sentence as "still fires".
6. **Apply the same R3 release to the reasoning path (F9),** limited as in change 5. Otherwise #10 depends on the mapper's wording.
7. **Rewrite `test_the_element_can_withhold_a_release` deliberately (F10),** and add the F11 Exxon case (element names the company, stays gated).
8. **Drop or redo the place-name fix (F12).** If kept, use a closed list of country and nation names, and pin Bank of England, NHS England and Central Bank of Ireland.
9. **Add a release reason to the interested-party receipt (F14).**
10. **Verification (F15):** fire-diff over the public payloads if they carry reasoning; read #7 and #10's stored fields first; add the adversarial set in this review as the regression suite; report lost and gained fires by direction and by claim type (boast or accusation).
