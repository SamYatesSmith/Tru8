# Verification of the 2026-09-10 improvement claims — recomputed from the raw sheets

**Why this exists:** the founder asked (2026-09-10, after run 3) *"verify your assertions on improvement are accurate please"*. Everything below is recomputed by script from `audit/review_sheets/*/labels_reviewed.csv` and the regrade `owner.json` files — not from my summaries. Script output verbatim; my reading follows it.

## Verdicts

1. **Rates: ACCURATE.** Recomputed from the CSVs, same primary reviewer model on all five sheets (gemini-3.5-flash-lite): 86.1 / 81.6 before → 87.6 / 86.0 / 89.0 after.
2. **"No element carried a precision word": ACCURATE, mechanically.** 3 and 8 elements before → 0 / 0 / 0 after, over every element of every run.
3. **"The targeted kind is 0/45": ACCURATE by judgement, 1/45 by a loose regex.** The regex's single after-hit (run 1, t09) is a *date the claim itself states* ("July 21, 2010") — the reviewer said the passage lacks it, which is a passage fault, not invented specificity. Before: 8/19 and 18/27 by the same regex (26 of 284 labels). Exact test: the chance that ≤1 of those 27 rejections would land in the 362 after-labels with no real change is **4×10⁻⁹**. This claim is solid.
4. **"The blind rate went up": TRUE but NOT statistically distinguishable from pool noise at this sample size.** Pooled 83.8% → 87.6%, z = 1.37, p = 0.17. I said "up from 81.6 and 86.1" — the numbers are right, but a reader should not take the 3.8-point rate move as proven. The *kind* result is the proven one; the rate follows from it only as far as the EV record (11 → 5 → 1 → 0 rejections) carries it.
5. **Structure held on the headline outcomes** (Bank Rate 4.25% disputed and 3.75% supported on every run; JWST orbit disputed; SELECT population and absolute-risk disputed; SQLite "cannot occur" disputed; Sweden causation disputed; the invented trial unresolved). Pool-draw variance shows on t01 (run 2: single-market/customs elements unresolved off a 6-label pool) and t03/t11 (a causal element U or C on one run each).
6. **One anomaly found by this check, not by the review:** run 3 t04 JWST's *mirror* element (a 6.5 m fact) read `disputed` — two primary supports, one challenge from a source stating "5 meters", and **three further supports demoted to context by the echo gate** (derivatives of the same NASA original). Two supports vs one challenge is exactly the 2× tie, which the strict `>` rule reads as `close_split` → `disputed`. So a single wrong source can dispute a settled fact once echo scoping has removed the corroboration. Not today's change (echo gate 2026-08-17, tie rule 2026-08-14) and not today's disease — recorded as a candidate: **weight or the tie rule should not let one erroneous source dispute a fact that N independent primaries state**.

## Script output

