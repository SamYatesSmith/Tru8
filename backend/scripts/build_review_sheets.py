"""Build human-review sheets from a regrade run (Astra's 8/10 gate: a knowledgeable
person judges >=200 directional relationships, target >=95% justified).

Usage (from repo root):
  python backend/scripts/build_review_sheets.py tmp/astra-regrade-final audit/review_sheets/2026-09-09

One Markdown sheet per record, one CSV of every directional label for tallying,
and a README with the protocol. Each row shows the label, the element, the
source, the system's own reasoning, and the passage the mapper was given
(the distilled facts or snippet — the same text the model read), so the
reviewer never has to open the app.
"""

import csv
import json
import re
import sys
from pathlib import Path

RUN = Path(sys.argv[1])
OUT = Path(sys.argv[2])
OUT.mkdir(parents=True, exist_ok=True)

GATE_WORDS = {
    "temporal_scope": "different period",
    "jurisdiction_scope": "another country's official source",
    "measure_scope": "different interval",
    "interested_party": "the claimant's own organ",
    "recital_scope": "reports the claim rather than making it",
    "absence_of_evidence": "says evidence is lacking, not a contrary finding",
    "same_study_scope": "another host of a study already counted",
    "echo_scope": "a copy of a source already counted",
    "fact_applicability": "time applicability not established",
    "relationship_scope": "scope review",
}


def clean(s, n=900):
    s = re.sub(r"\s+", " ", (s or "")).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def domain(url):
    m = re.match(r"https?://(?:www\.)?([^/]+)", url or "")
    return m.group(1) if m else (url or "")


rows = []
sheets = []
for folder in sorted(p for p in RUN.iterdir() if p.is_dir()):
    status_f = folder / "status.json"
    owner_f = folder / "owner.json"
    if not owner_f.exists():
        continue
    status = (
        json.loads(status_f.read_text(encoding="utf-8")) if status_f.exists() else {}
    )
    owner = json.loads(owner_f.read_text(encoding="utf-8"))
    run = json.loads((folder / "run.json").read_text(encoding="utf-8"))
    check_id = run["check_id"]
    md = [f"# Review sheet — {folder.name}", ""]
    md.append(
        f"Check `{check_id}` · {round(status.get('seconds', 0))} s · {status.get('sources')} sources. Input: {clean(json.dumps(run['input']), 300)}"
    )
    md.append("")
    md.append(
        "For each **directional label** below answer: **Justified?** Y / N / Unsure. If N, the kind: "
        "`direction` (the source says the opposite) · `absent` (the source does not say this) · "
        "`scope` (different population / period / place / endpoint / study) · `recital` (the source only repeats the claim) · "
        "`other` (say what). One line of note when you mark N or Unsure."
    )
    md.append("")
    n_dir = 0
    for ci, claim in enumerate(owner.get("claims", []), 1):
        cm = claim.get("claimMap") or {}
        ev = {
            (e.get("evidenceId") or e.get("id")): e for e in claim.get("evidence", [])
        }
        md.append(f"## Claim {ci}: {clean(claim.get('text'), 400)}")
        md.append("")
        for ei, el in enumerate(cm.get("elements", []), 1):
            state = el.get("state")
            md.append(f"### Element {ei} — state: **{state}**")
            md.append("")
            md.append(f"> {clean(el.get('description'), 500)}")
            md.append("")
            refs = el.get("evidenceRefs") or el.get("evidence_refs") or []
            directional = [
                r for r in refs if r.get("relationship") in ("supports", "challenges")
            ]
            context = [r for r in refs if r.get("relationship") == "context"]
            if not directional:
                md.append("_No directional labels on this element._")
                md.append("")
            for r in directional:
                n_dir += 1
                eid = r.get("evidenceId") or r.get("evidence_id")
                e = ev.get(eid, {})
                passage = e.get("snippet") or e.get("text") or ""
                quotes = [
                    c.get("quote") for c in (r.get("citations") or []) if c.get("quote")
                ]
                label_id = f"{folder.name}/c{ci}/e{ei}/{eid}"
                md.append(f"#### {label_id}")
                md.append("")
                md.append(
                    f"- **Label:** `{r.get('relationship')}` · **Source:** [{clean(e.get('title'), 120)}]({e.get('url')}) · {domain(e.get('url'))} · tier `{e.get('tier')}` · type `{e.get('evidenceType') or e.get('evidence_type')}`"
                )
                md.append(f"- **System's reasoning:** {clean(r.get('reasoning'), 500)}")
                if quotes:
                    md.append(
                        f"- **Exact quotation the system cited:** “{clean(quotes[0], 600)}”"
                    )
                md.append(
                    f"- **What the mapper was given (distilled facts or snippet):** {clean(passage, 900)}"
                )
                md.append(
                    "- **Justified?** ☐ Y ☐ N ☐ Unsure · **Kind:** ______ · **Note:** ________________________________"
                )
                md.append("")
                rows.append(
                    {
                        "label_id": label_id,
                        "record": folder.name,
                        "check_id": check_id,
                        "claim": ci,
                        "element": ei,
                        "state": state,
                        "relationship": r.get("relationship"),
                        "source": domain(e.get("url")),
                        "url": e.get("url"),
                        "tier": e.get("tier"),
                        "reasoning": clean(r.get("reasoning"), 300),
                        "justified": "",
                        "kind": "",
                        "note": "",
                    }
                )
            if context:
                md.append(
                    "<details><summary>Context only (not graded; flag here if one of these should have been directional)</summary>"
                )
                md.append("")
                for r in context:
                    e = ev.get(r.get("evidenceId") or r.get("evidence_id"), {})
                    md.append(
                        f"- {domain(e.get('url'))} — {clean(e.get('title'), 100)} — _{clean(r.get('reasoning'), 160)}_"
                    )
                md.append("")
                md.append("</details>")
                md.append("")
            basis = el.get("basis") or {}
            set_aside = []
            for key, word in GATE_WORDS.items():
                rec = basis.get(key)
                for x in (rec or {}).get("scoped") or []:
                    e = ev.get(x.get("evidence_id"), {})
                    was = (
                        x.get("was")
                        or (x.get("original_ref") or {}).get("relationship")
                        or "?"
                    )
                    detail = (
                        x.get("counted_as")
                        or x.get("element_period")
                        or x.get("reason")
                        or x.get("excerpt")
                        or ""
                    )
                    set_aside.append(
                        f"- {domain(e.get('url'))} was read as `{was}`, set aside as context: {word}{' — ' + clean(str(detail), 140) if detail else ''}"
                    )
            if set_aside:
                md.append(
                    "<details><summary>Set aside by the system's mechanical rules (flag here if a rule fired wrongly)</summary>"
                )
                md.append("")
                md.extend(set_aside)
                md.append("")
                md.append("</details>")
                md.append("")
    (OUT / f"{folder.name}.md").write_text("\n".join(md), encoding="utf-8")
    sheets.append((folder.name, n_dir))

