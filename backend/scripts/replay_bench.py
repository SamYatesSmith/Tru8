"""Replay bench — frozen-corpus regression check.

Runs each corpus claim through the live pipeline, captures structured signals
from the logs, and diffs them against golden.json. Reports unexpected drift
before commit.

Usage:
    python scripts/replay_bench.py --all
    python scripts/replay_bench.py --claim TRU-B4A3-C42D
    python scripts/replay_bench.py --claim TRU-B4A3-C42D --update-golden
    python scripts/replay_bench.py --all --verbose
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# Path setup so app.* imports resolve when run from anywhere
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import asyncio  # noqa: E402

from scripts.replay_bench.comparator import Diff, compare  # noqa: E402
from scripts.replay_bench.fixtures import DomainStatusFixture  # noqa: E402
from scripts.replay_bench.golden_io import (  # noqa: E402
    derive_default_golden,
    load_golden,
    write_golden,
    write_observation_dump,
)
from scripts.replay_bench.reporter import render_overall  # noqa: E402
from scripts.replay_bench.runner import run_one_async  # noqa: E402


CORPUS_DIR = BACKEND_DIR / "tests" / "replay_corpus"


def discover_claims(corpus_dir: Path) -> List[str]:
    return sorted(
        d.name
        for d in corpus_dir.iterdir()
        if d.is_dir() and not d.name.startswith("_") and (d / "input.json").exists()
    )


def current_git_sha() -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(BACKEND_DIR.parent),
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except Exception:
        return "unknown"


async def run_bench(
    claims: List[str], update_golden: bool, verbose: bool
) -> Tuple[str, int]:
    per_claim_diffs: List[Tuple[str, List[Diff]]] = []
    git_sha = current_git_sha()

    with DomainStatusFixture() as fixture:
        for claim_id in claims:
            print(
                f"\n... running {claim_id} (this exercises live LLM + Serper) ...",
                flush=True,
            )
            try:
                obs = await run_one_async(CORPUS_DIR, claim_id, fixture)
            except Exception as e:
                print(f"  [FATAL] {claim_id}: {type(e).__name__}: {e}", flush=True)
                per_claim_diffs.append(
                    (
                        claim_id,
                        [
                            Diff(
                                level="failure",
                                signal="bench_run",
                                expected="completed",
                                observed=f"{type(e).__name__}: {e}",
                                message="bench run threw — investigate before relying on diff",
                            )
                        ],
                    )
                )
                continue

            obs_dict = obs.to_dict()
            write_observation_dump(CORPUS_DIR, claim_id, obs_dict)

            if update_golden:
                golden = derive_default_golden(claim_id, obs_dict, git_sha)
                path = write_golden(CORPUS_DIR, claim_id, golden)
                print(f"  golden written: {path}", flush=True)
                per_claim_diffs.append((claim_id, []))
                continue

            golden = load_golden(CORPUS_DIR, claim_id)
            if golden is None:
                per_claim_diffs.append(
                    (
                        claim_id,
                        [
                            Diff(
                                level="warning",
                                signal="golden_missing",
                                expected="golden.json present",
                                observed="absent",
                                message=(
                                    "no golden — run with --update-golden first to capture one"
                                ),
                            )
                        ],
                    )
                )
                continue

            diffs = compare(obs_dict, golden)
            per_claim_diffs.append((claim_id, diffs))

            if verbose:
                print(f"\n  observation for {claim_id}:")
                print(json.dumps(obs_dict, indent=2, default=str))

    return render_overall(per_claim_diffs)


def main() -> int:
    parser = argparse.ArgumentParser(description="Replay bench for the Tru8 pipeline")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--all", action="store_true", help="Run every corpus claim")
    g.add_argument(
        "--claim",
        type=str,
        help="Run a single claim by ID, e.g. TRU-B4A3-C42D",
    )
    parser.add_argument(
        "--update-golden",
        action="store_true",
        help="Capture/replace golden.json from this run (no comparison)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print full observation alongside the diff report",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="(reserved) skip retrieve, replay from cached pool — not yet implemented",
    )
    args = parser.parse_args()

    if args.fast:
        print("[BENCH] --fast not yet implemented; running full mode.", flush=True)

    if args.all:
        claims = discover_claims(CORPUS_DIR)
        if not claims:
            print(f"[BENCH] no claims found in {CORPUS_DIR}", file=sys.stderr)
            return 2
    else:
        claims = [args.claim]

    text, exit_code = asyncio.run(run_bench(claims, args.update_golden, args.verbose))
    print(text, flush=True)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
