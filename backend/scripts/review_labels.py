"""Blind AI review of directional labels — the independent check behind Astra's
"human review of >=200 relationships" gate, without the human.

Two reviewers from different model families (OpenAI, Google) each read ONLY
the element and the passage the mapper was given — never Tru8's label or
reasoning — and say whether the passage supports, challenges or neither. A
label counts as justified when the reviewer's independent reading agrees.

Usage (from backend/, PYTHONPATH=.):
  python scripts/review_labels.py ../tmp/astra-regrade-final ../audit/review_sheets/2026-09-09 --dry-run
  python scripts/review_labels.py ../tmp/astra-regrade-final ../audit/review_sheets/2026-09-09 --reviewers gpt,gemini

Writes labels_reviewed.csv (one row per label, one column set per reviewer),
review_summary.md (rates, disagreements with the reviewers' one-line reasons)
and usage. Paid: ~1.5k tokens per label per reviewer. Never activates settings.
"""

import argparse
import asyncio
import csv
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PROMPT = (
    "You are an independent evidence reviewer. You will be shown ONE element of a "
    "claim and ONE passage from a source. Judge the passage on its own words only.\n\n"
    "Element (the thing that must hold):\n{element}\n\n"
    "Passage from the source:\n{passage}\n\n"
    "Question: does this passage, by itself, SUPPORT the element, CHALLENGE it, or NEITHER?\n"
    "- supports: the passage states or reports a finding that makes the element more likely true.\n"
    "- challenges: the passage states or reports a finding that contradicts the element or makes it less likely true.\n"
    "- neither: the passage is about something else, only repeats the claim without evidence, says evidence is lacking, "
    "concerns a different population/period/place/measure/study, or is too thin to tell.\n"
    "Do not use outside knowledge to fill gaps; a passage that does not say it does not support it.\n\n"
    'Reply with JSON only: {{"verdict": "supports|challenges|neither", "confidence": 0.0-1.0, "reason": "<one sentence>"}}'
)


def clean(s, n=2500):
    s = re.sub(r"\s+", " ", (s or "")).strip()
    return s if len(s) <= n else s[: n - 1] + "…"


def domain(url):
    m = re.match(r"https?://(?:www\.)?([^/]+)", url or "")
    return m.group(1) if m else (url or "")


def load_labels(run_dir: Path):
    labels = []
    for folder in sorted(p for p in run_dir.iterdir() if p.is_dir()):
        owner_f = folder / "owner.json"
        if not owner_f.exists():
            continue
        owner = json.loads(owner_f.read_text(encoding="utf-8"))
        for ci, claim in enumerate(owner.get("claims", []), 1):
            ev = {
                (e.get("evidenceId") or e.get("id")): e
                for e in claim.get("evidence", [])
            }
            for ei, el in enumerate(
                (claim.get("claimMap") or {}).get("elements", []), 1
            ):
                for r in el.get("evidenceRefs") or el.get("evidence_refs") or []:
                    if r.get("relationship") not in ("supports", "challenges"):
                        continue
                    eid = r.get("evidenceId") or r.get("evidence_id")
                    e = ev.get(eid, {})
                    quotes = [
                        c.get("quote")
                        for c in (r.get("citations") or [])
                        if c.get("quote")
                    ]
                    passage = (
                        quotes[0]
                        if quotes
                        else (e.get("snippet") or e.get("text") or "")
                    )
                    labels.append(
                        {
                            "label_id": f"{folder.name}/c{ci}/e{ei}/{eid}",
                            "record": folder.name,
                            "element": el.get("description") or "",
                            "state": el.get("state"),
                            "tru8_label": r.get("relationship"),
                            "tru8_reasoning": clean(r.get("reasoning"), 300),
                            "source": domain(e.get("url")),
                            "url": e.get("url"),
                            "tier": e.get("tier"),
                            "passage": clean(passage),
                        }
                    )
    return labels


