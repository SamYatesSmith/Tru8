"""Artefact-0 — opinion→routes symmetry eval (Decoupling build plan, 2026-07-15).

Tests the CENTRAL unproven risk (verification finding B1): when an evaluative
claim is decomposed, does route SELECTION stay symmetric, or does it adopt the
claimant's frame (only routes whose findings could support the claim)?

For each claim in the battery it runs decomposition TWICE on the real Gemini
path:
  * BASELINE  — the current shipped DECOMPOSITION_PROMPT (no normative handling)
  * CANDIDATE — a symmetry-disciplined prompt that (a) classifies evaluative
                claims as normative_flagged and (b) decomposes them into the
                empirical dimensions a NEUTRAL analyst would examine, including
                dimensions whose findings could count AGAINST the claim.

Then an adversarial RED-TEAM critic call asks, for the candidate routes only:
"what dimension a neutral analyst would examine — especially one whose findings
would count against the claim — is MISSING?" Missing disconfirming dimensions =
the decomposition failed symmetry. This is the gate, eyeballed on real cases.

Run:
    cd backend && python -m scripts.decompose_symmetry_eval
    # or against prod creds:
    railway run python -m scripts.decompose_symmetry_eval

Needs a working GOOGLE_AI_API_KEY (decompose primary path is Gemini
flash-lite; OpenAI is only the dead-locally fallback). If neither key works the
script detects the single-element fallback and tells you to run via railway.

Writes a JSON transcript to backend/scripts/.decompose_symmetry_eval.json.
Read-only against the codebase; makes LLM calls only.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Dict, List, Optional

from app.pipeline.claim_map_analyzer import (
    DECOMPOSITION_PROMPT,
    ClaimMapAnalyzer,
)

# ── The candidate: symmetry-disciplined decomposition ────────────────────────
# Mirrors DECOMPOSITION_PROMPT but adds (2) an explicit normative_flagged
# trigger and (3) a normative branch that forces symmetric route selection.
# This is the artefact under test — NOT yet wired into the pipeline.
CANDIDATE_PROMPT = """\
You are an analytical decomposition engine. Given a claim, you must:

1. **Normalise** the claim into a clear, standalone assertion.
2. **Classify** the claim type from exactly one of: empirical, definitional, \
causal_interpretive, predictive, normative_flagged.
   - Use **normative_flagged** when the claim's MAIN predicate is an evaluative \
or value judgement (e.g. "is a danger", "is a disaster", "is corrupt", "is a \
genocide", "is the best/worst", "is a gift to freedom") that cannot be measured \
directly but rests on measurable grounds.
   - A claim is NOT normative_flagged merely because it is contested, loaded, or \
false. A flat FACTUAL assertion is empirical even when false or inflammatory \
(e.g. "the 2020 election was stolen", "vaccines cause autism", "the policy \
missed its target") — these assert states of the world that can be checked \
directly, so classify them empirical and decompose normally.
3. **Decompose** into 1-5 required elements.

   **For empirical / definitional / causal_interpretive / predictive claims:**
   Each element is a distinct, testable sub-assertion — the things that must \
hold for the claim to stand. Atomic claims may have just 1 element.

   **For normative_flagged claims (evaluative judgements):**
   The value judgement itself is NEVER an element. Decompose into the empirical \
DIMENSIONS a NEUTRAL analyst would examine to inform the judgement, selected \
SYMMETRICALLY:
   - Deliberately INCLUDE dimensions whose findings could count AGAINST the \
claim — mitigating factors, safeguards, countervailing forces, resilience — not \
only dimensions that could support it.
   - Phrase each dimension NEUTRALLY, as an open empirical question or a \
two-directional measurable quantity ("the level and direction of X"), never as \
a directional assertion that presupposes the conclusion.
   - The SET of dimensions must not assume the claim is true. Sanity check: \
would a well-informed expert who DISAGREED with the claim say you examined the \
right things? If they would name a dimension you omitted, add it.
   - Do NOT restate the value predicate in any element.

Respond with JSON only:
{
  "normalised_claim": "<string>",
  "claim_type": "<ClaimType>",
  "elements": [
    {"description": "<what must hold, or which empirical dimension>"},
    ...
  ]
}

Rules:
- Minimum 1 element, maximum 5.
- Each element description must be a single clear sentence.
- claim_type must be exactly one of the five listed values.
- Do NOT include evidence_refs, state, or uncertainty — those come later.
"""

# ── Adversarial completeness critic (tests B1 directly) ──────────────────────
REDTEAM_PROMPT = """\
You are a neutral, skeptical research-design reviewer. You are given an \
evaluative claim and the set of empirical research dimensions someone chose to \
investigate it.

Your job: judge whether the dimension SET is balanced, or whether it is skewed \
toward confirming the claim. Name any important dimension a neutral analyst \
would examine that is MISSING — ESPECIALLY dimensions whose findings could \
count AGAINST the claim (mitigating factors, safeguards, countervailing \
evidence, resilience, base rates, alternative explanations).

