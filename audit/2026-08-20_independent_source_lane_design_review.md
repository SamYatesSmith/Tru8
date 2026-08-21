# Design review — swapping the counter-frame for an independent-source lane

**Date:** 2026-08-20
**Question:** Phase D's counter-frame wording was measured and failed. The proposed replacement is
site-targeted retrieval of independent publishers. **Is that decision correct?**
**Method:** adversarial. Try to break the proposal against the code and the invariants, not
confirm it.

**Verdict: directionally right, wrongly named, and NOT correct as proposed.** It needs three
amendments — one of which is a genuine hazard the probe did not reveal — and it re-opens a signed
founder decision. Detail below.

---

## 1. The evidence for the swap

Four claims, same short keyword base, one query each:

| Claim | Counter-frame wording | Independent-source targeting |
|---|---|---|
| Trump / six wars | 2 results, 1 useful, 1 Facebook | **8** — Drezner, Krugman, Ferguson, Parsi, Ryan |
| UK CPI Sept 2024 | 3 results, 0 useful | **8** — all Gianluca Benigno CPI reports |
| Truss mini-budget | 4 results, 2 Facebook | **8** — Robin Brooks, Adam Tooze, Klement, Murphy |
| London 40.3C | 1 Instagram reel | 1, irrelevant |

The CPI row is the strongest single datum: it returns
`gianlucabenigno.substack.com/p/uk-september-25-cpi-inflation-report` as the **top** result — the
exact URL `TRU-C1A0-0005`'s golden requires as a hard invariant, and the one the Phase D recording
lost. It is retrieved reliably rather than by luck of ranking.

**Why the wording approach failed, stated mechanically:** AND-ing four rare terms onto a keyword
query is far too restrictive. Google requires the topic terms *and* one counter term; few pages
carry both, and those that do skew to social posts matching loosely. Hence 1–4 results, mostly
Facebook/Instagram.

**Why site-targeting works:** the recorded failure was never phrasing. `2026-08-13_assertion_evidence_design.md`
§7 says it outright — *"Substack/small-site rebuttals never entering the pool"*. That is a
**ranking** problem: small sites lose to mainstream ones on every query, whatever its wording.
Restricting the index removes the competitors. Changing words never addressed the mechanism.

---

## 2. 🔴 The hazard the probe did not show

**Three commentary items exactly satisfy the factual support floor.**

- `_STATE_TIER_WEIGHTS = {"primary": 3, "reporting": 2, "commentary": 1}` (`claim_map_analyzer.py:873`)
- `FACTUAL_MIN_WEIGHTED_SUPPORT = 3` (Phase B, shipped today)
- Substack / Medium / WordPress classify as **commentary** — they are on no blocklist and in no
  explicit classifier list (verified), so they land in the general commentary/analysis bucket.
- The proposed lane ceiling is **3**.

So the lane can contribute exactly weight 3 of support — **enough, entirely on its own, to carry a
factual element from `unresolved` to `supported`.** An element with no primary evidence at all
could be badged supported by three bloggers the claimant never cited.

That is a sycophancy mechanism built out of a lane whose stated purpose is the opposite. It is
worse than the fault it replaces, because it is silent: the counter-frame's failure was visible as
junk in the pool, this one would be visible only as a state change.

**Fix — lower the ceiling to 2.** Then the lane's maximum contribution is weight 2, which is
strictly below the floor of 3, so **it can never by itself satisfy the support floor.** That is an
arithmetic guarantee of the kind this codebase prefers to a judgement.

Note the asymmetry is correct and intended: the floor governs `all_supports` only, so a single
independent **challenge** still counts and still moves an element toward `disputed`. Ceiling 2
therefore preserves exactly the capability the lane exists for while removing the one it must
never have. It is not a compromise — it is the right number.

---

## 3. 🟠 Single-author monopoly — and the cap does NOT catch it

The CPI probe returned **8 of 8 results from one author**. Take the top 3 and the lane imports one
blogger's back catalogue rather than three independent voices.

`_apply_domain_concentration_cap` (`runner.py`) does **not** protect against this. Its docstring is
explicit: it demotes excess **primary/reporting** items to commentary, and *"Items already at
tier='commentary' are counted toward visual presence at that domain but are never re-demoted."*
Substack items arrive as commentary, so the cap is a no-op on precisely this case.

**Fix — deduplicate by domain inside the lane:** at most one result per domain. With ceiling 2 that
yields up to two distinct independent voices, which is the point of the lane. Without it the lane's
worth collapses to whoever writes most often about the topic.

