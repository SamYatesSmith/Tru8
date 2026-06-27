---
name: phased-build-loop
description: >-
  Execute a multi-phase plan one phase at a time under a gated review loop, so
  the user never has to take the assistant's word that work was done correctly.
  Use when delivering any ordered build/change plan (e.g. a repositioning or
  refactor broken into phases), or when the user asks for "design review",
  "checks and loops", "assurances", "verify you actually did it", or "do it
  phase by phase with sign-off". Each phase runs: design → user approval →
  build → INDEPENDENT verification with evidence → fix-loop → user sign-off,
  before the next phase starts. The verifier must not be the same pass that did
  the build. Evidence (diffs, test/build output, screenshots), never assertion.
---

# Phased Build Loop

Deliver an ordered plan **one phase at a time**, with verification built in so
correctness is *demonstrated*, not claimed. Never start the next phase until the
current one is signed off. Never self-certify — an independent check confirms it.

## The loop (run for every phase)

1. **Design (no code).** Write a one-page design for the phase:
   - exact changes + the specific files touched
   - **acceptance criteria** — testable, fixed *now*, before any code, so "did it
     do what was asked" is objectively checkable later
   - risks + what's reversible
   - Present it. **Stop. Get explicit user approval before writing code.**
2. **Build.** Implement *only* what the approved design says. No scope creep; if
   something else needs doing, note it for a later phase.
3. **Independent verify.** A check that did **not** do the build confirms the diff
   against the acceptance criteria, with evidence:
   - run the build/typecheck and tests; capture output
   - for UI, invoke `verify-ui`; for spec/quality/drift, `verify-implementation`;
     for a bug-hunt of the diff, `code-review`; or spawn a fresh reviewer subagent
     that reads the design + diff and reports pass/fail per criterion
   - the verifier reports **PASS/FAIL per acceptance criterion** with the evidence
     that proves each
4. **Fix-loop.** Any FAIL → fix → re-verify. Repeat until every criterion passes.
   Do not present as done while any criterion is unmet.
5. **Sign-off.** Show the user the evidence: diff summary, build/test output, and
   screenshots for UI. **Stop. Get explicit user sign-off before the next phase.**

## Rules

- **One phase at a time.** No look-ahead building.
- **Acceptance criteria are frozen at design time.** Don't redefine "done" after
  building to match what you built.
- **The verifier is independent of the builder.** Same conversation is fine, but
  the verification step must re-derive pass/fail from the criteria + evidence, not
  inherit the builder's claims.
- **Evidence or it didn't happen.** No "should work" / "this compiles" without the
  captured output. If a check wasn't run, say so plainly.
- **Surface drift honestly.** If the build diverged from the approved design, say
  so and either justify or fix — don't paper over it.

## Tracking

Use TaskCreate/TaskUpdate to hold the phase list; mark a phase `completed` only
after user sign-off (step 5), not after the build (step 2).
