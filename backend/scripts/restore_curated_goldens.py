"""Restore curated golden sections after `--update-golden`.

`replay_bench.py --update-golden` writes an observation-only capture: it DROPS
`hard_invariants`, the curated `notes`, and every tolerance the corpus author
set by hand (learned 2026-09-09). This script merges the fresh capture with
the committed golden:

  * hard_invariants  <- committed (curated; never auto-derived)
  * notes            <- committed + a dated line
  * tolerant_counters:
      - tolerance-0 pins: committed value AND tolerance kept (re-pin by hand
        after reading the observation — never by assumption)
      - other keys: fresh VALUE, committed TOLERANCE
      - keys only in the fresh capture: added as captured
  * set_jaccard, captured_at, captured_with(_known_bugs) <- fresh

Usage (from repo root):
  python backend/scripts/restore_curated_goldens.py            # all claims
  python backend/scripts/restore_curated_goldens.py TRU-018F-44AA
Prints, per claim, every tolerance-0 pin whose fresh value differs from the
committed pin — those are the ones to read against the observation.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "backend" / "tests" / "replay_corpus"
DATE = "2026-09-10"
NOTE = (
    f"{DATE}: counters re-captured after the full corpus re-record (decomposition "
    "specificity rule re-keyed every cassette); hard_invariants, notes and "
    "tolerances restored from the committed golden by backend/scripts/restore_curated_goldens.py."
)


def committed(path: Path) -> dict:
    rel = path.relative_to(ROOT).as_posix()
    out = subprocess.run(
        ["git", "show", f"HEAD:{rel}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if out.returncode != 0:
        raise SystemExit(f"no committed golden for {rel}: {out.stderr.strip()}")
    return json.loads(out.stdout)


def merge(fresh: dict, old: dict) -> tuple[dict, list[str]]:
    merged = dict(fresh)
    merged["hard_invariants"] = old.get("hard_invariants", {})
    merged["notes"] = (old.get("notes") or "").rstrip() + " | " + NOTE
    counters = {}
    fresh_c = fresh.get("tolerant_counters", {}) or {}
    old_c = old.get("tolerant_counters", {}) or {}
    moved_pins = []
    for key, entry in old_c.items():
        tol = entry.get("tolerance", 0)
        if tol == 0:
            counters[key] = dict(entry)
            if key in fresh_c and fresh_c[key].get("value") != entry.get("value"):
                moved_pins.append(
                    f"{key}: pinned {entry.get('value')} -> observed {fresh_c[key].get('value')}"
                )
        elif key in fresh_c:
            counters[key] = {"value": fresh_c[key].get("value"), "tolerance": tol}
        else:
            counters[key] = dict(entry)
    for key, entry in fresh_c.items():
        if key not in counters:
            counters[key] = dict(entry)
    merged["tolerant_counters"] = counters
    return merged, moved_pins


def main(argv):
    claims = argv or sorted(
        p.name for p in CORPUS.iterdir() if p.name.startswith("TRU-")
    )
    for claim in claims:
        path = CORPUS / claim / "golden.json"
        fresh = json.loads(path.read_text(encoding="utf-8"))
        old = committed(path)
        merged, moved = merge(fresh, old)
        path.write_text(
            json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        flag = "  ⚠ pins moved: " + "; ".join(moved) if moved else "  pins hold"
        print(f"{claim}: restored{flag}")


if __name__ == "__main__":
    main(sys.argv[1:])
