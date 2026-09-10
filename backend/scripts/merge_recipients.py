"""Merge collected recipient CSVs into one master list, validating every row.

Usage (from repo root):
  python backend/scripts/merge_recipients.py <in1.csv> [<in2.csv> ...] --out audit/recipients/master.csv

The master lives under audit/recipients/ which is gitignored (third-party
contact data is never committed). Rules enforced here, not by convention:

  * a row needs a route AND the URL where the route was seen — no URL, no row;
  * a route of type `email` is refused when it looks pattern-built (the
    collector never saw it on a page: `route_seen_at_url` must be on the same
    domain as the address's domain OR be a page that the collector fetched —
    we accept any http(s) URL but flag domain mismatches for review);
  * personal-mailbox domains (gmail, hotmail, outlook, yahoo, icloud, proton)
    are refused for `email` rows — the person is reached by another route;
  * duplicates by (route) or by (name, organisation) collapse to one row, the
    one with the richer `current_topic` kept;
  * every refusal is written to <out>.rejected.csv with a reason, so the
    collector can fix the source rather than the symptom.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

HEADER = [
    "segment",
    "name",
    "role",
    "organisation",
    "country",
    "route_type",
    "route",
    "route_seen_at_url",
    "current_topic",
    "notes",
    "collected_on",
]
ROUTE_TYPES = {
    "email",
    "contact_form",
    "linkedin",
    "x",
    "bluesky",
    "substack",
    "org_inbox",
    "press_office",
    "submission_form",
    "github",
}
PERSONAL_DOMAINS = {
    "gmail.com",
    "googlemail.com",
    "hotmail.com",
    "hotmail.co.uk",
    "outlook.com",
    "live.com",
    "yahoo.com",
    "yahoo.co.uk",
    "icloud.com",
    "me.com",
    "proton.me",
    "protonmail.com",
    "aol.com",
}
# Best route first — the mass motion uses the highest-priority route a row holds.
ROUTE_PRIORITY = [
    "email",
    "org_inbox",
    "press_office",
    "submission_form",
    "contact_form",
    "linkedin",
    "substack",
    "github",
    "x",
    "bluesky",
]
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})$")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def validate(row: dict) -> str | None:
    """Return a rejection reason, or None when the row is acceptable."""
    for k in HEADER:
        row[k] = norm(row.get(k, ""))
    if not row["name"] and not row["organisation"]:
        return "no name or organisation"
    if row["route_type"] not in ROUTE_TYPES:
        return f"unknown route_type {row['route_type']!r}"
    if not row["route"]:
        return "empty route"
    if not row["route_seen_at_url"].startswith(("http://", "https://")):
        return "route_seen_at_url is not a URL (route not evidenced)"
    if row["route_type"] in ("email", "org_inbox", "press_office"):
        m = EMAIL_RE.match(row["route"])
        if not m:
            # An org inbox may be a community channel (Discord, Slack, a
            # forum) rather than an address — a URL is a legitimate route.
            if row["route_type"] != "email" and row["route"].startswith(
                ("http://", "https://")
            ):
                return None
            return "route_type email but route is not an address"
        domain = m.group(1).lower()
        if domain in PERSONAL_DOMAINS:
            return f"personal mailbox domain {domain} — reach by another route"
    return None


def flag(row: dict) -> str:
    """Non-fatal review flags."""
    flags = []
    if (
        row["route_type"] in ("email", "org_inbox", "press_office")
        and "@" in row["route"]
    ):
        domain = row["route"].split("@")[-1].lower()
        seen = urlparse(row["route_seen_at_url"]).netloc.lower()
        base = ".".join(domain.split(".")[-2:])
        if base not in seen:
            flags.append(
                f"address domain {domain} not on the page domain {seen} — confirm"
            )
    if not row["current_topic"]:
        flags.append("no current_topic")
    return "; ".join(flags)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    kept: dict[str, dict] = {}
    rejected: list[dict] = []
    seen_routes: dict[str, str] = {}
    for path in a.inputs:
        p = Path(path)
        if not p.exists():
            print(f"skip (missing): {p}")
            continue
        with io.open(p, encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                reason = validate(row)
                if reason:
                    rejected.append({**row, "reason": reason, "source_file": p.name})
                    continue
                row["review_flags"] = flag(row)
                key_route = row["route"].lower()
                key_person = (row["name"].lower(), row["organisation"].lower())
                dup = seen_routes.get(key_route) or (
                    key_person if key_person in kept else None
                )
                if dup and dup in kept:
                    # Same person twice: keep the BETTER route, the richer
                    # topic, and remember the other route in notes.
                    old = kept[dup]
                    better, other = (
                        (row, old)
                        if ROUTE_PRIORITY.index(row["route_type"])
                        < ROUTE_PRIORITY.index(old["route_type"])
                        else (old, row)
                    )
                    if len(other["current_topic"]) > len(better["current_topic"]):
                        better["current_topic"] = other["current_topic"]
                    better["notes"] = norm(
                        f"{better['notes']} | also {other['route_type']}: {other['route']}"
                    )
                    kept[dup] = better
                    seen_routes[key_route] = dup
                    continue
                kept[key_person] = row
                seen_routes[key_route] = key_person

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with io.open(out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=HEADER + ["review_flags"], extrasaction="ignore"
        )
        w.writeheader()
        for row in sorted(
            kept.values(), key=lambda r: (r["segment"], r["organisation"], r["name"])
        ):
            w.writerow(row)
    rej = out.with_suffix(".rejected.csv")
    with io.open(rej, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(
            f, fieldnames=HEADER + ["reason", "source_file"], extrasaction="ignore"
        )
        w.writeheader()
        w.writerows(rejected)

    by_seg: dict[str, int] = {}
    by_route: dict[str, int] = {}
    flagged = 0
    for r in kept.values():
        by_seg[r["segment"]] = by_seg.get(r["segment"], 0) + 1
        by_route[r["route_type"]] = by_route.get(r["route_type"], 0) + 1
        flagged += bool(r["review_flags"])
    print(f"kept {len(kept)} rows -> {out}")
    print(f"rejected {len(rejected)} rows -> {rej}")
    print("by segment:", dict(sorted(by_seg.items())))
    print("by route_type:", dict(sorted(by_route.items())))
    print(f"rows carrying a review flag: {flagged}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
