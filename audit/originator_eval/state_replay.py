"""Offline state replay: which element states would the originator review move?

Free and local (design §7.4). For every stored Astra run, re-derive each
element's state twice with the production rule (`_derive_element_state_with_
authority`): once on the stored tiers, once with the eval's lowered URLs set to
reporting. WEIGHT EFFECT ONLY: the mapper also sees tier in its prompt, and
its reaction is only visible on live checks (design §5).

Run from backend/:  python ../audit/originator_eval/state_replay.py <eval_result.json> [run_index]
"""

import collections
import glob
import json
import os
import sys

sys.path.insert(0, ".")
from app.pipeline.claim_map_analyzer import (  # noqa: E402
    _derive_element_state_with_authority,
)

FLOOR = 3  # FACTUAL_ and GROUNDS_MIN_WEIGHTED_SUPPORT are both 3 today


def _state(elem, evidence):
    refs = [
        {"evidence_id": r.get("evidenceId"), "relationship": r.get("relationship")}
        for r in elem.get("evidenceRefs") or []
    ]
    state, basis = _derive_element_state_with_authority(
        {"evidence_refs": refs}, evidence, FLOOR, "support_floor"
    )
    return getattr(state, "value", state), basis.get("rule_applied")


def _cause(elem, lowered_ids):
    sides = {
        r.get("relationship")
        for r in elem.get("evidenceRefs") or []
        if r.get("evidenceId") in lowered_ids
    }
    return (
        "+".join(sorted(s for s in sides if s in ("supports", "challenges"))) or "none"
    )


def main():
    result = json.load(open(sys.argv[1], encoding="utf-8"))
    run = int(sys.argv[2]) if len(sys.argv) > 2 else len(result["receipts"]) - 1
    here = os.path.dirname(os.path.abspath(__file__))
    rows = {
        r["id"]: r
        for r in json.load(
            open(os.path.join(here, "heldout_inputs.json"), encoding="utf-8")
        )
    }
    lowered_urls = {
        rows[i]["url"]
        for i, rc in result["receipts"][run].items()
        if rc.get("to_tier") == "reporting"
    }

    changes, elements, touched = [], 0, 0
    for path in sorted(glob.glob("../tmp/astra-regrade-*/*/owner.json")):
        record = os.path.basename(os.path.dirname(path))
        check = json.load(open(path, encoding="utf-8"))
        for claim in check.get("claims") or []:
            cm = claim.get("claimMap") or {}
            before = [
                {"evidence_id": e.get("evidenceId"), "tier": e.get("tier")}
                for e in claim.get("evidence") or []
            ]
            lowered_ids = {
                e.get("evidenceId")
                for e in claim.get("evidence") or []
                if e.get("tier") == "primary" and e.get("url") in lowered_urls
            }
            after = [
                dict(e, tier="reporting") if e["evidence_id"] in lowered_ids else e
                for e in before
            ]
            for elem in cm.get("elements") or []:
                elements += 1
                refs = {r.get("evidenceId") for r in elem.get("evidenceRefs") or []}
                if not refs & lowered_ids:
                    continue
                touched += 1
                s0, _ = _state(elem, before)
                s1, rule1 = _state(elem, after)
                if s0 != s1:
                    changes.append(
                        {
                            "record": record,
                            "run_dir": (
                                path.split(os.sep)[-3]
                                if os.sep in path
                                else path.split("/")[-3]
                            ),
                            "element": elem.get("description", "")[:90],
                            "from": s0,
                            "to": s1,
                            "rule": rule1,
                            "lowered_side": _cause(elem, lowered_ids),
                        }
                    )
    print(
        f"eval run {run + 1}: {len(lowered_urls)} URLs lowered; {elements} elements; {touched} touched; {len(changes)} state changes"
    )
    print(collections.Counter((c["from"], c["to"], c["lowered_side"]) for c in changes))
    for c in changes:
        print(
            f"  {c['record']:<18} {c['from']:>10} -> {c['to']:<10} [{c['rule']}; lowered {c['lowered_side']}] {c['element']}"
        )


if __name__ == "__main__":
    main()
