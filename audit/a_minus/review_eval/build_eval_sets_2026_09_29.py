"""Build the 2026-09-29 relationship-review eval sets (M1, the founder's scoped path).

Dev set: the 156 labelled pairs on the 19 A− baseline records (labels.csv),
payloads fetched from the public endpoint (no key needed).

Held-out set: the 2026-09-09/10 blind-review sheets (audit/review_sheets/*),
never used to tune the review. Payloads are the stored owner payloads in
tmp/astra-regrade-*/<record>/owner.json. Label = both blind reviewers agree:
  supports, (Y, Y) -> must_survive ; (N, N) -> should_demote ; anything else skipped.
All should_demote pairs + a seeded sample of must_survive, and each payload is
PRUNED to its labelled supports refs so no spend goes on unlabelled pairs.

Usage: python build_eval_sets_2026_09_29.py <out_dir> [--negatives 200]
"""

import csv
import glob
import json
import os
import random
import sys
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
SHEET_TO_RUN = {
    "2026-09-09": "astra-regrade-final",
    "2026-09-09-postfix": "astra-regrade-postfix",
    "2026-09-10-b2run1": "astra-regrade-2026-09-10-b2run1",
    "2026-09-10-b2run2": "astra-regrade-2026-09-10-b2run2",
    "2026-09-10-b2run3": "astra-regrade-2026-09-10-b2run3",
    "2026-09-10-b2run3b": "astra-regrade-2026-09-10-b2run3b",
    "2026-09-10-run1": "astra-regrade-2026-09-10-run1",
    "2026-09-10-run2": "astra-regrade-2026-09-10-run2",
    "2026-09-10-run3": "astra-regrade-2026-09-10-run3",
}
API = "https://api.trueight.com/api/v1/checks/public/{}?detailed=true"


def _prune(payload, keep):
    """Drop every supports ref not in ``keep`` = {(element_id, evidence_id)}."""
    for claim in payload.get("claims") or []:
        for el in (claim.get("claimMap") or {}).get("elements") or []:
            el["evidenceRefs"] = [
                r
                for r in el.get("evidenceRefs") or []
                if r.get("relationship") != "supports"
                or (el["elementId"], r["evidenceId"]) in keep
            ]
    return payload


def build_dev(out):
    os.makedirs(out, exist_ok=True)
    rows = list(
        csv.DictReader(
            open(
                os.path.join(ROOT, "audit/a_minus/review_eval/labels.csv"),
                encoding="utf-8",
            )
        )
    )
    for check_id in sorted({r["check_id"] for r in rows}):
        path = os.path.join(out, f"{check_id}.json")
        if os.path.exists(path):
            continue
        req = urllib.request.Request(
            API.format(check_id), headers={"User-Agent": "tru8-eval/1.0"}
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            open(path, "wb").write(resp.read())
    return len(rows)


def build_heldout(out, negatives, seed=29):
    os.makedirs(out, exist_ok=True)
    pos, neg = [], []
    for sheet, run in SHEET_TO_RUN.items():
        f = os.path.join(ROOT, "audit/review_sheets", sheet, "labels_reviewed.csv")
        if not os.path.exists(f):
            continue
        for r in csv.DictReader(open(f, encoding="utf-8")):
            if r["tru8_label"] != "supports":
                continue
            verdicts = (r["gemini_justified"], r["gemini_flash_justified"])
            record, _claim, element_id, evidence_id = r["label_id"].split("/")
            item = (sheet, run, record, element_id, evidence_id, r)
            if verdicts == ("Y", "Y"):
                neg.append(item)
            elif verdicts == ("N", "N"):
                pos.append(item)
    random.Random(seed).shuffle(neg)
    # Pack negatives onto the payloads that already hold positives: calls are
    # per claim, so scattered negatives cost a call each (2026-09-29 budget).
    pos_stems = {(p[0], p[2]) for p in pos}
    neg.sort(key=lambda n: (n[0], n[2]) not in pos_stems)
    chosen = pos + neg[:negatives]
    keep = {}
    labels = []
    for sheet, run, record, element_id, evidence_id, r in chosen:
        stem = f"{sheet}__{record}"
        keep.setdefault(stem, (run, record, set()))[2].add((element_id, evidence_id))
        labels.append(
            {
                "pair_key": f"{stem}|{element_id}|{evidence_id}",
                "relationship": "supports",
                "label": (
                    "should_demote"
                    if (r["gemini_justified"] == "N")
                    else "must_survive"
                ),
                "class": r.get("gemini_kind") or "",
                "reason": (r.get("gemini_reason") or "")[:200],
            }
        )
    missing = 0
    for stem, (run, record, pairs) in keep.items():
        src = os.path.join(ROOT, "tmp", run, record, "owner.json")
        payload = json.load(open(src, encoding="utf-8"))
        present = {
            (el["elementId"], ref["evidenceId"])
            for c in payload.get("claims") or []
            for el in (c.get("claimMap") or {}).get("elements") or []
            for ref in el.get("evidenceRefs") or []
            if ref.get("relationship") == "supports"
        }
        missing += len(pairs - present)
        json.dump(
            _prune(payload, pairs),
            open(os.path.join(out, f"{stem}.json"), "w", encoding="utf-8"),
        )
    with open(
        os.path.join(out, "labels_heldout.csv"), "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.DictWriter(
            f, fieldnames=["pair_key", "relationship", "label", "class", "reason"]
        )
        w.writeheader()
        w.writerows(labels)
    return len(pos), min(negatives, len(neg)), missing, len(keep)


if __name__ == "__main__":
    out = sys.argv[1]
    n_neg = (
        int(sys.argv[sys.argv.index("--negatives") + 1])
        if "--negatives" in sys.argv
        else 200
    )
    print("dev labelled pairs:", build_dev(os.path.join(out, "dev")))
    print(
        "held-out pos/neg/missing/payloads:",
        build_heldout(
            os.path.join(
                out,
                (
                    sys.argv[sys.argv.index("--heldout-dir") + 1]
                    if "--heldout-dir" in sys.argv
                    else "heldout"
                ),
            ),
            n_neg,
        ),
    )