```
## Rates recomputed from labels_reviewed.csv (primary reviewer = gemini column)
| run | labels | Y | N | rate | reviewer model per summary |
| 09-09 first | 137 | 118 | 19 | 86.1% | gemini (gemini-3.5-flash-lite), gemini_flash (gemini-3.7-flash) |
| 09-09 post-fix | 147 | 120 | 27 | 81.6% | gemini (gemini-3.5-flash-lite), gemini_flash (gemini-3.7-flash) |
| 09-10 run 1 | 138 | 120 | 17 | 87.6% | gemini (gemini-3.5-flash-lite), gemini_flash (gemini-3.7-flash) |
| 09-10 run 2 | 107 | 92 | 15 | 86.0% | gemini (gemini-3.5-flash-lite), gemini_flash (gemini-3.7-flash) |
| 09-10 run 3 | 118 | 105 | 13 | 89.0% | gemini (gemini-3.5-flash-lite), gemini_flash (gemini-3.7-flash) |

## Per-record rejections (gemini N) across the five runs
| record | 09-09 first | 09-09 post-fix | 09-10 run 1 | 09-10 run 2 | 09-10 run 3 |
| t01_brexit | 0/14 | 0/16 | 0/14 | 0/6 | 0/12 |
| t02_select | 1/12 | 1/13 | 1/14 | 1/13 | 5/12 |
| t03_creatine | 4/7 | 4/9 | 1/7 | 3/8 | 2/6 |
| t04_jwst | 0/16 | 0/14 | 0/9 | 1/10 | 0/9 |
| t05_bankrate_425 | 0/3 | 0/1 | 0/2 | 0/1 | 0/2 |
| t06_sweden_focus | 1/12 | 3/7 | 4/13 | 0/3 | 1/6 |
| t07_sqlite_busy | 4/11 | 3/16 | 3/13 | 4/12 | 3/16 |
| t08_ev | 1/17 | 11/29 | 5/27 | 1/16 | 0/17 |
| t09_sqlite_url | 1/17 | 0/17 | 1/9 | 0/11 | 0/12 |
| t11_inflation | 1/4 | 0/7 | 1/6 | 0/7 | 1/7 |
| t12_venus_image | 1/10 | 2/6 | 1/10 | 3/8 | 0/8 |
| t13_sweden | 2/8 | 1/8 | 0/7 | 1/7 | 1/6 |
| t14_bankrate_375 | 3/6 | 2/4 | 0/6 | 1/5 | 0/5 |

## Precision-word scan of EVERY element (from owner.json) per run
- 09-09 first: 42 elements, 3 with a precision word
    - t03_creatine: The target population consists strictly of healthy adults who do not currently have dementia.
    - t03_creatine: The intervention involves taking a daily dose of exactly 5g of creatine.
    - t07_sqlite_busy: Enabling write-ahead logging in SQLite completely eliminates reader-to-writer and writer-to-reader blocking.
- 09-09 post-fix: 41 elements, 8 with a precision word
    - t03_creatine: Healthy adults consistently consume 5g of creatine daily.
    - t05_bankrate_425: The Bank of England has set its benchmark Bank Rate to a level of 4.25% specifically for the date of 7 Septemb
    - t07_sqlite_busy: The absence of reader-writer blocking in write-ahead logging mode completely prevents SQLITE_BUSY errors under
    - t07_sqlite_busy: No other conditions or operations within SQLite besides reader-writer contention can trigger a SQLITE_BUSY err
    - t08_ev: What is the total lifecycle greenhouse gas emission volume associated with the manufacturing and operation of 
    - t08_ev: What proportion of the electricity used to charge electric cars is generated from fossil fuels across major ve
    - t12_venus_image: Venus has a quantified average surface temperature that is higher than that of any other planet in the Solar S
    - t12_venus_image: Every other planet in the Solar System has a verified maximum surface temperature lower than that of Venus.
- 09-10 run 1: 39 elements, 0 with a precision word
- 09-10 run 2: 40 elements, 0 with a precision word
- 09-10 run 3: 38 elements, 0 with a precision word

## Rejections whose reviewer reason names an unstated figure/absolute/qualifier (mechanical regex on the reason)
- 09-09 first: 8 of 19 rejections
    - t03_creatine | The intervention involves taking a daily dose of exactly 5g of creatin | The passage recommends a range of 3 to 5 grams per day, which does not specifically support or challenge the requirement
    - t03_creatine | The intervention involves taking a daily dose of exactly 5g of creatin | The passage mentions a general dose range of 3-5 grams per day, which does not specifically support or challenge the req
    - t03_creatine | The intervention involves taking a daily dose of exactly 5g of creatin | The passage states that 3 to 5 grams daily is sufficient for most adults, which does not specifically confirm a daily do
    - t03_creatine | The intervention involves taking a daily dose of exactly 5g of creatin | The passage mentions a general range of 3 to 5 grams used in most studies, but does not state that the specific interven
    - t07_sqlite_busy | Enabling write-ahead logging in SQLite completely eliminates reader-to | The passage challenges the claim by stating that leaving a transaction open too long or attempting to upgrade a transact
    - t07_sqlite_busy | Enabling write-ahead logging in SQLite completely eliminates reader-to | The passage states that readers can run concurrently with a 'single write transaction' and relaxes restrictions 'somewha
    - t07_sqlite_busy | Enabling write-ahead logging in SQLite completely eliminates reader-to | The passage states that WAL allows concurrent reads during writes, but it does not mention eliminating reader-to-reader 
    - t14_bankrate_375 | The next decision date for the Bank of England's Bank Rate is 17 Septe | The passage mentions a vote on 17 September without specifying the year 2026, making it too thin to confirm the exact da
- 09-09 post-fix: 18 of 27 rejections
    - t03_creatine | Healthy adults consistently consume 5g of creatine daily. | The passage recommends a range of 3 to 5 grams per day for people who take creatine, which contradicts the claim that he
    - t03_creatine | Healthy adults consistently consume 5g of creatine daily. | The passage discusses creatine use in older adults and notes low dietary intake, but it does not mention healthy adults 
    - t07_sqlite_busy | The absence of reader-writer blocking in write-ahead logging mode comp | The passage notes that writes do not run in parallel and still queue despite WAL mode, contradicting the absolute absenc
    - t07_sqlite_busy | No other conditions or operations within SQLite besides reader-writer  | The passage discusses transaction throughput and busy timeouts in SQLite, but does not address whether conditions other 
    - t07_sqlite_busy | No other conditions or operations within SQLite besides reader-writer  | The passage discusses common scenarios where SQLITE_BUSY occurs in WAL mode, but it does not address whether reader-writ
    - t08_ev | What is the total lifecycle greenhouse gas emission volume associated  | The passage discusses the percentage reduction in emissions by electric vehicles compared to gas-powered vehicles, but i
    - t08_ev | What is the total lifecycle greenhouse gas emission volume associated  | The passage discusses emissions per mile and vehicle efficiency, but it does not provide the total lifecycle greenhouse 
    - t08_ev | What is the total lifecycle greenhouse gas emission volume associated  | The passage mentions that electric vehicles have a life cycle emissions advantage in certain areas, but it does not prov
    - t08_ev | What is the total lifecycle greenhouse gas emission volume associated  | The passage discusses the timeframe in which EVs offset their emissions compared to gas-powered vehicles, but does not s
    - t08_ev | What is the total lifecycle greenhouse gas emission volume associated  | The passage only provides a fact-check rating and mentions missing context, without containing any information about the
    - t08_ev | What is the total lifecycle greenhouse gas emission volume associated  | The passage only mentions manufacturing emissions and does not provide the total lifecycle greenhouse gas emission volum
    - t08_ev | What is the total lifecycle greenhouse gas emission volume associated  | The passage discusses the general fact that electric vehicles have lower lifetime emissions than petrol cars and higher 
    - t08_ev | What is the total lifecycle greenhouse gas emission volume associated  | The passage mentions that the research analyzed the full lifecycle emissions of EVs and petrol cars, but it does not sta
    - t08_ev | What proportion of the electricity used to charge electric cars is gen | The passage discusses overall carbon emissions, zero-carbon power growth in Britain, and tailpipe emissions, but it does
    - t08_ev | What proportion of the electricity used to charge electric cars is gen | The passage discusses the general environmental benefits of EVs and mentions that electricity sources vary by region, bu
    - t08_ev | What proportion of the electricity used to charge electric cars is gen | The passage discusses projected reductions in grid emissions for the United States by 2030, but does not provide informa
    - t12_venus_image | Venus has a quantified average surface temperature that is higher than | The passage states that Venus is the hottest planet, but it does not provide a quantified average surface temperature as
    - t12_venus_image | Venus has a quantified average surface temperature that is higher than | While the passage provides a quantified average surface temperature for Venus, it does not compare it to other planets i
- 09-10 run 1: 1 of 17 rejections
    - t09_sqlite_url | SQLite made the Write-Ahead Log option available beginning with versio | The passage only mentions that SQLite version 3.7.0 will feature WAL capability, but does not provide evidence confirmin
- 09-10 run 2: 0 of 15 rejections
- 09-10 run 3: 0 of 13 rejections

## Significance
- pooled rate: before 238/284 = 83.8%  after 317/362 = 87.6%  z=1.37 p=0.172
- kind under test (regex): before 26/284 labels, after 1/362 labels

## Kind claim, exact: P(<=1 of 27 land in the after-group by chance) = 4.35e-09

## Structure check — element states per input across the five runs (regression guard on the headline outcomes)
| input | 09-09 post-fix | run1 | run2 | run3 |
| t01_brexit | SSS | SSS | SUU | SSS |
| t02_select | DSD | SDD | DSD | SDD |
| t03_creatine | SDD | SSD | SDC | SUC |
| t04_jwst | DSS | DSS | DSS | DDS |
| t05_bankrate_425 | D | D | D | D |
| t06_sweden_focus | SDD | SDD | UDC | SDD |
| t07_sqlite_busy | SDD | SD | SD | SD |
| t08_ev | SUSS | SSS | SSU | SUS |
| t09_sqlite_url | SS/SS/CC | S/SUU/C | S/USS/C | S/SUD/C |
| t10_lantern | UC | UUU | UUUU | UUU |
| t11_inflation | SDD | SDD | UDD | CDD |
| t12_venus_image | SC | SS | SS | S |
| t13_sweden | SDD | SDD | SDD | SDD |
| t14_bankrate_375 | SS | SS | SS | SS |
S=supported D=disputed U=unresolved C=context; one string per claim, one letter per element

```
