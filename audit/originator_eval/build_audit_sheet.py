"""Stratified 30-item audit of the blind labels (design §7.1).

At most 3 items per host; every held-out record represented; seed fixed so
the sample is reproducible. Overlap records (A- #18/#19 claims) excluded.
"""

import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
SEED, SIZE, PER_HOST = 20260930, 30, 3

rows = json.load(open(os.path.join(HERE, "heldout_inputs.json"), encoding="utf-8"))
labels = {r["id"]: r for r in json.load(open(os.path.join(HERE, "blind_labels.json"), encoding="utf-8"))}
held = [r for r in rows if not r["overlap"]]
rng = random.Random(SEED)
rng.shuffle(held)

chosen, hosts = [], {}


def take(row):
    if row in chosen or hosts.get(row["host"], 0) >= PER_HOST:
        return False
    chosen.append(row)
    hosts[row["host"]] = hosts.get(row["host"], 0) + 1
    return True


for record in sorted({rec for r in held for rec in r["records"]}):
    next(r for r in held if record in r["records"] and take(r))
for row in held:
    if len(chosen) >= SIZE:
        break
    take(row)

lines = [
    "# Founder audit: 30 blind labels (originator review eval)",
    "",
    "For each page: did its **publisher** produce the information it presents?",
    "Mark **Agree** or **Disagree** (with the right label). More than 3 disagreements means the rubric is revised and labelling redone.",
    "Rubric: `labelling_rubric.md`. Text shown is exactly what the labeller saw (cut to 400 chars here).",
    "",
]
for n, row in enumerate(chosen, 1):
    lab = labels[row["id"]]
    text = " ".join(row["text"].split())[:400]
    lines += [
        f"## {n}. `{row['id']}` {row['host']}",
        f"- **Title:** {row['title']}",
        f"- **URL:** {row['url']}",
        f"- **Text:** {text}",
        f"- **Label:** `{lab['label']}` ({lab['why']})",
        "- **Your verdict:** Agree / Disagree →",
        "",
    ]
open(os.path.join(HERE, "founder_audit.md"), "w", encoding="utf-8").write("\n".join(lines))
print(len(chosen), "items;", len(hosts), "hosts; records:", len({r["records"][0] for r in chosen}))
from collections import Counter
print(Counter(labels[r["id"]]["label"] for r in chosen))
