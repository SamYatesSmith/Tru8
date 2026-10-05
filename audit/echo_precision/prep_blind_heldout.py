"""Blind labelling inputs for the held-out set (design rev 2 §10 M3).

The labeller sees only A and B: publisher, URL, title, date, verbatim text. No claim,
no detector rule, no similarity scores, no gate flag. Order shuffled (seed 20261005),
split into batches for separate fresh labellers. key_heldout.json maps ids back.
"""

import json, os, random

HERE = os.path.dirname(os.path.abspath(__file__))
pairs = json.load(open(os.path.join(HERE, "heldout_all.json"), encoding="utf-8"))
random.Random(20261005).shuffle(pairs)

blind, key = [], []
for n, p in enumerate(pairs, 1):
    pid = f"h{n:03d}"
    side = lambda s: {
        k: p[s][k] for k in ("source", "url", "title", "published_date")
    } | {"text": p[s]["verbatim"]}
    blind.append({"id": pid, "A": side("A"), "B": side("B")})
    key.append(
        {
            "id": pid,
            "claim_id": p["claim_id"],
            "source": p.get("source", "local"),
            "rule": p["rule"],
            "gate_would_scope": p["gate_would_scope"],
            "strong_facts": p["strong_facts"],
            "verbatim_source": p["verbatim_source"],
            "A_id": p["A"]["evidence_id"],
            "B_id": p["B"]["evidence_id"],
            "B_tier": p["B"]["tier"],
        }
    )

SIZE = 42
os.makedirs(os.path.join(HERE, "heldout_batches"), exist_ok=True)
for b in range(0, len(blind), SIZE):
    json.dump(
        blind[b : b + SIZE],
        open(
            os.path.join(HERE, "heldout_batches", f"batch{b // SIZE + 1}.json"),
            "w",
            encoding="utf-8",
        ),
        ensure_ascii=False,
        indent=1,
    )
json.dump(
    key, open(os.path.join(HERE, "key_heldout.json"), "w", encoding="utf-8"), indent=1
)
print("pairs", len(blind), "batches", (len(blind) + SIZE - 1) // SIZE)
