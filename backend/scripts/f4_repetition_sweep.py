"""F4 real-evidence sweep — run the unanchored-repetition detector over frozen,
already-classified evidence pools and report what fires, so the sentence-shingle
thresholds can be judged against REAL text distributions (NF-18 lesson: synthetic
fixtures won't surface real-world similarity).

Pools: the mapping-sweep corpora (scripts/.mapping_sweep_pool*.json) — real
Serper/adapter evidence with tiers assigned. Read-only; mutates nothing on disk.

Run:  cd backend && python -m scripts.f4_repetition_sweep
"""

import glob
import json
import os

from app.utils.corroboration import (
    annotate_repetition_clusters,
    _get_ownership_group,
    _MIN_REPETITION_CLUSTER,
    _MIN_SHINGLE_JACCARD,
)

POOL_GLOB = os.path.join(os.path.dirname(__file__), ".mapping_sweep_pool*.json")


def _load_pools():
    for path in sorted(glob.glob(POOL_GLOB)):
        try:
            data = json.load(open(path, encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - diagnostic
            print(f"  ! skip {os.path.basename(path)}: {exc}")
            continue
        for i, pool in enumerate(data):
            yield f"{os.path.basename(path)}#{i}", pool


def main() -> None:
    print(
        f"F4 sweep — min_cluster={_MIN_REPETITION_CLUSTER} "
        f"shingle_jaccard>={_MIN_SHINGLE_JACCARD}\n"
    )
    total_pools = 0
    total_fires = 0
    total_items_flagged = 0

    for name, pool in _load_pools():
        total_pools += 1
        evs = pool.get("evidence", [])
        # Detector mutates in place; that's fine for an in-memory diagnostic.
        clusters = annotate_repetition_clusters(evs)
        claim = (pool.get("claim_text") or "")[:70]
        tiers = {}
        for e in evs:
            tiers[e.get("tier") or "none"] = tiers.get(e.get("tier") or "none", 0) + 1
        header = f"[{name}] n={len(evs)} tiers={tiers} :: {claim}"
        if not clusters:
            print(f"{header}\n    -> no repetition cluster\n")
            continue

        total_fires += clusters
        print(f"{header}\n    -> {clusters} cluster(s):")
        by_cluster = {}
        for e in evs:
            cid = e.get("repetition_cluster_id")
            if cid:
                by_cluster.setdefault(cid, []).append(e)
        for cid, members in sorted(by_cluster.items()):
            total_items_flagged += len(members)
            groups = {
                _get_ownership_group(m.get("source", ""), m.get("url", ""))
                for m in members
            }
            print(
                f"      cluster {cid}: {len(members)} items, "
                f"{len(groups)} ownership group(s)"
            )
            for m in members:
                print(
                    f"        - [{m.get('tier')}] {m.get('source')}  "
                    f"{(m.get('snippet') or m.get('text') or '')[:90]!r}"
                )
        print()

    print(
        f"SUMMARY: {total_pools} pools, {total_fires} clusters fired, "
        f"{total_items_flagged} items flagged.\n"
        f"MANUAL CHECK: are any flagged sets genuinely-independent, "
        f"diverse-wording reporting (a false positive)?"
    )


if __name__ == "__main__":
    main()
