You are Claude Code acting as a Staff+ Software Engineer + Release Manager.

GOAL
I want you to acquire full context of this repository and produce a production-ready release plan to move from “dev/testing” to “production-ready” for a public beta.
This is for a SaaS-style web product. Assume UK-based, but keep output technical and actionable.

OPERATING MODE (IMPORTANT)
- Work in phases. In each phase:
  1) State what you will inspect
  2) Inspect relevant files (read-first, do not change yet)
  3) Summarize findings with exact file paths and any risky patterns
  4) Produce a concrete checklist of fixes
  5) If I say “apply”, implement changes with small, reviewable diffs + tests
- Do NOT hand-wave. If something is unknown, locate it in the codebase or propose the minimal instrumentation to confirm it.
- Prefer minimal changes that significantly increase reliability/safety.
- If there are multiple stacks (backend/frontend), treat them separately then integrate.

CONTEXT ACQUISITION (DO THIS FIRST)
1) Identify:
   - Tech stack (frameworks, runtime versions)
   - Entry points (main server start, worker processes, cron jobs)
   - Critical flows (auth, billing if any, API endpoints, DB writes, external calls)
   - Deployment assumptions (where config lives, env vars expected)
2) Create a map:
   - “System Map” diagram in text: components + data flow
   - “Risk Map”: top 10 release risks ranked by severity/likelihood

RELEASE READINESS AUDIT (REQUIRED AREAS)
Audit and report on each section with: findings + gaps + recommended changes + exact file locations.

A) Build & Reproducibility
- Can the project be built from scratch from README?
- Pin versions (Node/Python/etc), lockfiles, deterministic installs
- Dev vs prod build flags
- Containers? (Dockerfile, compose) if applicable

B) Configuration & Secrets
- Inventory all env vars and secrets
- Confirm secrets never committed
- Add `.env.example` and a “Required Env Vars” table
- Ensure prod-safe defaults (no debug, no permissive CORS, etc)

C) Security Baseline
- Auth/session/JWT/cookies: secure flags, expiry, refresh logic
- Password storage (hashing), rate limits, brute-force protection
- CORS/CSRF
- Input validation + output encoding (XSS)
- Dependency vulnerabilities (recommend tooling)
- Threat model: top 5 likely attacks for this app

D) Data & Privacy (Technical)
- What user data is stored?
- Are logs capturing personal/sensitive info?
- Data retention: propose simple policy + deletion tooling
- Backups and restore path (even minimal)

E) Database & Migrations
- Which DB is used? Are migrations present and reliable?
- Seed/test data strategy
- Connection pooling, timeouts, retries
- Safe schema changes and rollback plan

F) Reliability & Error Handling
- Global error boundaries / exception handlers
- API error standardization
- Timeouts and retries for external APIs
- Background jobs queue safety if used

G) Observability
- Logging: format, levels, correlation IDs
- Metrics: minimal recommended set
- Tracing: optional, but propose if needed
- Health checks: liveness/readiness endpoints
- Sentry (or equivalent) integration plan (optional)

H) Testing Strategy
- Current tests: unit/integration/e2e coverage
- Add “release gate” tests: smoke tests
- Identify the minimum set of tests required before public beta
- Provide commands to run locally and in CI

I) CI/CD Pipeline
- Does CI exist? If not, propose a minimal pipeline:
  - install → lint → test → build → security scan (basic)
- Deployment workflow: staging → production promotion
- Environment separation (dev/staging/prod)

J) Frontend Production Concerns (if applicable)
- Build optimization, source maps, error reporting
- API base URL management
- Caching strategy, CDN considerations
- Accessibility quick pass and performance checks

K) Documentation for Release
- README: install/run/test
- “Ops Runbook”: how to deploy, rollback, common incidents
- “Release Checklist”: one page, tick-box style

OUTPUTS I WANT (STRICT)
1) `PRODUCTION_READINESS_REPORT.md`
   - System Map
   - Risk Map
   - Findings by section A–K
   - “Must Fix Before Public Beta” list (prioritized)
2) `RELEASE_PLAN.md`
   - A numbered task list (small, reviewable tasks)
   - Each task includes: files touched, commands to run, acceptance criteria
3) `ENVIRONMENT_VARIABLES.md`
   - Table of env vars: name, purpose, required, example, where used
4) `RELEASE_CHECKLIST.md`
   - A short checklist suitable for final go/no-go
5) If CI/CD is missing: propose a minimal GitHub Actions workflow OR equivalent for this repo.
   - Do not implement unless I say “apply”.

EXECUTION DETAILS
- Start by scanning the repository structure and key config files.
- Use ripgrep-style searching to locate auth, DB, secrets, external API calls, and logging.
- If there are TODOs/FIXMEs, collect them and rank by release risk.
- Do not modify code yet — first produce the reports.

BEGIN NOW.
First step: print a concise repo tree (top-level + key subfolders) and identify the runtime/framework stack.
Then proceed through phases.