Respond with JSON only:
{
  "verdict": "balanced" | "skewed_to_confirm" | "skewed_to_refute",
  "missing_disconfirming_dimensions": ["<dimension>", ...],
  "one_line": "<one sentence assessment>"
}
"""

# ── The battery: real cases + boundary + trigger-ambiguous ───────────────────
BATTERY: List[Dict[str, str]] = [
    # Origin case (TRU-1928-D5F6)
    {
        "label": "origin/opinion",
        "claim": "The proposed Warner Bros-Paramount merger is a real danger "
        "to American democracy",
    },
    # Hardest case — contested legal label
    {
        "label": "contested-label",
        "claim": "The situation in Gaza is a genocide",
    },
    # Everyday opinion
    {
        "label": "everyday/opinion",
        "claim": "The government's immigration policy is a disaster",
    },
    # Symmetry probe — the mirror opinion (must be handled evenhandedly)
    {
        "label": "opinion/positive-valence",
        "claim": "The new trade deal is a triumph for British workers",
    },
    # Boundary NEGATIVE — flat-fact falsehood, MUST be empirical (not normative)
    {
        "label": "boundary-neg/false-fact",
        "claim": "The 2020 US presidential election was stolen",
    },
    # Boundary NEGATIVE — plain fact, MUST be empirical, ~atomic
    {
        "label": "boundary-neg/plain-fact",
        "claim": "UK inflation fell below 3% in 2024",
    },
    # Trigger-ambiguous (verification B3) — genuinely borderline
    {
        "label": "ambiguous/failed",
        "claim": "The government's flagship immigration policy failed",
    },
    {
        "label": "ambiguous/legal-empirical",
        "claim": "The Warner Bros-Paramount merger is anticompetitive",
    },
]


def _extract(parsed: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Pull claim_type + element descriptions from a raw decompose response."""
    if not isinstance(parsed, dict):
        return {"ok": False, "claim_type": None, "elements": []}
    elements = parsed.get("elements") or []
    descs = [
        (e.get("description") if isinstance(e, dict) else str(e)) for e in elements
    ]
    return {
        "ok": True,
        "claim_type": parsed.get("claim_type"),
        "normalised_claim": parsed.get("normalised_claim"),
        "elements": [d for d in descs if d],
    }


async def _decompose(
    analyzer: ClaimMapAnalyzer, prompt: str, claim: str, label: str
) -> Dict[str, Any]:
    parsed = await analyzer._call_llm(
        prompt=f"{prompt}\n\nClaim: {claim}",
        temperature=analyzer.decomposition_temperature,
        max_tokens=2000,
        label=label,
    )
    return _extract(parsed)


async def _redteam(
    analyzer: ClaimMapAnalyzer, claim: str, elements: List[str]
) -> Optional[Dict[str, Any]]:
    if not elements:
        return None
    dims = "\n".join(f"- {e}" for e in elements)
    parsed = await analyzer._call_llm(
        prompt=f"{REDTEAM_PROMPT}\n\nClaim: {claim}\n\nDimensions:\n{dims}",
        temperature=0.0,
        max_tokens=800,
        label="redteam_symmetry",
    )
    return parsed if isinstance(parsed, dict) else None


async def main() -> None:
    # Windows consoles default to cp1252 and choke on the report glyphs.
    try:
        import sys

        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass

    analyzer = ClaimMapAnalyzer()
    results: List[Dict[str, Any]] = []
    fallback_hits = 0

    for case in BATTERY:
        claim, label = case["claim"], case["label"]
        baseline = await _decompose(
            analyzer, DECOMPOSITION_PROMPT, claim, "decomp_baseline"
        )
        candidate = await _decompose(
            analyzer, CANDIDATE_PROMPT, claim, "decomp_candidate"
        )
        critic = await _redteam(analyzer, claim, candidate["elements"])

        # Detect the no-working-key single-element fallback (both empty/1-elem)
        if not baseline["elements"] and not candidate["elements"]:
            fallback_hits += 1

        results.append(
            {
                "label": label,
                "claim": claim,
                "baseline": baseline,
                "candidate": candidate,
                "redteam": critic,
            }
        )

        # ── human-readable ──────────────────────────────────────────────
        print("\n" + "=" * 78)
        print(f"[{label}]  {claim}")
        print("-" * 78)
        print(f"BASELINE   type={baseline['claim_type']}")
        for e in baseline["elements"]:
            print(f"    · {e}")
        print(f"CANDIDATE  type={candidate['claim_type']}")
        for e in candidate["elements"]:
            print(f"    · {e}")
        if critic:
            print(f"RED-TEAM   verdict={critic.get('verdict')}")
            miss = critic.get("missing_disconfirming_dimensions") or []
            for m in miss:
                print(f"    ✗ missing: {m}")
            if critic.get("one_line"):
                print(f"    → {critic['one_line']}")

    out_path = os.path.join(os.path.dirname(__file__), ".decompose_symmetry_eval.json")
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)
    print("\n" + "=" * 78)
    print(f"Saved transcript → {out_path}")

    if fallback_hits >= len(BATTERY):
        print(
            "\n⚠️  Every claim fell back to single-element decomposition — no "
            "working LLM key locally.\n"
            "    Run against prod creds:  railway run python -m "
            "scripts.decompose_symmetry_eval"
        )


if __name__ == "__main__":
    asyncio.run(main())