---

## 4. 🟠 It is not a "challenge lane", and must not be called one

Site-targeting is **direction-neutral**. It fetches independent publishers regardless of whether
they agree. Benigno's CPI reports are not rebuttals; they are independent reports that happen to be
off-period. Drezner and Krugman are critical of Trump because that topic attracts critics, not
because the query asked for criticism.

This matters for two reasons.

**(a) Naming.** Every expensive failure in this codebase traces to a name that promised what the
code did not do: `retrieve.py` reading an `elements` key nothing wrote for months; a challenge
query that was truncated away on every claim it was built for. Calling a direction-neutral
retrieval lane a "challenge lane" would plant the next one. It is an **independent-source lane**.

**(b) It changes a signed decision.** On 2026-08-17 the founder confirmed Phase D *knowing* it
reverses signed D1 Option A: a **challenge lane for ALL claims, universal**. Direction-neutral
independent-source retrieval is a different feature, not a refinement of that one. It needs
explicit re-decision, not a build note.

---

## 5. The argument FOR, which is stronger than it first looks

**Direction-neutrality is better aligned with invariant #7, not worse.**

Invariant #7 forbids sycophancy *and* false balance. A lane that seeks only disagreement
manufactures two-sidedness by construction — it is a false-balancing mechanism wearing a
non-sycophancy label, and the July design's own hedge ("mapping stays free to find nothing") is an
admission that the retrieval step is not neutral.

An independent-source lane presupposes no direction. It corrects a measurable **retrieval bias**
(small publishers systematically outranked) without deciding in advance what should be found. That
is the same species of fix as the class augmenter, which corrects the opposite bias by targeting
authoritative news and officials. The two together are a mirror pair, and neither takes a side.

This is the strongest reason to prefer the swap, and it is a better reason than the yield numbers.

---

## 6. Remaining weaknesses, stated plainly

| # | Weakness | Severity |
|---|---|---|
| 1 | **Untested on the motivating claims.** Scotland (Macfarlane) and dairy (Gid M-K) claim texts were not available; evidence comes from four substitute claims. This is the weakest link in the whole argument. | **High** — test before committing |
| 2 | **Platform-only coverage.** The site list catches `substack.com`, `medium.com`, `wordpress.com`, `blogspot.com`, `ghost.io`. A self-hosted expert on a personal or `.org` domain is missed entirely — and Macfarlane may well be self-hosted. | Medium |
| 3 | **Predictable tier-mix cost.** The lane reliably adds commentary, so `factual_weight_share` will fall — a bench metric with a 0.15 floor that already fails on several claims. Expect it; do not be surprised by it. | Medium, accepted |
| 4 | **Topical noise.** The wildfire probe returned an unrelated WordPress post about AI. Ceiling 2 bounds the damage to two junk items. | Low |
| 5 | **Bench cannot verify it.** Two identical flag-off runs of `TRU-018F-44AA` differed by 25 of 40 URLs. A 2-slot change is invisible in 62% churn. Verification must be direct (issue the query, inspect results), not whole-pool. | Structural — applies to any version of this feature |

---

## 7. What survives from the Phase D build

Everything except the query string. The infrastructure was built against the right hazards and is
needed *more* by this version, not less, because commentary is easier to over-count than junk:

- reserved slot at index 2 (not appended — it loses the truncation race)
- counter-frame never claims the F1-D3 hedge slot
- subordinated depth (5) and fetch weight (1)
- hard ceiling — **now 2, not 3** (§2)
- `query_is_challenge` array + `_challenge_hit` accumulating tag + yield log
- `PipelineConfig.enable_challenge_queries` + `no_challenge_queries` tier receipt
- 37 tests, 6/6 mutations caught

Rename the identifiers to `independent`/`independent_source` in the same commit (§4a).

---

## 8. Verdict and the single decision

**The swap is correct in mechanism and wrong as currently specified.** Adopt it only with:

- **A. Ceiling 2, not 3** — arithmetic guarantee that the lane can never alone satisfy the factual
  support floor (§2). Non-negotiable; without it the feature is a sycophancy mechanism.
- **B. One result per domain** within the lane (§3).
- **C. Renamed** to independent-source throughout (§4a).
- **D. Tested on Scotland and dairy first** — the two claims that motivated the whole phase (§6.1).
  Founder to supply the claim texts; the test is two searches and costs pence.