with (OUT / "labels.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader()
    w.writerows(rows)

readme = [
    "# Human review of directional relationships — 2026-09-09 regrade records",
    "",
    "Astra's 8/10 gate (`tmp/tru8-hands-on/tru8-route-to-eight.md`, Evidence fidelity): a knowledgeable human reviews at least 200 directional relationships; target at least 95% justified support/challenge labels, misses reported by kind, a second reviewer on ambiguous cases.",
    "",
    f"These sheets carry **{len(rows)} directional labels** across {len(sheets)} records from the final default-configuration regrade of Astra's 14 inputs (`tmp/astra-regrade-final/`, branch `codex/evidence-quality`).",
    "",
    "## Protocol",
    "",
    "1. Open a sheet. For each label, read the element, the system's reasoning and the passage the mapper was given. Decide **Justified? Y / N / Unsure** — is the label warranted by what the source says about *that* element?",
    "2. If N: name the kind — `direction`, `absent`, `scope`, `recital`, `other` — and write one line.",
    "3. Record answers in `labels.csv` (columns `justified`, `kind`, `note`), one row per label; `label_id` matches the heading in the sheet.",
    "4. Do not look up the source live unless the passage is insufficient to decide; if you do, say so in the note. The question is whether the label is justified by what the system read.",
    "5. Context-only and set-aside lists are not graded; flag one only if you think it should have been directional or a rule fired wrongly.",
    "",
    "## Tally",
    "",
    "`justified rate = Y / (Y + N)`; report Unsure separately; report kinds of N. Anything under 95% names the next build.",
    "",
    "| Record | Directional labels |",
    "|---|---:|",
]
readme += [f"| {name} | {n} |" for name, n in sheets]
readme += ["", f"| **Total** | **{len(rows)}** |"]
(OUT / "README.md").write_text("\n".join(readme), encoding="utf-8")
print(f"{len(sheets)} sheets, {len(rows)} directional labels -> {OUT}")