async def review_gpt(prompt, model):
    import httpx
    from app.core.config import settings

    key = getattr(settings, "OPENAI_API_KEY", "")
    if not key:
        return None, {"error": "no OPENAI_API_KEY"}
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "max_tokens": 200,
            },
        )
    if resp.status_code != 200:
        return None, {"error": f"HTTP {resp.status_code}: {resp.text[:120]}"}
    data = resp.json()
    usage = data.get("usage", {})
    try:
        parsed = json.loads(data["choices"][0]["message"]["content"])
    except Exception as exc:  # noqa: BLE001
        return None, {"error": f"unparseable: {exc}"}
    return parsed, {
        "in": usage.get("prompt_tokens", 0),
        "out": usage.get("completion_tokens", 0),
    }


async def review_gemini(prompt, model):
    from app.services.google_ai import call_google_ai_with_usage

    try:
        parsed, usage = await call_google_ai_with_usage(
            prompt, temperature=0, max_tokens=200, timeout=45, model=model
        )
    except Exception as exc:  # noqa: BLE001
        return None, {"error": str(exc)[:120]}
    if not isinstance(parsed, dict):
        return None, {"error": "no response"}
    return parsed, {
        "in": (usage or {}).get("input_tokens", 0),
        "out": (usage or {}).get("output_tokens", 0),
    }


REVIEWERS = {
    "gpt": ("gpt-4o-mini", review_gpt),
    "gemini": ("gemini-3.5-flash-lite", review_gemini),
    # Fallback second reviewer when no OpenAI key works: the MAPPER's own model
    # family, so its agreement is partly self-agreement — say so in the record.
    "gemini_flash": ("gemini-3.7-flash", review_gemini),
}


def kind_of_miss(tru8_label, verdict):
    if verdict == tru8_label:
        return ""
    if verdict in ("supports", "challenges"):
        return "direction"
    return "neither"  # absent / scope / recital — the reviewer's reason says which