**Decision required (one):** Phase D was signed off on 2026-08-17 as a *universal challenge lane*.
Replacing it with a *direction-neutral independent-source lane* is a different feature. Does the
founder accept the swap?

If no: the counter-frame is deleted and nothing replaces it, per the standing rule that code below
operational value is fixed or removed — never shipped disabled.

---

## 9. 🔴 AMENDMENT D EXECUTED — THE PROPOSAL FAILS ITS OWN TEST (2026-08-20)

§6.1 named the untested motivating claims as the weakest link in the argument. They were recovered
from `audit/2026-06-18_outreach_contact_map.md` and tested. **The proposal fails on all three.**

Known rebuttal targets:

- **Scotland** — `futureeconomy.scot/posts/589-a-response-to-dan-neidle-...` (Laurie Macfarlane,
  rebutting Dan Neidle's "Scotland's 48p top rate lost £22m")
- **Dairy** — `gidmk.substack.com/p/full-fat-dairy-and-heart-health` (Gideon Meyerowitz-Katz)
- **Wildfire** — `carbonbrief.org/factcheck-no-europe-is-not-having-its-quietest-year-for-wildfires`

| Case | Plain query | Platform-targeted (the proposal) |
|---|---|---|
| Scotland | ❌ | ❌ — returned Celtic FC financial analysis, a funding roundup, Peter Kellner on elections |
| Dairy | ❌ | ❌ — unrelated nutrition Substacks |
| Wildfire | ✅ **rank 1** | ❌ |

**0 of 3.** Two results deserve emphasis:

1. **Restricting to Substack did not surface the Substack rebuttal.** The dairy target *is* on
   `gidmk.substack.com`, and the platform-restricted query still missed it — his post is framed
   around "heart health" while the claim is about weight gain. Narrowing the index does not help
   when the framing differs.
2. **Wildfire is found by the PLAIN query at rank 1.** This confirms the design review's own aside
   that wildfire "escaped only because Carbon Brief indexes well". Where a rebuttal is published by
   a well-indexed outlet we already find it with no new machinery at all.

### A fourth mechanism, tested on the spot: claimant-anchored

The Scotland URL contains its own hint — `a-response-to-dan-neidle`. Phase C shipped a `claimant`
field, so a counter-frame could anchor on the person rather than the topic. Tested:

    "response to Dan Neidle Scotland 48p tax"
      -> rank 1: linkedin.com/posts/laurie-macfarlane-...a-response-to-dan-neidle-tax-d...

**It finds the rebuttal at rank 1** — but at a LinkedIn URL, and `linkedin.com` is on the runtime
blocklist, so the pipeline would discard it. The canonical `futureeconomy.scot` post never ranks.
On dairy (no person claimant, `subjects: []`) the approach has nothing to anchor on and returned
nothing relevant.

### What this establishes

Three query-side mechanisms — counter-frame wording, independent-platform targeting,
claimant-anchoring — **none reliably retrieves a known rebuttal.** The failures share a cause that
no query wording can reach: rebuttals are published days later, on low-authority or self-hosted
domains, framed differently from the claim, and are sometimes reachable only via a blocked social
platform.

**This is a discovery problem, not a phrasing problem.** Generic web search ranks by authority and
topical match; a rebuttal is by construction lower-authority than what it rebuts and is phrased in
its author's terms, not the claimant's.

### Verdict

**Delete the counter-frame lane.** It does not work, and the standing rule is that code below
operational value is fixed or removed — never shipped disabled. Two fix attempts have been made and
measured; a third guess is not warranted without a different class of mechanism.

### What a future attempt should start from (do not re-derive this)

- **Claimant-anchoring is the only thread that reached rank 1.** The blocker is domain policy, not
  retrieval. Resolving a blocked social post to the canonical article it links to would convert a
  rank-1 hit into a usable source. That is a link-resolution build, not a query build.
- **Well-indexed rebuttals need nothing** — the plain query already finds them (wildfire).
- **A claim with no person claimant (dairy) has no anchor at all** and is out of reach of every
  mechanism tested. Do not promise it.
- **Do not use topic-level evaluative words** ("criticism", "limitations"): they retrieve critiques
  of the subject, measured 2026-08-20 on `TRU-C1A0-0005`.
- **Do not verify any of this on the replay bench.** Two identical flag-off runs of
  `TRU-018F-44AA` differed by 25 of 40 URLs; a 2–3 slot change is invisible in that churn. Verify
  by issuing the query and reading the results, which costs pence and answers directly.
