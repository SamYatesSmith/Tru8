"""
Compare evidence URLs between two frozen replay runs (E vs F).
For each fixture and each claim, compute Jaccard similarity of evidence_urls sets.
Also compute per-element URL Jaccard using evidence_refs from ClaimMaps.
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


def _extract_element_urls(claim_map, evidence_list):
    """Extract per-element URL sets from ClaimMap evidence_refs.

    Returns dict of element_id -> set of URLs mapped to that element.
    """
    if not claim_map or not isinstance(claim_map, dict):
        return {}

    # Build evidence_id -> url lookup from evidence list
    id_to_url = {}
    for ev in evidence_list:
        eid = ev.get("evidence_id", "")
        url = ev.get("url", "")
        if eid and url:
            id_to_url[eid] = url

    element_urls = {}
    for elem in claim_map.get("elements", []):
        eid = elem.get("element_id", "?")
        urls = set()
        for ref in elem.get("evidence_refs", []):
            url = id_to_url.get(ref.get("evidence_id", ""), "")
            if url:
                urls.add(url)
        element_urls[eid] = urls

    return element_urls


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
        claim_maps_e = data_e.get("claim_maps", {})
        claim_maps_f = data_f.get("claim_maps", {})

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

                print(
                    f"\n  Claim {pos} | Jaccard = {j:.4f} | E: {len(set_e)} urls, F: {len(set_f)} urls"
                )
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

                # Per-element URL Jaccard (if ClaimMaps available)
                cm_e = claim_maps_e.get(pos)
                cm_f = claim_maps_f.get(pos)
                # Build evidence list from the data for URL lookup
                # evidence_urls only has URLs, but claim_maps have evidence_refs with IDs
                # We need the full evidence data for ID->URL mapping
                check_data_e = data_e.get("_check_data", {})
                check_data_f = data_f.get("_check_data", {})
                evidence_e = []
                evidence_f = []
                if check_data_e:
                    claims_e = check_data_e.get("claims", [])
                    pos_int = int(pos)
                    if pos_int < len(claims_e):
                        evidence_e = claims_e[pos_int].get("evidence", [])
                if check_data_f:
                    claims_f = check_data_f.get("claims", [])
                    pos_int = int(pos)
                    if pos_int < len(claims_f):
                        evidence_f = claims_f[pos_int].get("evidence", [])

                elem_urls_e = _extract_element_urls(cm_e, evidence_e)
                elem_urls_f = _extract_element_urls(cm_f, evidence_f)
                if elem_urls_e or elem_urls_f:
                    all_elements = sorted(set(elem_urls_e) | set(elem_urls_f))
                    print(f"    Per-element URL Jaccard:")
                    for eid in all_elements:
                        eu = elem_urls_e.get(eid, set())
                        fu = elem_urls_f.get(eid, set())
                        ej = jaccard(eu, fu)
                        marker = " ***" if ej < 1.0 else ""
                        print(
                            f"      {eid}: {ej:.4f} (E={len(eu)}, F={len(fu)}){marker}"
                        )

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
        print(
            f"Consistency rate: {(total_claims - divergent_claims) / total_claims * 100:.1f}%"
        )


if __name__ == "__main__":
    main()
