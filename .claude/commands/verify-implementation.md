Adversarially verify an implementation before commit — loop over the change to confirm it touches the RIGHT CODE, fixes the RIGHT PROBLEM, and does so the RIGHT WAY (accurate + quality), with EVIDENCE for every claim. Use after writing code for any plan phase, before committing.

Target: $ARGUMENTS (the change/phase to verify; default: the current uncommitted diff — run `git status` + `git diff`).

This is the code counterpart of the knowledge loop (memory `feedback_knowledge_loop.md`) and sits alongside the pipeline pre-commit bench (`feedback_replay_bench.md`). It exists because real defects shipped this project when output was *asserted* instead of *verified* (priced by analogy not code; relayed sub-agent claims unscrubbed; missed client-vs-server and call-count-vs-result-count). 

## The one hard rule
**Every gate needs EVIDENCE — a command actually run (with its output) or a `file:line` citation. No gate passes on assertion. No "safe to commit" without it.** Be adversarial: your job is to find what's wrong, not to confirm it's fine.

## The loop
Run the gates in order. If any gate FAILS, fix the code, then re-run from the failed gate. Repeat until all pass — or a gate is explicitly waived with a written reason. Then emit the verdict.

### G0 — Contract (what is this even fixing?)
Quote, one line each, from a real source (the plan `audit/2026-06-15_verification_repositioning_plan.md`, `audit/OPEN_WORK.md`, or a named issue):
- **Problem** being fixed.
- **Intended behaviour change.**
- **Acceptance criterion** ("done when…").
If you can't quote these from a source, STOP — you're fixing an unspecified problem. Don't invent the spec.

### G1 — Right PROBLEM (root cause, not symptom)
- Trace problem → root cause → fix. State the causal chain.
- **Verify against runtime/code, not stale docs or memory** (memory is point-in-time; it can be wrong). Read the actual code path.
- Adversarial check: *what evidence proves this is the real cause?* (This session: the path returned 503 not 500 when an env var was empty — the "500" in the notes was wrong. Check, don't trust.)
- Confirm the fix removes the cause, and that the symptom can't arise another way.

### G2 — Right CODE (does the change actually run?)
- The changed symbol/file is **on the executed path**: grep its call sites and confirm it's invoked from the entry points that matter.
- **Multi-path coverage:** if the system has several entry points, confirm the change covers ALL relevant ones — or is explicitly scoped out. (This session: `save_check_results_async` is the single save path for dashboard *and* agent *and* x402 — verified by grepping call sites. Don't assume.)
- Walk the **Tru8 trap list** below and tick each that applies.
- Confirm nothing reachable was missed and nothing dead was touched.

### G3 — Right WAY (accuracy + quality)
- **Conventions:** matches surrounding naming, structure, comment density, idioms.
- **Defensive / idempotent:** can't break the happy path (e.g. wrap non-critical work in try/except); pipeline stages and saves stay idempotent.
- **Accuracy of claims in the code:** no unverified numbers/constants asserted as fact — mark UNVERIFIED, separate **ground truth** (raw data captured) from **derived/estimated** views, and make estimates recomputable.
- **Scrub any sub-agent input** that informed the change: confidence-tag claims, strip dismissive/unprovable language, verify load-bearing facts against primary source or code before they enter the code or its comments.
- **Self-consistency:** numbers and claims agree with each other and with prior statements in the same work (this session: "£0.15 too low" then "£199/1,500 = 13.3p" — caught only on re-read).

### G4 — Prove it (run something — don't assert)
- Backend: `python -m py_compile <changed files>`; run the narrowest relevant tests (`/test-pipeline` or `pytest tests/... -q`); functionally smoke pure logic with a representative input AND a degenerate/empty input.
- Web: `npx tsc --noEmit` (exit 0, zero lines = clean); lint the changed files.
- Migrations: confirm `down_revision` = current head and there's a single head.
- Capture the **actual output**. Anything you cannot run, list explicitly as **unverified** with its risk.

### G5 — Independent adversarial pass (non-trivial changes)
For anything beyond a trivial edit, spawn a **fresh reviewer agent that did NOT write the code** (Explore/general-purpose) and ask it to *break* the change: find the missed path, the wrong assumption, the untested branch, the convention drift. Treat its findings as G1–G4 failures and loop.

## Tru8 known traps (tick each that applies)
- **Multi-path:** dashboard (`checks.py`) vs agent (`agent.py`) vs x402 — does the change cover all, or just one?
- **Client vs server components:** `onClick`/hooks require `'use client'`; server-component pages need a client wrapper (e.g. `TrackedLink`).
- **`NEXT_PUBLIC_*`** must be a Docker **build ARG** to bake into the bundle, AND any third-party domain must be in the CSP `connect-src`/`script-src` or it's silently dropped.
- **Stale memory/docs ≠ runtime truth** — verify file/function/flag still exists and behaves as claimed.
- **Count semantics:** call-count vs result-count, pence vs pounds, per-query vs per-record — confirm the unit.
- **Migration head:** `down_revision` = current head; runs via `entrypoint.sh` on deploy.
- **Idempotency:** every pipeline stage and save path must be safely re-runnable.
- **Don't ground in analogy or sub-agent output** where the codebase has the real answer — read the code.

## Verdict (emit at the end)
A short report:
- **Per gate:** PASS / FAIL / WAIVED(reason), each with its evidence (command + result, or `file:line`).
- **Residual unverified items** + the risk of each.
- **One-line recommendation:** safe to commit? (No green light without evidence behind every gate.)
