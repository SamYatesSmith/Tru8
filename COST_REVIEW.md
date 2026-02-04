# Claude Code — Investigate Fly.io costs for Tru8 (Jan 8–Feb 1, 2026)

You are my senior infra/devops engineer. I deployed Tru8 to Fly.io (region lhr) and my invoice preview shows notable charges for:
- Machines Shared CPU 1x / 2x
- Machines Performance CPU 2x (largest cost)
- Additional RAM for those machines
- Upstash Redis add-on (trueight-redis)
- Volumes + Volume Snapshot Storage
- Bandwidth lines are $0

## Goal
Identify exactly *which programming/runtime/deployment choices* in this codebase and Fly config are causing:
1) Performance CPU 2x usage
2) Extra RAM allocation
3) Redis usage
4) Volume + snapshots usage
…and propose code/config changes to reduce cost without breaking production.

## Hard requirements
- Do NOT guess. Prove findings using repo evidence: config files, logs, metrics, Fly status outputs, and app behavior.
- Output must be short, actionable, and specific (file paths, settings, commands, exact values).
- Prioritise: biggest savings first.

---

## Step A — Inventory what is deployed
1. Locate Fly config and deployment details:
   - `fly.toml` (and any per-env variants)
   - Dockerfile / build pipeline
   - any scripts under `scripts/`, `ops/`, `.github/`, etc.

2. Determine apps + machines actually running:
   - Run:
     - `fly apps list`
     - `fly status -a <APPNAME>`
     - `fly machine list -a <APPNAME>`
     - `fly scale show -a <APPNAME>`
     - `fly regions list -a <APPNAME>`
   - Capture machine sizes, CPU kind (shared/performance), memory, count, and uptime.

3. Pull billing-relevant machine history (if possible):
   - `fly releases -a <APPNAME>`
   - `fly logs -a <APPNAME> --since 30d`
   - Note restarts, OOM kills, deploy loops, crash loops, autoscaling events.

Deliverable: a table of each machine with:
- id, process group, region, cpu kind, cpu size, memory, started_at, restarts, health status

---

## Step B — Explain why “Performance CPU 2x” happened
Investigate all paths that could set performance CPUs:
- `fly.toml` settings: `vm`, `[[services]]`, `processes`, `metrics`, `auto_stop_machines`, `auto_start_machines`
- CLI history in docs/notes (search repo for `fly scale vm`, `performance`, `shared-cpu`, `--vm-cpu-kind`, `--vm-size`)
- CI/CD commands that set VM size or memory

Run:
- `fly config show -a <APPNAME>`
- `fly machine status <MACHINE_ID> -a <APPNAME>` for the expensive machine(s)

Deliverable: pinpoint the exact config/command that set performance 2x (file path + line number OR CLI command), and whether it’s necessary.

---

## Step C — Explain “Additional RAM” lines (why RAM > preset)
Find:
- Any explicit memory settings in `fly.toml` (`[vm] memory`, etc.)
- Any `fly scale memory` usage in scripts/CI
- Evidence of memory pressure:
  - OOM kills in logs
  - large Node heap settings
  - Python workers count too high
  - image processing / PDF parsing / Playwright usage / embeddings, etc.

Actions:
- Inspect runtime memory drivers:
  - Node: check `NODE_OPTIONS`, heap flags, SSR, large in-memory caches
  - Python: gunicorn workers/threads, background jobs, large payloads
  - DB: if running locally in-app

Deliverable:
- Why memory was increased (evidence)
- Recommended new memory per machine (safe lower bound)
- Code/config changes to reduce memory (e.g., streaming, batching, worker limits)

---

## Step D — Investigate Upstash Redis usage (trueight-redis)
Find where Redis is used:
- Search repo for: `redis`, `ioredis`, `upstash`, `REDIS_URL`, `KV_URL`, `cache`, `bull`, `bullmq`, `rq`, `celery`, `session`, `rate limit`
- Identify what features depend on it:
  - caching
  - sessions/auth
  - background queues
  - rate limiting
  - pub/sub

Deliverable:
- Exact modules using Redis (file paths)
- Whether Redis can be removed, downgraded, or replaced (e.g., in-memory cache, SQLite/Postgres table, Fly Postgres, etc.)
- Any misconfig causing excessive Redis calls (loops, cache stampede)

---

## Step E — Investigate Volumes + Snapshot Storage
Identify what volume is attached to:
- `fly volumes list -a <APPNAME>`
- `fly machine list -a <APPNAME>` (volume mounts)
- `fly machine status <MACHINE_ID>` to see mount paths
- Search for filesystem persistence assumptions:
  - uploads folder
  - sqlite db file
  - tmp usage
  - logs written to disk

Determine snapshot drivers:
- frequency, retention, old snapshots
- whether volume is actually required (stateless app?)

Deliverable:
- What data lives on the volume, where in code it’s written, and whether it can move to:
  - object storage (S3/R2)
  - managed Postgres
  - ephemeral storage
- How to reduce snapshot costs (reduce size, remove unused volume, prune snapshots)

---

## Step F — Final output format (must follow)
1) **Biggest cost drivers** (ranked list with $ impact)
2) **Root causes** (each with repo evidence + Fly evidence)
3) **Fix plan** (concrete steps + exact commands + file edits)
4) **Safety checks** (how to confirm no downtime / no data loss)
5) **Cost estimate after fixes** (rough but reasoned)

---

## Notes
- Assume region is `lhr`.
- If multiple Fly apps exist (web, worker, api), include all.
- If anything is missing (app name, org, etc.), infer it from repo or `fly apps list` output first.
