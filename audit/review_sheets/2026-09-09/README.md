# Human review of directional relationships — 2026-09-09 regrade records

Astra's 8/10 gate (`tmp/tru8-hands-on/tru8-route-to-eight.md`, Evidence fidelity): a knowledgeable human reviews at least 200 directional relationships; target at least 95% justified support/challenge labels, misses reported by kind, a second reviewer on ambiguous cases.

These sheets carry **137 directional labels** across 14 records from the final default-configuration regrade of Astra's 14 inputs (`tmp/astra-regrade-final/`, branch `codex/evidence-quality`).

## Protocol

1. Open a sheet. For each label, read the element, the system's reasoning and the passage the mapper was given. Decide **Justified? Y / N / Unsure** — is the label warranted by what the source says about *that* element?
2. If N: name the kind — `direction`, `absent`, `scope`, `recital`, `other` — and write one line.
3. Record answers in `labels.csv` (columns `justified`, `kind`, `note`), one row per label; `label_id` matches the heading in the sheet.
4. Do not look up the source live unless the passage is insufficient to decide; if you do, say so in the note. The question is whether the label is justified by what the system read.
5. Context-only and set-aside lists are not graded; flag one only if you think it should have been directional or a rule fired wrongly.

## Tally

`justified rate = Y / (Y + N)`; report Unsure separately; report kinds of N. Anything under 95% names the next build.

| Record | Directional labels |
|---|---:|
| t01_brexit | 14 |
| t02_select | 12 |
| t03_creatine | 7 |
| t04_jwst | 16 |
| t05_bankrate_425 | 3 |
| t06_sweden_focus | 12 |
| t07_sqlite_busy | 11 |
| t08_ev | 17 |
| t09_sqlite_url | 17 |
| t10_lantern | 0 |
| t11_inflation | 4 |
| t12_venus_image | 10 |
| t13_sweden | 8 |
| t14_bankrate_375 | 6 |

| **Total** | **137** |

## Blind AI review, run 2026-09-09 (founder-approved; no human reviewer was available or affordable)

`backend/scripts/review_labels.py` shows each reviewer ONLY the element and the passage the mapper read — never Tru8's label or reasoning — and asks supports / challenges / neither. Results in `review_summary.md` and `labels_reviewed.csv`.

| Reviewer | Scored | Justified | Rate |
|---|---:|---:|---:|
| gemini-3.5-flash-lite (a different model from the mapper) | 137 | 118 | **86.1%** |
| gemini-3.7-flash (the mapper's own model, weaker independence; 45 no-responses on a 200-token budget) | 92 | 79 | 85.9% |

Reviewer-to-reviewer agreement 95.7% on the 92 both scored; both reject 9. The OpenAI key is dead (401), so no second model family was available; Claude did not grade.

**Reading the 19 rejections by hand:** 4 are the creatine element that says "exactly 5g" while every source says 3–5 g — the decomposition invented the precision (the premise-element class again); 3 are Bank Rate supports where the passage states 3.75% without the date or the institution — the reviewer applied the fact-anchor standard the candidate's gate applies; 4 are Tru8 mislabels the reviewer caught (inflation: a Fed passage labelled `supports` on an element phrased as the false proposition; Chocolatey: 23 January vs 22; Reddit Venus: compares only to Mercury; EV connectsci: "higher CO2 in the first two years" labelled as support); 3 look like reviewer errors (the Nature Sweden lockdown study read as supporting the causal claim it contradicts, twice; a Sweden–Norway comparison rejected as "not every other country" though Norway lower is exactly a challenge); the rest are arguable strictness on "completely eliminates" wording. **Adjudicated, the rate is roughly 88–90%: below Astra's 95%, with the misses concentrated in decomposition wording rather than in reading sources.**

Cost: ~86k tokens, about 2p. Re-run after any build with the same command; the rate holds or it names the next fix.
