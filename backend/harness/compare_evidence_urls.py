"""
Compare evidence URLs between two frozen replay runs (E vs F).
For each fixture and each claim, compute Jaccard similarity of evidence_urls sets.
Output ONLY claims where Jaccard < 1.0.
"""

import json
import os

RUN_E = "C:/Users/projects/Tru8/backend/harness/runs/20260206T152808_frozen-replay-E"
RUN_F = "C:/Users/projects/Tru8/backend/harness/runs/20260206T153423_frozen-replay-F"


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0  # both empty = identical
    return len(a & b) / len(a | b)


def main():
    # Collect fixture filenames (skip underscore-prefixed meta files)
    fixtures_e = sorted(
        f for f in os.listdir(RUN_E) if f.endswith(".json") and not f.startswith("_")
    )
    fixtures_f = sorted(
        f for f in os.listdir(RUN_F) if f.endswith(".json") and not f.startswith("_")
    )

    # Verify same fixture set
    if fixtures_e != fixtures_f:
        only_e = set(fixtures_e) - set(fixtures_f)
        only_f = set(fixtures_f) - set(fixtures_e)
        if only_e:
            print(f"WARNING: Fixtures only in E: {only_e}")
        if only_f:
            print(f"WARNING: Fixtures only in F: {only_f}")

    common = sorted(set(fixtures_e) & set(fixtures_f))
    print(f"Comparing {len(common)} fixtures between Run E and Run F")
    print(f"Run E: {RUN_E}")
    print(f"Run F: {RUN_F}")
    print("=" * 100)

    total_claims = 0
    divergent_claims = 0
    perfect_fixtures = 0

    for fixture_name in common:
        with open(os.path.join(RUN_E, fixture_name)) as f:
            data_e = json.load(f)
        with open(os.path.join(RUN_F, fixture_name)) as f:
            data_f = json.load(f)

        urls_e = data_e.get("evidence_urls", {})
        urls_f = data_f.get("evidence_urls", {})
        verdicts_e = data_e.get("verdicts", {})
        verdicts_f = data_f.get("verdicts", {})
        confidences_e = data_e.get("confidences", {})
        confidences_f = data_f.get("confidences", {})

        # Union of all claim positions from both runs
        all_positions = sorted(
            set(urls_e.keys()) | set(urls_f.keys()), key=lambda x: int(x)
        )

        fixture_has_divergence = False

        for pos in all_positions:
            total_claims += 1
            set_e = set(urls_e.get(pos, []))
            set_f = set(urls_f.get(pos, []))
            j = jaccard(set_e, set_f)

            if j < 1.0:
                divergent_claims += 1
                if not fixture_has_divergence:
                    # Print fixture header on first divergent claim
                    slug = fixture_name.replace(".json", "")
                    print(f"\n{'=' * 100}")
                    print(f"FIXTURE: {slug}")
                    print(f"{'=' * 100}")
                    fixture_has_divergence = True

                only_in_e = set_e - set_f
                only_in_f = set_f - set_e
                shared = set_e & set_f

                ve = verdicts_e.get(pos, "N/A")
                vf = verdicts_f.get(pos, "N/A")
                ce = confidences_e.get(pos, "N/A")
                cf = confidences_f.get(pos, "N/A")

                verdict_changed = ve != vf
                confidence_changed = ce != cf

                print(f"\n  Claim {pos} | Jaccard = {j:.4f} | E: {len(set_e)} urls, F: {len(set_f)} urls")
                print(f"    Verdict:    E={ve}  F={vf}  {'*** CHANGED ***' if verdict_changed else '(same)'}")
                print(f"    Confidence: E={ce}  F={cf}  {'*** CHANGED ***' if confidence_changed else '(same)'}")
                print(f"    Shared ({len(shared)}):")
                for u in sorted(shared):
                    print(f"      {u}")
                if only_in_e:
                    print(f"    Only in E ({len(only_in_e)}):")
                    for u in sorted(only_in_e):
                        print(f"      + {u}")
                if only_in_f:
                    print(f"    Only in F ({len(only_in_f)}):")
                    for u in sorted(only_in_f):
                        print(f"      + {u}")

        if not fixture_has_divergence:
            perfect_fixtures += 1

    # Summary
    print(f"\n{'=' * 100}")
    print("SUMMARY")
    print(f"{'=' * 100}")
    print(f"Total fixtures compared: {len(common)}")
    print(f"Perfect fixtures (all Jaccard=1.0): {perfect_fixtures}/{len(common)}")
    print(f"Total claims compared: {total_claims}")
    print(f"Divergent claims (Jaccard<1.0): {divergent_claims}/{total_claims}")
    if total_claims > 0:
        print(f"Consistency rate: {(total_claims - divergent_claims) / total_claims * 100:.1f}%")


if __name__ == "__main__":
    main()