async def main(run_dir, out_dir, reviewers, dry_run, limit):
    labels = load_labels(run_dir)
    if limit:
        labels = labels[:limit]
    print(f"{len(labels)} directional labels from {run_dir}")
    if dry_run:
        est = (
            sum(
                len(PROMPT.format(element=l["element"], passage=l["passage"]))
                for l in labels
            )
            // 4
        )
        print(
            f"dry run: ~{est:,} prompt tokens per reviewer; reviewers={reviewers}; no calls made"
        )
        return
    sem = asyncio.Semaphore(4)
    usage = {r: {"in": 0, "out": 0, "errors": 0} for r in reviewers}
    started = time.monotonic()

    async def one(label, rname):
        model, fn = REVIEWERS[rname]
        prompt = PROMPT.format(element=label["element"], passage=label["passage"])
        async with sem:
            parsed, u = await fn(prompt, model)
        if parsed is None:
            usage[rname]["errors"] += 1
            return rname, {
                "verdict": "error",
                "confidence": "",
                "reason": u.get("error", ""),
            }
        usage[rname]["in"] += u.get("in", 0)
        usage[rname]["out"] += u.get("out", 0)
        v = str(parsed.get("verdict", "")).strip().lower()
        if v not in ("supports", "challenges", "neither"):
            v = "error"
        return rname, {
            "verdict": v,
            "confidence": parsed.get("confidence", ""),
            "reason": clean(parsed.get("reason"), 240),
        }

    tasks = [one(label, r) for label in labels for r in reviewers]
    results = await asyncio.gather(*tasks)
    idx = 0
    for label in labels:
        for _ in reviewers:
            rname, res = results[idx]
            idx += 1
            label[f"{rname}_verdict"] = res["verdict"]
            label[f"{rname}_confidence"] = res["confidence"]
            label[f"{rname}_reason"] = res["reason"]
            label[f"{rname}_justified"] = (
                ""
                if res["verdict"] == "error"
                else ("Y" if res["verdict"] == label["tru8_label"] else "N")
            )
            label[f"{rname}_kind"] = (
                ""
                if res["verdict"] == "error"
                else kind_of_miss(label["tru8_label"], res["verdict"])
            )

    out_dir.mkdir(parents=True, exist_ok=True)
    fields = list(labels[0].keys())
    with (out_dir / "labels_reviewed.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(labels)

    lines = [
        f"# Blind AI review — {run_dir.name} — {time.strftime('%Y-%m-%d %H:%M')}",
        "",
    ]
    lines.append(
        f"{len(labels)} directional labels; reviewers {', '.join(f'{r} ({REVIEWERS[r][0]})' for r in reviewers)}; each saw only the element and the passage. {round(time.monotonic() - started)} s."
    )
    lines.append("")
    lines.append("| Reviewer | Justified (Y) | Not (N) | Errors | Justified rate |")
    lines.append("|---|---:|---:|---:|---:|")
    for r in reviewers:
        y = sum(1 for l in labels if l[f"{r}_justified"] == "Y")
        n = sum(1 for l in labels if l[f"{r}_justified"] == "N")
        e = sum(1 for l in labels if l[f"{r}_verdict"] == "error")
        rate = f"{100 * y / (y + n):.1f}%" if (y + n) else "n/a"
        lines.append(f"| {r} | {y} | {n} | {e} | {rate} |")
    if len(reviewers) >= 2:
        a, b = reviewers[0], reviewers[1]
        both_scored = [
            l
            for l in labels
            if l[f"{a}_verdict"] != "error" and l[f"{b}_verdict"] != "error"
        ]
        both_y = sum(
            1
            for l in both_scored
            if l[f"{a}_justified"] == "Y" and l[f"{b}_justified"] == "Y"
        )
        both_n = sum(
            1
            for l in both_scored
            if l[f"{a}_justified"] == "N" and l[f"{b}_justified"] == "N"
        )
        split = len(both_scored) - both_y - both_n
        agree = sum(1 for l in both_scored if l[f"{a}_verdict"] == l[f"{b}_verdict"])
        lines.append("")
        lines.append(
            f"Both reviewers scored {len(both_scored)}: **both justified {both_y}**, both not {both_n}, split {split}. Reviewer-to-reviewer agreement {100 * agree / max(1, len(both_scored)):.1f}%."
        )
        lines.append("")
        lines.append("## Labels BOTH reviewers reject (read these first)")
        lines.append("")
        for l in both_scored:
            if l[f"{a}_justified"] == "N" and l[f"{b}_justified"] == "N":
                lines.append(
                    f"- `{l['label_id']}` Tru8 said **{l['tru8_label']}** ({l['source']}, {l['tier']}); {a}: {l[f'{a}_verdict']} — {l[f'{a}_reason']}; {b}: {l[f'{b}_verdict']} — {l[f'{b}_reason']}"
                )
        lines.append("")
        lines.append("## Split decisions (second-reviewer cases)")
        lines.append("")
        for l in both_scored:
            if (l[f"{a}_justified"] == "N") != (l[f"{b}_justified"] == "N"):
                lines.append(
                    f"- `{l['label_id']}` Tru8 **{l['tru8_label']}** ({l['source']}); {a}: {l[f'{a}_verdict']} — {l[f'{a}_reason']}; {b}: {l[f'{b}_verdict']} — {l[f'{b}_reason']}"
                )
    lines.append("")
    lines.append("## Usage")
    lines.append("")
    for r in reviewers:
        lines.append(
            f"- {r}: {usage[r]['in']:,} in / {usage[r]['out']:,} out tokens, {usage[r]['errors']} errors"
        )
    (out_dir / "review_summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("\n".join(lines[:12]))
    print("saved", out_dir / "review_summary.md")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("run_dir", type=Path)
    p.add_argument("out_dir", type=Path)
    p.add_argument("--reviewers", default="gpt,gemini")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=0)
    a = p.parse_args()
    asyncio.run(
        main(
            a.run_dir.resolve(),
            a.out_dir.resolve(),
            a.reviewers.split(","),
            a.dry_run,
            a.limit,
        )
    )
