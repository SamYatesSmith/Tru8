#!/usr/bin/env python3
"""
Golden dataset runner — runs fixture checks against the Tru8 API.

Usage:
    python run_golden_dataset.py --tag baseline-v1
    python run_golden_dataset.py --tag after-PR-1A --api-url http://localhost:8000
    python run_golden_dataset.py --tag after-PR-1A --freeze-from runs/20260206T120000_baseline-v1

Requires:
    - Backend running with DEBUG_EVIDENCE_LEDGER=1
    - Valid Clerk JWT token (set TRU8_TOKEN env var or --token flag)
    - pip install requests  (standard library otherwise)
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).parent
FIXTURES_PATH = SCRIPT_DIR / "fixtures.json"
RUNS_DIR = SCRIPT_DIR / "runs"
LEDGER_DIR = SCRIPT_DIR.parent / "data" / "ledger"


def refresh_clerk_jwt(clerk_secret_key, session_id):
    """Get a fresh JWT from Clerk Backend API. Tokens expire in ~60s."""
    resp = requests.post(
        f"https://api.clerk.com/v1/sessions/{session_id}/tokens",
        headers={"Authorization": f"Bearer {clerk_secret_key}", "Content-Type": "application/json"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["jwt"]


def capture_fingerprint():
    """Capture run environment fingerprint for reproducibility."""
    # Git commit hash
    try:
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        git_dirty = bool(subprocess.check_output(
            ["git", "status", "--porcelain"], text=True, stderr=subprocess.DEVNULL
        ).strip())
    except Exception:
        git_hash = "unknown"
        git_dirty = False

    # Collect ENABLE_* flags, thresholds, models from environment
    flags = {}
    thresholds = {}
    models = {}
    for key, val in sorted(os.environ.items()):
        if key.startswith("ENABLE_"):
            flags[key] = val
        elif any(t in key for t in ["THRESHOLD", "MINIMUM", "_CAP", "_RATIO"]):
            if not key.startswith("_"):  # Skip system vars
                thresholds[key] = val
        elif any(t in key for t in ["_MODEL", "_PROVIDER"]) and "COM" not in key:
            models[key] = val

    # LLM params
    llm_params = {}
    for key in ["JUDGE_TEMPERATURE", "JUDGE_MAX_TOKENS", "LLM_RELEVANCE_MIN_SCORE",
                "LLM_RELEVANCE_MAX_EVIDENCE", "EVIDENCE_SNIPPET_LENGTH",
                "PRIMARY_LLM_PROVIDER", "GOOGLE_LLM_MODEL"]:
        val = os.environ.get(key)
        if val is not None:
            llm_params[key] = val

    return {
        "git_commit": git_hash,
        "git_dirty": git_dirty,
        "flags": flags,
        "thresholds": thresholds,
        "models": models,
        "llm_params": llm_params,
    }


def parse_sse_stream(response):
    """Parse SSE stream, return (check_id, events list, final_status)."""
    check_id = response.headers.get("X-Check-Id", "")
    events = []
    final_status = "unknown"

    for raw_line in response.iter_lines(decode_unicode=True):
        if not raw_line or not raw_line.startswith("data: "):
            continue
        try:
            data = json.loads(raw_line[6:])
        except json.JSONDecodeError:
            continue

        events.append(data)
        evt_type = data.get("type", "")

        if not check_id and data.get("checkId"):
            check_id = data["checkId"]

        if evt_type == "completed":
            final_status = "completed"
        elif evt_type == "error":
            final_status = "error"

    return check_id, events, final_status


def _normalize_claim_text(text):
    """Normalize claim text for comparison (lowercase, strip whitespace)."""
    return " ".join(text.lower().split()) if text else ""


def run_fixture(fixture, api_url, token, fingerprint, frozen_claim_data=None):
    """Run a single fixture check and return the artifact dict.

    Args:
        frozen_claim_data: Optional dict of claim position -> {"claim_text": ..., "evidence": [...]}
            from a previous run's _freeze.json. When provided, sends frozen_urls to the API.
    """
    slug = fixture["slug"]
    tag = fixture.get("tag", "untagged")
    print(f"  [{slug}] ({tag}) Submitting...", end="", flush=True)

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"input_type": fixture["input_type"], "content": fixture.get("content"), "url": fixture.get("url")}

    # Frozen replay: send frozen_evidence (v2) or frozen_urls (v1) to API
    if frozen_claim_data:
        import hashlib

        has_extracted = any(
            claim_info.get("extracted_evidence")
            for claim_info in frozen_claim_data.values()
        )

        if has_extracted:
            # V2: frozen_evidence (zero network)
            frozen_evidence = {}
            frozen_claim_texts = {}
            for pos, claim_info in frozen_claim_data.items():
                claim_key = claim_info.get("claim_key", pos)
                extracted = claim_info.get("extracted_evidence", [])
                frozen_evidence[claim_key] = extracted
                # Also key by position as fallback
                frozen_evidence[pos] = extracted
                claim_text = claim_info.get("claim_text", "")
                if claim_text:
                    frozen_claim_texts[claim_key] = claim_text
                    frozen_claim_texts[pos] = claim_text
            body["frozen_evidence"] = frozen_evidence
            if frozen_claim_texts:
                body["frozen_claim_texts"] = frozen_claim_texts
            print(f" [FROZEN-V2: {len(frozen_claim_data)} claims]", end="", flush=True)
        else:
            # V1 fallback: frozen_urls
            frozen_urls = {}
            frozen_claim_texts = {}
            for pos, claim_info in frozen_claim_data.items():
                evidence_list = claim_info.get("evidence", [])
                frozen_urls[pos] = evidence_list  # Include empty lists (0 frozen evidence)
                claim_text = claim_info.get("claim_text", "")
                if claim_text:
                    frozen_claim_texts[pos] = claim_text
            if frozen_urls:
                body["frozen_urls"] = frozen_urls
                if frozen_claim_texts:
                    body["frozen_claim_texts"] = frozen_claim_texts
                print(f" [FROZEN-V1: {len(frozen_urls)} claims]", end="", flush=True)

    t0 = time.time()
    resp = requests.post(f"{api_url}/api/v1/checks/stream", json=body, headers=headers, stream=True, timeout=300)

    if resp.status_code != 200:
        print(f" FAILED (HTTP {resp.status_code})")
        return {"slug": slug, "tag": tag, "error": f"HTTP {resp.status_code}: {resp.text[:200]}", "fingerprint": fingerprint}

    check_id, events, status = parse_sse_stream(resp)
    elapsed = time.time() - t0
    print(f" {status} in {elapsed:.1f}s (check={check_id[:8]}...)", flush=True)

    if status != "completed":
        return {"slug": slug, "tag": tag, "check_id": check_id, "status": status, "elapsed_s": elapsed, "events": events, "fingerprint": fingerprint}

    # Fetch full check result from API
    print(f"  [{slug}] Fetching result...", end="", flush=True)
    detail_resp = requests.get(f"{api_url}/api/v1/checks/{check_id}", headers=headers, timeout=30)
    check_data = detail_resp.json() if detail_resp.status_code == 200 else {}

    # Read ledger file if it exists
    ledger_path = LEDGER_DIR / f"{check_id}.json"
    ledger_data = {}
    if ledger_path.exists():
        with open(ledger_path) as f:
            ledger_data = json.load(f)
        print(f" + ledger", flush=True)
    else:
        print(f" (no ledger — set DEBUG_EVIDENCE_LEDGER=1)", flush=True)

    # Build artifact
    claims = check_data.get("claims", [])
    return {
        "slug": slug,
        "tag": tag,
        "check_id": check_id,
        "status": status,
        "elapsed_s": round(elapsed, 2),
        "verdicts": {str(c.get("position", i)): c.get("verdict") for i, c in enumerate(claims)},
        "confidences": {str(c.get("position", i)): c.get("confidence") for i, c in enumerate(claims)},
        "evidence_urls": {
            str(c.get("position", i)): [e.get("url", "") for e in c.get("evidence", [])]
            for i, c in enumerate(claims)
        },
        "evidence_counts": {str(c.get("position", i)): len(c.get("evidence", [])) for i, c in enumerate(claims)},
        "judge_input_hashes": {
            str(c.get("position", i)): c.get("judge_input_hash", "")
            for i, c in enumerate(claims)
        },
        "total_claims": len(claims),
        "credibility_score": check_data.get("credibilityScore"),
        "evidence_ledger": ledger_data,
        "fingerprint": fingerprint,
        "_check_data": check_data,  # Full response for freeze data extraction
    }


def save_freeze_data(run_dir, results):
    """Save evidence URLs, metadata, verdicts, and claim texts for frozen replay.

    v2 format includes extracted_evidence (full pre-weighting dicts) from the ledger,
    enabling zero-network frozen evidence replay. Falls back to v1 format (URLs only)
    when ledger data is unavailable.

    Format:
    {
      "slug": {
        "claims": {
          "0": {
            "claim_text": "...",
            "claim_key": "<sha1>",
            "evidence": [{"url": "...", "title": "...", "snippet": "..."}, ...],
            "extracted_evidence": [<full pre-weighting dicts>]
          }
        },
        "verdicts": {"0": "supported"},
        "claim_count": 2
      }
    }
    """
    import hashlib

    freeze = {}
    for artifact in results:
        if artifact.get("status") != "completed":
            continue
        slug = artifact["slug"]
        claims_data = {}
        check_data = artifact.get("_check_data", {})
        api_claims = check_data.get("claims", [])
        ledger_data = artifact.get("evidence_ledger", {})
        # Prefer judge_input_evidence (post-filtering, what judge actually saw)
        # over pre_weighting_evidence (pre-filtering) for deterministic V2 replay
        judge_input_ev = ledger_data.get("stages", {}).get(
            "judge_input_evidence", {}
        ).get("evidence", {})
        pre_weighting = judge_input_ev or ledger_data.get("stages", {}).get(
            "pre_weighting_evidence", {}
        ).get("evidence", {})

        for pos, urls in artifact.get("evidence_urls", {}).items():
            # Get claim text from API response
            claim_text = ""
            evidence_meta = []
            pos_int = int(pos)
            if pos_int < len(api_claims):
                claim_obj = api_claims[pos_int]
                claim_text = claim_obj.get("text", "")
                # Build per-URL metadata from evidence objects
                for ev in claim_obj.get("evidence", []):
                    ev_url = ev.get("url", "")
                    if ev_url:
                        evidence_meta.append({
                            "url": ev_url,
                            "title": ev.get("title", ""),
                            "snippet": ev.get("snippet", ev.get("text", ""))[:300],
                        })

            # Fallback: if we couldn't get metadata from API, use bare URLs
            if not evidence_meta:
                evidence_meta = [{"url": u, "title": "", "snippet": ""} for u in urls if u]

            # v2: pre-weighting evidence from ledger (full dicts)
            extracted = pre_weighting.get(pos, [])

            # Compute stable claim key
            normalized = " ".join(claim_text.lower().split()) if claim_text else ""
            claim_key = hashlib.sha1(normalized.encode()).hexdigest() if claim_text else pos

            claims_data[pos] = {
                "claim_text": claim_text,
                "claim_key": claim_key,
                "evidence": evidence_meta,                # v1 compat
                "extracted_evidence": extracted,            # v2: full pre-weighting dicts
            }

        has_extracted = any(
            claim_info.get("extracted_evidence")
            for claim_info in claims_data.values()
        )

        # Determine freeze stage: judge_input_evidence (v3) or pre_weighting (v2) or urls-only (v1)
        freeze_stage = None
        freeze_ver = 1
        if has_extracted:
            if judge_input_ev:
                freeze_stage = "judge_input_evidence"
                freeze_ver = 3
            else:
                freeze_stage = "pre_weighting_evidence"
                freeze_ver = 2

        freeze[slug] = {
            "claims": claims_data,
            "verdicts": artifact.get("verdicts", {}),
            "claim_count": artifact.get("total_claims", 0),
            # Keep flat evidence_urls for backward compat with compare_runs.py
            "evidence_urls": artifact.get("evidence_urls", {}),
            "freeze_version": freeze_ver,
            "freeze_stage": freeze_stage,
        }

    path = run_dir / "_freeze.json"
    with open(path, "w") as f:
        json.dump(freeze, f, indent=2)
    return path


def load_freeze_data(freeze_from_dir):
    """Load freeze data from a previous run."""
    freeze_path = Path(freeze_from_dir) / "_freeze.json"
    if not freeze_path.exists():
        print(f"WARNING: No _freeze.json in {freeze_from_dir}. Run without --freeze-from first.", file=sys.stderr)
        return {}
    with open(freeze_path) as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Run golden dataset against Tru8 API")
    parser.add_argument("--tag", required=True, help="Run tag (e.g. baseline-v1, after-PR-1A)")
    parser.add_argument("--api-url", default="http://localhost:8000", help="Backend API URL")
    parser.add_argument("--token", default=os.environ.get("TRU8_TOKEN", ""), help="Clerk JWT token")
    parser.add_argument("--clerk-session", default=os.environ.get("CLERK_SESSION_ID", ""), help="Clerk session ID for auto-refresh (tokens expire ~60s)")
    parser.add_argument("--clerk-secret", default=os.environ.get("CLERK_SECRET_KEY", ""), help="Clerk secret key for token refresh")
    parser.add_argument("--fixtures", default=str(FIXTURES_PATH), help="Path to fixtures JSON")
    parser.add_argument("--freeze-from", default=None, help="Path to previous run dir for freshness freeze comparison")
    args = parser.parse_args()

    # Token refresh setup
    auto_refresh = bool(args.clerk_session and args.clerk_secret)
    if auto_refresh:
        args.token = refresh_clerk_jwt(args.clerk_secret, args.clerk_session)
        print(f"Auth: auto-refresh via Clerk session {args.clerk_session[:16]}...")
    elif not args.token:
        print("ERROR: No auth token. Set TRU8_TOKEN or use --clerk-session + --clerk-secret.", file=sys.stderr)
        sys.exit(1)

    with open(args.fixtures) as f:
        fixtures = json.load(f)

    fingerprint = capture_fingerprint()
    freeze_data = load_freeze_data(args.freeze_from) if args.freeze_from else {}

    # Auto-enable ledger for baseline captures (needed for pre_weighting_evidence)
    if not args.freeze_from:
        os.environ.setdefault("DEBUG_EVIDENCE_LEDGER", "1")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_dir = RUNS_DIR / f"{ts}_{args.tag}"
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"Running {len(fixtures)} fixtures with tag '{args.tag}'")
    print(f"Git: {fingerprint['git_commit'][:10]}{'*' if fingerprint['git_dirty'] else ''}")
    if freeze_data:
        print(f"Freeze baseline: {args.freeze_from} ({len(freeze_data)} slugs)")
    print(f"Output: {run_dir}\n")

    results = []
    for fixture in fixtures:
        # Refresh JWT before each fixture (Clerk tokens expire in ~60s)
        if auto_refresh:
            try:
                args.token = refresh_clerk_jwt(args.clerk_secret, args.clerk_session)
            except Exception as e:
                print(f"  WARNING: Token refresh failed: {e}", flush=True)

        slug = fixture["slug"]

        # Build frozen claim data for this fixture (if --freeze-from provided)
        frozen_claim_data = None
        if freeze_data and slug in freeze_data:
            frozen_claim_data = freeze_data[slug].get("claims", {})
            # Fallback for old freeze format (flat evidence_urls without claim text)
            if not frozen_claim_data and "evidence_urls" in freeze_data[slug]:
                frozen_claim_data = {
                    pos: {"claim_text": "", "evidence": [{"url": u, "title": "", "snippet": ""} for u in urls]}
                    for pos, urls in freeze_data[slug]["evidence_urls"].items()
                }

        artifact = run_fixture(fixture, args.api_url, args.token, fingerprint, frozen_claim_data=frozen_claim_data)

        # Attach frozen baseline for comparison
        if freeze_data and slug in freeze_data:
            artifact["frozen_baseline"] = freeze_data[slug]

        # Save per-check artifact (exclude _check_data to keep files small)
        save_artifact = {k: v for k, v in artifact.items() if k != "_check_data"}
        out_path = run_dir / f"{slug}.json"
        with open(out_path, "w") as f:
            json.dump(save_artifact, f, indent=2, default=str)
        results.append(artifact)

    # Save freeze data for future runs
    freeze_path = save_freeze_data(run_dir, results)

    # Tag counts
    tag_counts = {}
    for f_item in fixtures:
        t = f_item.get("tag", "untagged")
        tag_counts[t] = tag_counts.get(t, 0) + 1

    # Save run summary
    summary = {
        "tag": args.tag,
        "timestamp": ts,
        "fixture_count": len(fixtures),
        "fixture_tags": tag_counts,
        "completed": sum(1 for r in results if r.get("status") == "completed"),
        "failed": sum(1 for r in results if r.get("status") != "completed"),
        "fingerprint": fingerprint,
        "freeze_from": str(args.freeze_from) if args.freeze_from else None,
        "freeze_version": max(
            (slug_data.get("freeze_version", 0) for slug_data in freeze_data.values()),
            default=0
        ) if freeze_data else None,
        "freeze_stage": next(
            (slug_data.get("freeze_stage") for slug_data in freeze_data.values()
             if slug_data.get("freeze_stage")),
            None
        ) if freeze_data else None,
    }
    with open(run_dir / "_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nDone: {summary['completed']}/{summary['fixture_count']} completed")
    print(f"Tags: {tag_counts}")
    print(f"Freeze data: {freeze_path}")
    print(f"Artifacts: {run_dir}")


if __name__ == "__main__":
    main()
