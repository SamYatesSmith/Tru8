"""Build / refresh the outreach working queue from the validated recipient master.

    python backend/scripts/outreach_queue.py                       # build or refresh
    python backend/scripts/outreach_queue.py --start 2026-09-14    # first send day
    python backend/scripts/outreach_queue.py --report              # counts only

Reads  audit/recipients/master.csv  (validated rows, gitignored)
Writes audit/recipients/queue.csv   (the working file, gitignored)

Idempotent: every state column already filled in queue.csv is preserved by ``rid``
(a stable hash of the route). Priority, wave, approach day and time are recomputed
only for rows whose status is still ``queued``. Procedure and column meaning:
audit/2026-09-11_outreach_operating_procedure.md §7.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "audit" / "recipients" / "master.csv"
QUEUE = ROOT / "audit" / "recipients" / "queue.csv"

MASTER_COLS = [
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
    "review_flags",
]
PLAN_COLS = [
    "priority",
    "wave",
    "approach_day",
    "approach_time_local",
    "send_channel_how",
    "src_tag",
]
STATE_COLS = [
    "topic_claim",
    "topic_source_url",
    "topic_piece_date",
    "topic_verified_on",
    "check_id",
    "record_url",
    "record_grade",
    "own_piece_in_pool",
    "pressure_pass_on",
    "charged_pence",
    "note_path",
    "note_verified_on",
    "founder_row_ok",
    "founder_read_on",
    "sent_on",
    "sent_by_route",
    "replied_on",
    "reply_shape",
    "outcome",
    "status",
    "held_reason",
    "updated_on",
]
COLS = ["rid"] + MASTER_COLS + PLAN_COLS + STATE_COLS

SEGMENT_WEIGHT = {"journalists_uk": 40, "newsletters": 40, "osint": 30}
ROUTE_WEIGHT = {
    "email": 25,
    "org_inbox": 18,
    "press_office": 18,
    "substack": 16,
    "bluesky": 14,
    "contact_form": 10,
    "x": 8,
    "linkedin": 6,
    "submission_form": 0,
    "github": 0,
}
WAVE1_SEGMENTS = {"journalists_uk", "newsletters", "osint"}
# wave 1 measures both lead segments: 30 journalists + 20 newsletter/OSINT writers.
WAVE1_QUOTA = {"journalists": 30, "writers": 20}
WAVE1_PER_ORG_CAP = 3  # wave 1 measures segments, not one outlet
# Contested-voice rows the newsletter collector flagged for the founder's call (2026-09-10).
# They are held, never auto-scheduled; the founder clears them by setting status back to queued.
FOUNDER_CALL_NAMES = (
    "matt goodwin",
    "alex berenson",
    "steve kirsch",
    "robert malone",
    "john campbell",
    "norman fenton",
    "clare craig",
)
DAILY_CAP = 25
PER_ORG_CAP = 2

CHANNEL_HOW = {
    "email": "email from the sending mailbox",
    "org_inbox": "email to the organisation inbox, marked 'For <name> —'",
    "press_office": "email to the press office, marked 'For <name> —'",
    "substack": "subscribe (free), then reply to a newsletter email or Substack DM",
    "bluesky": "Bluesky DM (follow first if DMs are followers-only)",
    "x": "X DM (or reply if DMs closed)",
    "contact_form": "website contact form, opening 'For <name> —'",
    "linkedin": "LinkedIn message (connection note if not connected)",
    "submission_form": "directory / listing submission form",
    "github": "GitHub issue or PR on the listed repository",
}

# (allowed weekdays as Mon=0..Sun=6, time window) per route; US email in UK afternoon.
SLOT = {
    "email": ((1, 2, 3, 0, 4), "09:30-11:00"),
    "org_inbox": ((1, 2, 3, 0, 4), "09:30-11:00"),
    "press_office": ((1, 2, 3, 0, 4), "09:30-11:00"),
    "substack": ((0, 1, 2, 3), "12:00-14:00"),
    "bluesky": ((0, 1, 2, 3), "12:00-14:00 or 17:00-18:30"),
    "x": ((0, 1, 2, 3), "12:00-14:00 or 17:00-18:30"),
    "contact_form": ((0, 1, 2, 3), "10:00-12:00"),
    "linkedin": ((1, 2, 3), "08:30-09:30"),
    "submission_form": ((0, 1, 2, 3), "10:00-12:00"),
    "github": ((0, 1, 2, 3), "10:00-12:00"),
}
US_EMAIL_TIME = "09:00-10:30 local (14:00-15:30 UK)"

MONTHS = {
    m: i
    for i, m in enumerate(
        [
            "jan",
            "feb",
            "mar",
            "apr",
            "may",
            "jun",
            "jul",
            "aug",
            "sep",
            "oct",
            "nov",
            "dec",
        ],
        1,
    )
}
DATE_RE = re.compile(
    r"\b(\d{1,2})\s+([A-Za-z]{3})[a-z]*\.?\s+(20\d\d)\b|\b([A-Za-z]{3})[a-z]*\.?\s+(20\d\d)\b"
)


def rid_for(route: str) -> str:
    return hashlib.sha1(route.strip().lower().encode("utf-8")).hexdigest()[:10]


def topic_date(text: str) -> date | None:
    """Most recent date mentioned in current_topic, or None."""
    best: date | None = None
    for m in DATE_RE.finditer(text or ""):
        try:
            if m.group(1):
                d = date(
                    int(m.group(3)), MONTHS[m.group(2).lower()[:3]], int(m.group(1))
                )
            else:
                d = date(int(m.group(5)), MONTHS[m.group(4).lower()[:3]], 1)
        except (KeyError, ValueError):
            continue
        if best is None or d > best:
            best = d
    return best


def freshness_points(text: str, today: date) -> int:
    d = topic_date(text)
    if d is None:
        return 0
    age = (today - d).days
    if age <= 14:
        return 25
    if age <= 30:
        return 15
    if age <= 60:
        return 8
    return 0


def priority(row: dict, today: date) -> int:
    p = SEGMENT_WEIGHT.get(row["segment"], 10)
    p += ROUTE_WEIGHT.get(row["route_type"], 0)
    p += freshness_points(row["current_topic"], today)
    if row.get("review_flags"):
        p -= 15
    return max(0, min(100, p))


def src_tag(row: dict) -> str:
    base = re.sub(
        r"[^a-z0-9]+", "-", (row["name"] or row["organisation"]).lower()
    ).strip("-")
    return f"o-{base[:24]}"


def next_day(after: date, allowed: tuple[int, ...]) -> date:
    d = after
    while d.weekday() not in allowed:
        d += timedelta(days=1)
    return d


def assign_waves(rows: list[dict]) -> None:
    """Wave 1 = the highest-priority queued rows in the lead segments up to WAVE1_QUOTA
    (30 journalists + 20 writers); the rest of those segments wave 2; every other
    segment wave 3 (waits for the wave-1 verdict)."""
    queued = [r for r in rows if r["status"] == "queued"]
    queued.sort(key=lambda r: (-int(r["priority"]), r["country"] != "UK", r["name"]))
    taken: Counter = Counter()
    per_org: Counter = Counter()
    for r in queued:
        if r["segment"] not in WAVE1_SEGMENTS:
            r["wave"] = "3"
            continue
        bucket = "journalists" if r["segment"] == "journalists_uk" else "writers"
        org = (r["organisation"] or r["name"]).strip().lower()
        if taken[bucket] < WAVE1_QUOTA[bucket] and per_org[org] < WAVE1_PER_ORG_CAP:
            taken[bucket] += 1
            per_org[org] += 1
            r["wave"] = "1"
        else:
            r["wave"] = "2"


def schedule(rows: list[dict], start: date) -> None:
    """Assign approach_day / time to queued wave-1 and wave-2 rows, wave 1 first,
    respecting the daily and per-organisation caps. Wave 3 carries no day yet."""
    queued = [r for r in rows if r["status"] == "queued"]
    queued.sort(key=lambda r: (int(r["wave"] or 9), -int(r["priority"]), r["country"] != "UK", r["name"]))
    day_count: Counter = Counter()
    org_count: dict[str, Counter] = defaultdict(Counter)
    for r in queued:
        if r["wave"] not in ("1", "2"):
            r["approach_day"] = ""
            r["approach_time_local"] = ""
            continue
        allowed, window = SLOT.get(r["route_type"], ((0, 1, 2, 3), "10:00-12:00"))
        d = next_day(start, allowed)
        org = (r["organisation"] or r["name"]).strip().lower()
        while day_count[d] >= DAILY_CAP or org_count[d][org] >= PER_ORG_CAP:
            d = next_day(d + timedelta(days=1), allowed)
        day_count[d] += 1
        org_count[d][org] += 1
        r["approach_day"] = d.isoformat()
        if r["route_type"] in ("email", "org_inbox", "press_office") and r["country"] == "US":
            r["approach_time_local"] = US_EMAIL_TIME
        else:
            r["approach_time_local"] = window


def load_master() -> list[dict]:
    with MASTER.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_queue() -> dict[str, dict]:
    if not QUEUE.exists():
        return {}
    with QUEUE.open(encoding="utf-8", newline="") as f:
        return {r["rid"]: r for r in csv.DictReader(f)}


def build(start: date, today: date) -> list[dict]:
    existing = load_queue()
    out: list[dict] = []
    for m in load_master():
        rid = rid_for(m["route"])
        row = {c: "" for c in COLS}
        row.update({c: m.get(c, "") for c in MASTER_COLS})
        row["rid"] = rid
        prev = existing.get(rid)
        if prev:
            for c in STATE_COLS + PLAN_COLS:
                row[c] = prev.get(c, "")
        if not row["status"]:
            row["status"] = "queued"
            if any(n in row["name"].lower() for n in FOUNDER_CALL_NAMES):
                row["status"] = "held"
                row["held_reason"] = "founder_call_contested_voice"
        if not row["send_channel_how"]:
            row["send_channel_how"] = CHANNEL_HOW.get(row["route_type"], "").replace(
                "<name>", row["name"]
            )
        if not row["src_tag"]:
            row["src_tag"] = src_tag(row)
        if row["status"] == "queued":
            row["priority"] = str(priority(row, today))
        row["updated_on"] = row["updated_on"] or today.isoformat()
        out.append(row)
    assign_waves(out)
    schedule(out, start)
    return out


def write(rows: list[dict]) -> None:
    with QUEUE.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)


def report(rows: list[dict]) -> None:
    print(f"{len(rows)} rows in {QUEUE.relative_to(ROOT)}")
    print("status:", dict(Counter(r["status"] for r in rows)))
    print("wave:  ", dict(sorted(Counter(r["wave"] for r in rows).items())))
    w1 = [r for r in rows if r["wave"] == "1"]
    print("wave 1 by segment:", dict(Counter(r["segment"] for r in w1)))
    print("wave 1 by route:  ", dict(Counter(r["route_type"] for r in w1)))
    print(
        "wave 1 by day:    ",
        dict(sorted(Counter(r["approach_day"] for r in w1).items())),
    )
    print("wave 1 flagged:   ", sum(1 for r in w1 if r["review_flags"]))
    print(
        "wave 1 topic dated <=30d:",
        sum(1 for r in w1 if freshness_points(r["current_topic"], date.today()) >= 15),
    )


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--start",
        default=None,
        help="first send day (ISO); default next Monday or today if Monday-Thursday",
    )
    ap.add_argument(
        "--report",
        action="store_true",
        help="print counts from the existing queue; write nothing",
    )
    args = ap.parse_args()
    today = date.today()
    if args.report and QUEUE.exists():
        report(list(load_queue().values()))
        return 0
    if args.start:
        start = datetime.strptime(args.start, "%Y-%m-%d").date()
    else:
        start = (
            today
            if today.weekday() <= 3
            else today + timedelta(days=7 - today.weekday())
        )
    rows = build(start, today)
    write(rows)
    report(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
