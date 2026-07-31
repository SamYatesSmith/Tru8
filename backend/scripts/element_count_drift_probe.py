"""Why did element counts fall on 4 of 8 replay-corpus claims at the F7 re-gold?

The re-gold (`f6fd038`, 2026-07-30) recorded element counts falling on four
corpus claims (3->1, 3->2, 3->2, 4->3) against goldens captured on `fdf3509`.
The register's working diagnosis was model drift. That diagnosis is not safe to
act on, because the shared factual decompose path DID change in between:
`fa35465` / `2b8b8a9` added the causal-link and comparison-baseline element
rules to DECOMPOSITION_PROMPT, and those commits land AFTER `fdf3509`.

This probe re-runs decompose only — no retrieval, no mapping — N times per
claim, on the current code, and prints the count and the element text. It
separates the two hypotheses:

  * model nondeterminism  -> counts vary run to run around the old value
  * systematic shift      -> counts are stable at the new, lower value

It says nothing about whether fewer elements is worse. That is a judgement on
the element TEXT, which is why the text is printed rather than just the count.

Usage:  python -m scripts.element_count_drift_probe [--runs 3]
"""

import argparse
import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer  # noqa: E402

CORPUS = Path(__file__).resolve().parents[1] / "tests" / "replay_corpus"

# value = element count in the golden captured on fdf3509 (2026-07-21)
BASELINE = {
    "TRU-A3E8-3199": 3,
    "TRU-C1A0-0001": 3,
    "TRU-93DD-F4B7": 3,
    "TRU-B4A3-C42D": 4,
    "TRU-C1A0-0003": 3,  # control — held at 3
    "TRU-C1A0-0004": 3,  # control — held at 3
}


def load_claim(claim_id: str) -> str:
    data = json.loads((CORPUS / claim_id / "input.json").read_text(encoding="utf-8"))
    return data["content"]


async def probe(runs: int, source_context: bool = True) -> int:
    analyzer = ClaimMapAnalyzer()
    counts = defaultdict(list)
    texts = {}

    for claim_id, baseline in BASELINE.items():
        claim_text = load_claim(claim_id)
        for run in range(runs):
            # source_context mirrors the runner: for a text submission the
            # content IS the claim, which is what claim integrity (`fa35465`)
            # started passing through. --no-context suppresses it, which is
            # the pre-`fa35465` call shape — the A/B that isolates whether the
            # anchoring is what tightened the decomposition.
            result = await analyzer.decompose_claims_batch(
                [{"text": claim_text, "claim_id": "0"}],
                source_context=claim_text if source_context else None,
            )
            claim_map = result["0"]
            # decompose_claims_batch is annotated -> ClaimMap but returns the
            # dict form the runner stores on claim["claim_map"]; accept either.
            if isinstance(claim_map, dict):
                elements = claim_map.get("elements", [])
                descs = [e.get("description", "") for e in elements]
            else:
                elements = claim_map.elements
                descs = [e.description for e in elements]
            counts[claim_id].append(len(elements))
            if run == 0:
                texts[claim_id] = descs

    print("\n" + "=" * 78)
    print(f"{'claim':18} {'golden':>6} {'runs':>14} {'stable?':>9}")
    print("=" * 78)
    drifting = 0
    for claim_id, baseline in BASELINE.items():
        seen = counts[claim_id]
        stable = len(set(seen)) == 1
        if not stable:
            drifting += 1
        flag = "yes" if stable else "VARIES"
        print(f"{claim_id:18} {baseline:>6} {str(seen):>14} {flag:>9}")

    print(
        "\nElements produced on run 1 (the judgement is on this text, not the count):"
    )
    for claim_id, descs in texts.items():
        delta = len(descs) - BASELINE[claim_id]
        marker = "" if delta == 0 else f"  [{delta:+d} vs golden]"
        print(f"\n  {claim_id} — {len(descs)} element(s){marker}")
        for i, d in enumerate(descs, 1):
            print(f"    {i}. {d}")

    print(f"\n{drifting} of {len(BASELINE)} claims varied across {runs} runs.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument(
        "--no-context",
        action="store_true",
        help="call decompose without source_context (the pre-fa35465 shape)",
    )
    args = parser.parse_args()
    return asyncio.run(probe(args.runs, source_context=not args.no_context))


if __name__ == "__main__":
    raise SystemExit(main())
