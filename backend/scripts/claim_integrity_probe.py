"""Claim-integrity probe — measures specification loss through extraction atomisation.

Motivating case: check 27F32CF7 (2026-07-21). User submitted ONE causal compound
sentence ("Compared to the last 50 years, tectonic plate movement is extremely
active currently, causing a large rise in volcanic eruptions and earthquakes").
Extraction split it into 3 sealed claims, dropped the causal connective entirely,
and the fragments lost the 50-year anchor — so decompose invented its own vague
comparison windows ("a recent period vs a preceding period") and retrieval
drifted (1000 AD eruptions, Cretaceous plate motion).

This probe quantifies that loss across 6 compound causal submissions and tests
two candidate remedies BEFORE any build decision:

  COND 1  extraction (current)   — n claims, causal link preserved?, anchor per claim
  COND 2  decompose bare (current) — fragment claims decomposed with no context:
                                     do elements carry the user's anchor?
  COND 3  candidate B            — same fragments + original submission as context:
                                     does anchoring recover?
  COND 4  candidate E            — the INTACT sentence as one claim: element count,
                                     causal element present?, anchor retained?,
                                     claim_type (expect causal_interpretive)

Metrics are mechanical (regex on output text) — no LLM judging LLM.

Usage:
    python -m scripts.claim_integrity_probe

LIVE calls (Gemini extract + decompose; no retrieval/mapping spend).
Results -> scripts/.claim_integrity_probe.json (gitignored dot-file).
Local-only tooling — not part of the shipped product.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Causal-language detector (deliberately broad: verbs + connectives)
CAUSE_RE = re.compile(
    r"\bcaus\w*|\bdriv(?:e|es|en|ing)\b|\bled to\b|\blead(?:s|ing)? to\b"
    r"|\bresult(?:s|ed|ing)? (?:in|from)\b|\bdue to\b|\bbecause\b"
    r"|\bcontribut\w+ to\b|\btrigger\w*|\bresponsible for\b|\battribut\w+ to\b",
    re.IGNORECASE,
)

# Invented-vagueness detector for element wording (the 27F32CF7 signature)
VAGUE_WINDOW_RE = re.compile(
    r"\brecent (?:period|years|times|decades)\b|\bpreceding period\b"
    r"|\bearlier period\b|\bprevious period\b|\bpast period\b|\bover time\b",
    re.IGNORECASE,
)

# Each entry: the intact submission, anchor regexes (temporal/spatial spec the
# user explicitly provided), and a short key.
POOL = [
    {
        "key": "tectonic",
        "text": (
            "Compared to the last 50 years, tectonic plate movement is extremely "
            "active currently, causing a large rise in volcanic eruptions and "
            "earthquakes"
        ),
        "anchors": [r"50\s*years?"],
    },
    {
        "key": "food_prices",
        "text": (
            "Since 2016, UK food prices have risen faster than the EU average, "
            "causing a sharp increase in food bank use across Britain"
        ),
        "anchors": [r"\b2016\b", r"\bUK\b|\bBritain\b|\bBritish\b"],
    },
    {
        "key": "arctic_ice",
        "text": (
            "Over the past decade Arctic sea ice has declined dramatically, "
            "driving a rise in extreme winter weather across Europe"
        ),
        "anchors": [r"decade|\b10\s*years?\b", r"\bEurope\w*\b"],
    },
    {
        "key": "antibiotics",
        "text": (
            "Compared to the 1990s, antibiotic prescribing in England has fallen "
            "sharply, leading to a decline in antimicrobial resistance rates"
        ),
        "anchors": [r"1990s?", r"\bEngland\b"],
    },
    {
        "key": "teen_social",
        "text": (
            "Social media use among teenagers has more than doubled since 2015, "
            "causing a large rise in anxiety and depression diagnoses"
        ),
        "anchors": [r"\b2015\b"],
    },
    {
        "key": "water_sewage",
        "text": (
            "Since privatisation in 1989, investment in England's water "
            "infrastructure has fallen, causing a big rise in sewage discharges "
            "into rivers"
        ),
        "anchors": [r"\b1989\b|privatisation", r"\bEngland\b"],
    },
]


# Over-merge CONTROLS for the E routing rule (recombine_single_thesis):
# these MUST NOT recombine. Mechanical check, no LLM spend.
ROUTING_CONTROLS = [
    {
        "key": "ctrl_two_sentences",
        "text": "UK GDP rose 2% in 2023. Arsenal won the Premier League the same year.",
        "must_recombine": False,
    },
    {
        "key": "ctrl_question",
        "text": "Is sea level rising 3mm per year?",
        "must_recombine": False,
    },
    {
        "key": "ctrl_paragraph",
        "text": (
            "The government announced a new housing policy in March. Critics "
            "said it would not help renters. House prices rose 4% in the "
            "following quarter."
        ),
        "must_recombine": False,
    },
    # And the motivating case MUST recombine:
    {"key": "ctrl_tectonic", "text": POOL[0]["text"], "must_recombine": True},
]


def check_routing_controls() -> list[dict]:
    from app.pipeline.extract import recombine_single_thesis

    dummy_frags = [
        {"text": "frag a", "position": 0, "confidence": 80, "key_entities": []},
        {"text": "frag b", "position": 1, "confidence": 80, "key_entities": []},
    ]
    rows = []
    for c in ROUTING_CONTROLS:
        recombined = recombine_single_thesis(c["text"], dummy_frags) is not None
        rows.append(
            {
                "key": c["key"],
                "expected": c["must_recombine"],
                "recombined": recombined,
                "ok": recombined == c["must_recombine"],
            }
        )
    return rows


def _any_match(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def _anchor_hits(entry: dict, text: str) -> int:
    return sum(1 for p in entry["anchors"] if re.search(p, text, re.IGNORECASE))


async def _extract(text: str) -> list[dict]:
    from app.pipeline.extract import ClaimExtractor

    extractor = ClaimExtractor()
    result = await asyncio.wait_for(
        extractor.extract_claims(text, metadata={"source": "probe"}), timeout=90
    )
    return result.get("claims", []) if result.get("success") else []


async def _decompose(claim_text: str, claim_id: str) -> dict:
    from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

    analyzer = ClaimMapAnalyzer()
    cm = await asyncio.wait_for(
        analyzer.decompose_claim(claim_text, claim_id), timeout=120
    )
    return {
        "claim_type": str(cm.get("claim_type")),
        "normalised_claim": cm.get("normalised_claim"),
        "elements": [e["description"] for e in cm["elements"]],
    }


async def probe_one(i: int, entry: dict) -> dict:
    key = entry["key"]
    text = entry["text"]
    out: dict = {"key": key, "text": text}

    # ── COND 1: current extraction ──────────────────────────────────────
    print(f"[{key}] extracting ...", flush=True)
    claims = await _extract(text)
    claim_rows = []
    for c in claims:
        ctext = c.get("text", "")
        claim_rows.append(
            {
                "text": ctext,
                "causal": bool(CAUSE_RE.search(ctext)),
                "anchor_hits": _anchor_hits(entry, ctext),
            }
        )
    out["cond1_extraction"] = {
        "n_claims": len(claim_rows),
        "causal_preserved": any(r["causal"] for r in claim_rows),
        "claims_with_full_anchor": sum(
            1 for r in claim_rows if r["anchor_hits"] == len(entry["anchors"])
        ),
        "claims": claim_rows,
    }

    # Fragments of interest = extracted claims that LOST at least one anchor.
    # These are the ones current decompose runs blind on. Cap 2 for cost.
    fragments = [
        r["text"] for r in claim_rows if r["anchor_hits"] < len(entry["anchors"])
    ][:2]
    out["fragments_probed"] = fragments

    # ── COND 2 vs COND 3: bare vs context-carried decompose ─────────────
    cond2, cond3 = [], []
    for j, frag in enumerate(fragments):
        print(f"[{key}] decompose bare frag {j} ...", flush=True)
        bare = await _decompose(frag, f"PROBE-{i}-BARE-{j}")
        print(f"[{key}] decompose ctx  frag {j} ...", flush=True)
        ctx_claim = (
            f"{frag}\n(Context — this claim derives from the user's submission: "
            f'"{text}". Keep elements anchored to the submission\'s stated '
            f"timeframe and scope.)"
        )
        ctx = await _decompose(ctx_claim, f"PROBE-{i}-CTX-{j}")
        for cond, dec in ((cond2, bare), (cond3, ctx)):
            elems = dec["elements"]
            cond.append(
                {
                    "fragment": frag,
                    "elements": elems,
                    "any_element_anchored": any(
                        _anchor_hits(entry, e) > 0 for e in elems
                    ),
                    "invented_vague_window": any(
                        VAGUE_WINDOW_RE.search(e) for e in elems
                    ),
                }
            )
    out["cond2_bare"] = cond2
    out["cond3_context"] = cond3

    # ── COND 4: candidate E — intact sentence as ONE claim ──────────────
    print(f"[{key}] decompose intact (E) ...", flush=True)
    e_dec = await _decompose(text, f"PROBE-{i}-INTACT")
    elems = e_dec["elements"]
    out["cond4_intact"] = {
        "claim_type": e_dec["claim_type"],
        "normalised_claim": e_dec["normalised_claim"],
        "n_elements": len(elems),
        "within_cap": len(elems) <= 5,
        "causal_element_present": any(CAUSE_RE.search(e) for e in elems),
        "elements_anchored": sum(1 for e in elems if _anchor_hits(entry, e) > 0),
        "elements": elems,
    }
    return out


def _pct(n: int, d: int) -> str:
    return f"{n}/{d}" if d else "0/0"


def summarise(results: list[dict]) -> None:
    n = len(results)
    c1_causal = sum(1 for r in results if r["cond1_extraction"]["causal_preserved"])
    frag_total = sum(len(r["cond2_bare"]) for r in results)
    c2_anchored = sum(
        1 for r in results for f in r["cond2_bare"] if f["any_element_anchored"]
    )
    c2_vague = sum(
        1 for r in results for f in r["cond2_bare"] if f["invented_vague_window"]
    )
    c3_anchored = sum(
        1 for r in results for f in r["cond3_context"] if f["any_element_anchored"]
    )
    c3_vague = sum(
        1 for r in results for f in r["cond3_context"] if f["invented_vague_window"]
    )
    c4_causal = sum(1 for r in results if r["cond4_intact"]["causal_element_present"])
    c4_cap = sum(1 for r in results if r["cond4_intact"]["within_cap"])
    c4_anchor = sum(1 for r in results if r["cond4_intact"]["elements_anchored"] > 0)
    c4_type = sum(
        1
        for r in results
        if "causal" in (r["cond4_intact"]["claim_type"] or "").lower()
    )

    print("\n" + "=" * 68)
    print("CLAIM-INTEGRITY PROBE — SUMMARY")
    print("=" * 68)
    print(f"Inputs (compound causal submissions):            {n}")
    print("\nCOND 1 — current extraction")
    print(f"  causal link preserved in ANY claim:            {_pct(c1_causal, n)}")
    for r in results:
        c1 = r["cond1_extraction"]
        print(
            f"    {r['key']:<12} n_claims={c1['n_claims']} "
            f"causal={'Y' if c1['causal_preserved'] else 'N'} "
            f"full-anchor claims={c1['claims_with_full_anchor']}/{c1['n_claims']}"
        )
    print(f"\nCOND 2 — bare fragment decompose (current path); fragments={frag_total}")
    print(
        f"  >=1 element carries user's anchor:             {_pct(c2_anchored, frag_total)}"
    )
    print(
        f"  invented vague window ('recent period'):       {_pct(c2_vague, frag_total)}"
    )
    print(f"\nCOND 3 — candidate B (context-carried decompose)")
    print(
        f"  >=1 element carries user's anchor:             {_pct(c3_anchored, frag_total)}"
    )
    print(
        f"  invented vague window:                         {_pct(c3_vague, frag_total)}"
    )
    print(f"\nCOND 4 — candidate E (intact sentence, one claim)")
    print(f"  within 5-element cap:                          {_pct(c4_cap, n)}")
    print(f"  causal element present:                        {_pct(c4_causal, n)}")
    print(f"  >=1 element anchored:                          {_pct(c4_anchor, n)}")
    print(f"  claim_type = causal_interpretive:              {_pct(c4_type, n)}")
    print("=" * 68)


async def main() -> None:
    # Routing controls first — free, and a failure here voids the rest.
    print("ROUTING CONTROLS (recombine_single_thesis):")
    control_rows = check_routing_controls()
    for row in control_rows:
        mark = "ok " if row["ok"] else "!! "
        print(
            f"  {mark}{row['key']}: expected recombine={row['expected']}, "
            f"got {row['recombined']}"
        )
    if not all(r["ok"] for r in control_rows):
        print("!! ROUTING CONTROL FAILURE — fix before trusting LLM metrics")

    results = []
    for i, entry in enumerate(POOL):
        try:
            results.append(await probe_one(i, entry))
        except Exception as e:  # noqa: BLE001
            print(f"[{entry['key']}] FAILED: {type(e).__name__}: {e}", flush=True)
            results.append({"key": entry["key"], "error": str(e)})
    results = [r for r in results if "error" not in r]

    out_path = BACKEND_DIR / "scripts" / ".claim_integrity_probe.json"
    out_path.write_text(
        json.dumps(
            {"ran_at": datetime.utcnow().isoformat(), "results": results},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"\nDetail -> {out_path}")
    summarise(results)


if __name__ == "__main__":
    asyncio.run(main())
