"""Render audit cases as readable markdown review sheets.

Generates one markdown file per case with evidence and mapper assignments
laid out for quick human judgment.

Usage:
    python scripts/audit_render.py
    python scripts/audit_render.py --case case-003
"""

import argparse
import json
import logging
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

AUDIT_DIR = backend_dir / "audit" / "track-n" / "audit"
CASES_DIR = AUDIT_DIR / "cases"
REVIEWS_DIR = AUDIT_DIR / "reviews"

FAILURE_MODE_LABELS = {
    "A": "Missed contradiction",
    "B": "Phantom support",
    "C": "Misattributed scope",
    "D": "State inflation",
}


def render_case(case: dict) -> str:
    """Render a case file as a markdown review sheet."""
    lines = []
    case_id = case["case_id"]
    claim = case["claim"]
    evidence_by_id = {ev["evidence_id"]: ev for ev in case["evidence"]}
    mapper = case["mapper_output"]

    # Header
    lines.append(f"# {case_id} — Review Sheet")
    lines.append("")
    lines.append(f"**Claim**: {claim['normalised_claim']}")
    lines.append(
        f"**Type**: {claim['claim_type']} | **Model**: {mapper['model']} | **Prompt hash**: `{mapper['prompt_hash']}`"
    )
    lines.append("")

    # Elements summary
    lines.append("## Elements")
    lines.append("")
    for elem in claim["elements"]:
        lines.append(f"- **{elem['element_id']}**: {elem['description']}")
    lines.append("")

    # Per-element review sections
    for m_elem in mapper["elements"]:
        eid = m_elem["element_id"]
        state = m_elem["state"]
        uncertainty = m_elem.get("uncertainty") or "—"
        refs = m_elem.get("evidence_refs", [])

        lines.append("---")
        lines.append("")
        lines.append(f"## {eid} — mapper state: `{state}`")
        if uncertainty != "—":
            lines.append(f"*Uncertainty*: {uncertainty}")
        lines.append("")

        if not refs:
            lines.append("*No evidence mapped to this element.*")
            lines.append("")
            lines.append(f"### State judgment: `{state}`")
            lines.append("")
            lines.append("| Field | Value |")
            lines.append("|-------|-------|")
            lines.append(f"| Mapper state | `{state}` |")
            lines.append("| Correct? | `___` (true/false) |")
            lines.append("| Expected state | `___` |")
            lines.append("| Failure mode | `___` (A/B/C/D/—) |")
            lines.append("| Notes | |")
            lines.append("")
            continue

        for ref in refs:
            ev_id = ref["evidence_id"]
            rel = ref["relationship"]
            reasoning = ref.get("reasoning") or "—"
            ev = evidence_by_id.get(ev_id, {})

            title = ev.get("title", "Unknown")
            source = ev.get("source", "")
            tier = ev.get("tier") or "unclassified"
            ev_type = ev.get("evidence_type") or "unclassified"
            full_text = ev.get("full_text", "")
            window = ev.get("mapper_window", "")
            url = ev.get("url", "")

            window_truncated = len(full_text) > len(window)

            lines.append(f"### {ev_id} -> `{rel}`")
            lines.append("")
            lines.append(f"**{title}** ({source}, {tier}/{ev_type})")
            if url:
                lines.append(f"URL: {url}")
            lines.append("")

            # Show what the mapper saw
            lines.append("**Mapper saw** (first 400 chars):")
            lines.append(f"> {window}")
            lines.append("")

            # If full text is longer, show what was outside the window
            if window_truncated:
                beyond = full_text[len(window) :]
                lines.append(f"**Beyond window** (+{len(beyond)} chars):")
                lines.append(f"> {beyond[:500]}{'...' if len(beyond) > 500 else ''}")
                lines.append("")

            lines.append(f"**Mapper reasoning**: {reasoning}")
            lines.append("")

            # Judgment table
            lines.append("| Field | Value |")
            lines.append("|-------|-------|")
            lines.append(f"| Mapper relationship | `{rel}` |")
            lines.append("| Correct? | `___` (true/false) |")
            lines.append(
                "| Expected relationship | `___` (supports/challenges/context) |"
            )
            lines.append("| Failure mode | `___` (A/B/C/D/—) |")
            lines.append(
                f"| Window sufficient? | `{'likely' if not window_truncated else '___'}` (true/false) |"
            )
            lines.append("| Notes | |")
            lines.append("")

        # State judgment
        lines.append(f"### State judgment: `{state}`")
        lines.append("")
        supports = sum(1 for r in refs if r["relationship"] == "supports")
        challenges = sum(1 for r in refs if r["relationship"] == "challenges")
        context = sum(1 for r in refs if r["relationship"] == "context")
        lines.append(
            f"Ref tally: {supports} supports, {challenges} challenges, {context} context"
        )
        lines.append("")
        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| Mapper state | `{state}` |")
        lines.append("| Correct? | `___` (true/false) |")
        lines.append("| Expected state | `___` (supported/disputed/unresolved) |")
        lines.append("| Failure mode | `___` (D/—) |")
        lines.append("| Notes | |")
        lines.append("")

    # Missing refs section
    lines.append("---")
    lines.append("")
    lines.append("## Missing refs")
    lines.append("")
    lines.append("Evidence the mapper should have mapped but didn't:")
    lines.append("")

    # List unmapped evidence
    mapped_ev_ids = set()
    for m_elem in mapper["elements"]:
        for ref in m_elem.get("evidence_refs", []):
            mapped_ev_ids.add(ref["evidence_id"])

    unmapped = [ev for ev in case["evidence"] if ev["evidence_id"] not in mapped_ev_ids]
    if unmapped:
        for ev in unmapped:
            lines.append(
                f"- **{ev['evidence_id']}**: {ev['title']} ({ev.get('source', '')})"
            )
            text_preview = (ev.get("full_text") or "")[:150]
            lines.append(f"  > {text_preview}")
            lines.append("")
    else:
        lines.append("*(All evidence was mapped)*")
        lines.append("")

    lines.append("Add missing refs here:")
    lines.append("")
    lines.append(
        "| Element | Evidence ID | Expected relationship | Failure mode | Window sufficient? | Notes |"
    )
    lines.append(
        "|---------|-------------|----------------------|--------------|-------------------|-------|"
    )
    lines.append("| | | | | | |")
    lines.append("")

    # Failure mode key
    lines.append("---")
    lines.append("")
    lines.append("## Failure mode key")
    lines.append("")
    for code, label in FAILURE_MODE_LABELS.items():
        lines.append(f"- **{code}**: {label}")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Render audit cases as markdown review sheets"
    )
    parser.add_argument(
        "--case", type=str, help="Render a specific case (e.g. case-003)"
    )
    args = parser.parse_args()

    REVIEWS_DIR.mkdir(parents=True, exist_ok=True)

    if args.case:
        case_files = [CASES_DIR / f"{args.case}.json"]
    else:
        case_files = sorted(CASES_DIR.glob("case-*.json"))

    if not case_files:
        print("No case files found.")
        return

    for path in case_files:
        if not path.exists():
            print(f"Not found: {path}")
            continue

        with open(path) as f:
            case = json.load(f)

        md = render_case(case)
        out_path = REVIEWS_DIR / f"{case['case_id']}.md"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(md)

        n_refs = sum(
            len(e.get("evidence_refs", [])) for e in case["mapper_output"]["elements"]
        )
        print(f"  {case['case_id']}: {n_refs} refs to review -> {out_path.name}")

    print(f"\nReview sheets written to {REVIEWS_DIR}")


if __name__ == "__main__":
    main()
