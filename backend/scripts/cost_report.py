"""What a check costs, recomputed from stored telemetry — and whether it pays.

WHY THIS EXISTS
---------------
Every check since 2026-06-15 stores ``Check.cost_telemetry``, and since
2026-08-03 that blob carries MEASURED search spend: per-provider query and
billable-unit counts from ``app/core/search_meter.py``. Nothing could read it.

That gap mattered. Search is the largest variable cost and was, until the meter
shipped, the one nobody had measured at all. Console sells 200 checks for £20 —
10p of revenue per check — so "is a fully-utilised subscriber profitable?" turns
on a number that has been sitting in the database, unread.

WHAT IT DOES DIFFERENTLY FROM ``check_cost_snapshot.py``
-------------------------------------------------------
That script reads the ``estimated_cost_usd`` frozen into each row at save time,
and predates the meter — its own note says search cost "is not included". This
one RECOMPUTES from the raw tokens and billable units at the price table as it
stands today, which is the stated reason the raw data is stored at all (see the
``cost_constants`` module docstring). Correct a price in ``cost_constants.py``
and every historical check reprices; no backfill, no migration.

WHAT IT CANNOT TELL YOU — read this before quoting any number
-------------------------------------------------------------
1. **LLM cost is PARTIAL.** Only the analyzer, classifier and distiller stages
   report tokens. Extract, the relevance scorer and the query stage do not. So
   every cost below is a FLOOR — and therefore every margin is a CEILING. A
   headroom figure that looks comfortable may not be.
2. **Prices are UNVERIFIED placeholders** (``PRICING_VERSION``), and search is
   priced at Serper's ENTRY tier deliberately: their top tier is ~3.3x cheaper,
   so assuming a volume discount would flatter the estimate. A cost model should
   fail pessimistic.
3. **Checks before 2026-08-03 carry no search meter.** They are reported
   separately and never as zero. A silent zero would read as "search is free",
   which is the opposite of true.
4. **FX is a constant you pass in, not a live rate.** It is printed with every
   run so a stale rate cannot masquerade as a measurement.

Run locally:
    cd backend && python -m scripts.cost_report

Run against production (Railway):
    railway run --service Postgres python -m scripts.cost_report

``--service Postgres`` is REQUIRED: it injects the public TCP-proxy URL. A plain
``railway run`` injects the internal ``*.railway.internal`` host, which does not
resolve from a laptop.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import sys
from collections import Counter
from typing import Any, Dict, List, Optional, Sequence

from app.core.agent_pricing import AGENT_PRICING_PENCE
from app.core.cost_constants import (
    PRICING_VERSION,
    SEARCH_PRICING_USD_PER_UNIT,
    estimate_llm_cost_usd,
    estimate_search_cost_usd,
)

# GBP/USD. Not a live rate and deliberately not fetched — a report that silently
# re-based its own margins between runs would be worse than one that states its
# assumption. Override with --gbp-usd or GBP_USD_RATE.
DEFAULT_GBP_USD = 1.28

# Console: £20/month for 200 checks. The revenue line a per-check cost has to
# clear for a fully-utilised subscriber to be profitable.
CONSOLE_MONTHLY_GBP = 20.0
CONSOLE_CHECKS_PER_MONTH = 200
CONSOLE_REVENUE_PENCE_PER_CHECK = (
    CONSOLE_MONTHLY_GBP * 100 / CONSOLE_CHECKS_PER_MONTH
)  # 10.0p

# The date search metering began. Rows created before it have no billable-unit
# counts and are excluded from every search figure.
METER_LIVE_FROM = "2026-08-03"

ROWS_SQL = """
SELECT
    id,
    created_at,
    COALESCE(status, '(none)')        AS status,
    executed_tier,
    client,
    cost_telemetry
FROM "check"
WHERE cost_telemetry IS NOT NULL
  {window}
ORDER BY created_at DESC
LIMIT :limit
"""


# ---------------------------------------------------------------------------
# Pure computation — no DB, no I/O. Everything below is unit-tested.
# ---------------------------------------------------------------------------


def _percentile(sorted_vals: Sequence[float], q: float) -> Optional[float]:
    """Linear-interpolated percentile of an ALREADY SORTED sequence.

    Written out rather than using ``statistics.quantiles`` because that needs at
    least two data points, and at current volume a window can legitimately hold
    one check. A report that crashes on a quiet week is not a report.
    """
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    k = (len(sorted_vals) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return float(sorted_vals[int(k)])
    return float(sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo))


def _spread(values: List[float]) -> Dict[str, Optional[float]]:
    """avg / median / p90 / min / max for a list of costs."""
    if not values:
        return {
            "n": 0,
            "avg": None,
            "median": None,
            "p90": None,
            "min": None,
            "max": None,
        }
    s = sorted(values)
    return {
        "n": len(s),
        "avg": sum(s) / len(s),
        "median": _percentile(s, 0.5),
        "p90": _percentile(s, 0.9),
        "min": s[0],
        "max": s[-1],
    }


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _section(blob: Any, key: str) -> Dict[str, Any]:
    """A sub-dict of the telemetry blob, or {} if it is missing or malformed.

    ``cost_telemetry`` is JSONB written by a pipeline whose shape has changed
    twice, and a report that dies on one old row is a report nobody runs. Note
    that ``x.get(k) or {}`` is NOT enough — a truthy non-dict (an old row where
    ``llm`` was a string) sails straight through and blows up on ``.get``.
    """
    if not isinstance(blob, dict):
        return {}
    value = blob.get(key)
    return value if isinstance(value, dict) else {}


def row_costs(telemetry: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Recompute one check's cost from its raw telemetry, at today's prices.

    ``search_usd`` is None — never 0.0 — when the row predates metering, so an
    un-instrumented check reports as unknown rather than as free. ``total_usd``
    is None whenever either half is, rather than a misleading partial sum.
    """
    telemetry = telemetry if isinstance(telemetry, dict) else {}
    llm = _section(telemetry, "llm")
    search = _section(telemetry, "search")

    in_tok = _int(llm.get("input_tokens"))
    out_tok = _int(llm.get("output_tokens"))
    think_tok = _int(llm.get("thinking_tokens"))
    by_stage = llm.get("by_stage")
    llm_usd = estimate_llm_cost_usd(in_tok, out_tok, by_stage, thinking_tokens=think_tok)

    units = search.get("billable_units_by_provider")
    metered = isinstance(units, dict)
    search_usd = (
        estimate_search_cost_usd({"billable_units_by_provider": units})
        if metered
        else None
    )

    return {
        "llm_usd": llm_usd,
        "search_usd": search_usd,
        "total_usd": (llm_usd + search_usd) if search_usd is not None else None,
        "metered": metered,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "thinking_tokens": think_tok,
        "llm_calls": _int(llm.get("calls")),
        "by_stage": by_stage if isinstance(by_stage, dict) else {},
        "queries_by_provider": search.get("queries_by_provider") or {},
        "billable_units_by_provider": units or {},
        "total_queries": _int(search.get("total_queries")),
        "total_billable_units": _int(search.get("total_billable_units")),
        "wall_time_ms": _int((telemetry.get("timing") or {}).get("wall_time_ms")),
        "stored_pricing_version": telemetry.get("pricing_version"),
    }


def _stage_cost_usd(stage: Dict[str, Any]) -> float:
    """Cost of one stage, priced at the priciest model that stage used.

    Reuses ``estimate_llm_cost_usd`` with a single-stage map so the per-stage
    figures here and the per-check total cannot drift apart: pass the stage's own
    tokens as the totals and there is no residual to price at the default rate.
    """
    si = _int(stage.get("input_tokens"))
    so = _int(stage.get("output_tokens"))
    return estimate_llm_cost_usd(si, so, {"_": stage})


def build_report(rows: List[Dict[str, Any]], gbp_usd: float) -> Dict[str, Any]:
    """Aggregate per-check costs into the shape the renderer prints.

    ``rows`` are dicts with keys: status, executed_tier, client, cost_telemetry.
    Pure — give it fixtures and it is fully testable without a database.
    """
    costed = [{**r, **row_costs(r.get("cost_telemetry"))} for r in rows]
    metered = [c for c in costed if c["metered"]]

    def to_pence(usd: Optional[float]) -> Optional[float]:
        return None if usd is None else usd / gbp_usd * 100

    llm_pence = [to_pence(c["llm_usd"]) for c in costed]
    search_pence = [to_pence(c["search_usd"]) for c in metered]
    total_pence = [to_pence(c["total_usd"]) for c in metered]

    # Per-stage LLM spend. Answers "where do the tokens actually go?" and, since
    # 2026-08-07, which model each stage really used — the F4b question.
    stages: Dict[str, Dict[str, Any]] = {}
    for c in costed:
        for name, stage in (c["by_stage"] or {}).items():
            if not isinstance(stage, dict):
                continue
            agg = stages.setdefault(
                name,
                {
                    "checks": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "thinking_tokens": 0,
                    "calls": 0,
                    "usd": 0.0,
                    "models": Counter(),
                },
            )
            agg["checks"] += 1
            agg["input_tokens"] += _int(stage.get("input_tokens"))
            agg["output_tokens"] += _int(stage.get("output_tokens"))
            agg["thinking_tokens"] += _int(stage.get("thinking_tokens"))
            agg["calls"] += _int(stage.get("calls"))
            agg["usd"] += _stage_cost_usd(stage)
            models = stage.get("models_used")
            if isinstance(models, dict):
                agg["models"].update(m for m in models.values() if m)
            elif isinstance(models, (list, tuple)):
                agg["models"].update(m for m in models if m)

    stage_usd_total = sum(s["usd"] for s in stages.values()) or 0.0
    stage_rows = sorted(stages.items(), key=lambda kv: kv[1]["usd"], reverse=True)

    # Search providers, over metered rows only.
    queries: Counter = Counter()
    units: Counter = Counter()
    for c in metered:
        for p, n in (c["queries_by_provider"] or {}).items():
            queries[p] += _int(n)
        for p, n in (c["billable_units_by_provider"] or {}).items():
            units[p] += _int(n)

    # Cost by executed tier — does `quick` actually cost less than `full`?
    by_tier: Dict[str, List[float]] = {}
    for c in metered:
        tier = c.get("executed_tier") or "(unset)"
        p = to_pence(c["total_usd"])
        if p is not None:
            by_tier.setdefault(tier, []).append(p)

    status_counts = Counter(c.get("status") or "(none)" for c in costed)
    stored_versions = Counter(
        c.get("stored_pricing_version") or "(none)" for c in costed
    )

    return {
        "gbp_usd": gbp_usd,
        "pricing_version": PRICING_VERSION,
        "counts": {
            "checks_with_telemetry": len(costed),
            "metered_for_search": len(metered),
            "unmetered_for_search": len(costed) - len(metered),
            "by_status": dict(status_counts.most_common()),
            "stored_pricing_versions": dict(stored_versions.most_common()),
        },
        "pence_per_check": {
            "llm_partial": _spread([p for p in llm_pence if p is not None]),
            "search": _spread([p for p in search_pence if p is not None]),
            "total_partial": _spread([p for p in total_pence if p is not None]),
        },
        "stages": [
            {
                "stage": name,
                "usd": s["usd"],
                "share": (s["usd"] / stage_usd_total) if stage_usd_total else 0.0,
                "checks": s["checks"],
                "input_tokens": s["input_tokens"],
                "output_tokens": s["output_tokens"],
                "thinking_tokens": s["thinking_tokens"],
                "calls": s["calls"],
                "models": dict(s["models"].most_common()),
            }
            for name, s in stage_rows
        ],
        "search_providers": [
            {
                "provider": p,
                "queries": queries.get(p, 0),
                "billable_units": units.get(p, 0),
                "usd_per_unit": SEARCH_PRICING_USD_PER_UNIT.get(p),
                "usd": units.get(p, 0) * (SEARCH_PRICING_USD_PER_UNIT.get(p) or 0.0),
            }
            for p in sorted(set(queries) | set(units))
        ],
        "by_tier": {tier: _spread(vals) for tier, vals in sorted(by_tier.items())},
        "margins": _margins(_spread([p for p in total_pence if p is not None])),
    }


def _margins(total_spread: Dict[str, Optional[float]]) -> Dict[str, Any]:
    """Cost against every price we actually charge.

    Uses the MEDIAN, not the mean: a single pathological check (a 40-fetch
    article against a 3-word claim) drags an average somewhere no real check
    lives, and the question here is what a typical check does to the margin.
    """
    median = total_spread.get("median")
    lines = [
        {
            "product": "Console (£20 / 200 checks)",
            "revenue_pence": CONSOLE_REVENUE_PENCE_PER_CHECK,
        }
    ]
    lines += [
        {"product": f"Agent tier: {tier}", "revenue_pence": float(pence)}
        for tier, pence in sorted(AGENT_PRICING_PENCE.items(), key=lambda kv: kv[1])
    ]
    for line in lines:
        rev = line["revenue_pence"]
        if median is None:
            line["headroom_pence"] = None
            line["margin_pct"] = None
        else:
            line["headroom_pence"] = rev - median
            line["margin_pct"] = ((rev - median) / rev * 100) if rev else None
    return {"median_cost_pence": median, "lines": lines}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _p(v: Optional[float], places: int = 3) -> str:
    return f"{v:.{places}f}" if v is not None else "-"


def _spread_line(label: str, s: Dict[str, Optional[float]]) -> str:
    return (
        f"  {label:<16}n={s['n']:<5} avg {_p(s['avg'])}  median {_p(s['median'])}  "
        f"p90 {_p(s['p90'])}  min {_p(s['min'])}  max {_p(s['max'])}"
    )


def render(report: Dict[str, Any]) -> str:
    out: List[str] = []
    c = report["counts"]
    total = report["pence_per_check"]["total_partial"]

    out.append("=== COST PER CHECK — recomputed from raw telemetry ===")
    out.append(
        f"checks with telemetry : {c['checks_with_telemetry']}"
        f"   (search-metered: {c['metered_for_search']}, "
        f"unmetered: {c['unmetered_for_search']})"
    )
    out.append(f"prices                : {report['pricing_version']} (UNVERIFIED)")
    out.append(
        f"GBP/USD assumed       : {report['gbp_usd']}  (constant, not a live rate)"
    )
    if c["unmetered_for_search"]:
        out.append(
            f"note                  : {c['unmetered_for_search']} check(s) predate "
            f"search metering ({METER_LIVE_FROM}) and are excluded from every "
            "search and total figure — not counted as zero."
        )

    out.append("")
    out.append("--- THE QUESTION: does a check pay for itself? ---")
    m = report["margins"]
    if m["median_cost_pence"] is None:
        out.append("  No search-metered checks in this window — cannot answer yet.")
    else:
        out.append(
            f"  median measured cost : {_p(m['median_cost_pence'], 2)}p per check"
        )
        out.append("")
        out.append(f"  {'against':<30}{'revenue':>10}{'headroom':>11}{'margin':>9}")
        out.append(f"  {'-' * 60}")
        for line in m["lines"]:
            out.append(
                f"  {line['product']:<30}{_p(line['revenue_pence'], 2):>9}p"
                f"{_p(line['headroom_pence'], 2):>10}p"
                f"{_p(line['margin_pct'], 1):>8}%"
            )
        out.append("")
        out.append("  ⚠️ Cost is a FLOOR (extract, relevance scorer and the query stage")
        out.append("     report no tokens), so every headroom above is a CEILING.")

    out.append("")
    out.append("--- PENCE PER CHECK ---")
    out.append(_spread_line("llm (partial)", report["pence_per_check"]["llm_partial"]))
    out.append(_spread_line("search", report["pence_per_check"]["search"]))
    out.append(_spread_line("total (partial)", total))

    if report["stages"]:
        out.append("")
        out.append("--- WHERE THE LLM SPEND GOES ---")
        out.append(
            f"  {'stage':<22}{'share':>7}{'USD':>10}{'in tok':>10}{'out tok':>9}"
            f"{'think tok':>11}{'calls':>7}  models"
        )
        out.append(f"  {'-' * 95}")
        for s in report["stages"]:
            models = ", ".join(f"{k}×{v}" for k, v in s["models"].items()) or "-"
            out.append(
                f"  {s['stage']:<22}{s['share'] * 100:>6.1f}%{s['usd']:>10.5f}"
                f"{s['input_tokens']:>10}{s['output_tokens']:>9}"
                f"{s['thinking_tokens']:>11}{s['calls']:>7}  {models}"
            )

    if report["search_providers"]:
        out.append("")
        out.append("--- SEARCH PROVIDERS (metered checks only) ---")
        out.append(
            f"  {'provider':<12}{'queries':>9}{'billable':>10}{'$/unit':>9}{'USD':>10}"
        )
        out.append(f"  {'-' * 50}")
        for p in report["search_providers"]:
            out.append(
                f"  {p['provider']:<12}{p['queries']:>9}{p['billable_units']:>10}"
                f"{_p(p['usd_per_unit'], 4):>9}{p['usd']:>10.4f}"
            )
        q = sum(p["queries"] for p in report["search_providers"])
        u = sum(p["billable_units"] for p in report["search_providers"])
        if u > q:
            out.append(
                f"  billable units exceed queries by {u - q} — Serper charges 2 credits "
                "for 11-100 results,"
            )
            out.append(
                "  and the claim lane asks for 13. Counting queries alone would "
                "understate this."
            )

    if report["by_tier"]:
        out.append("")
        out.append("--- COST BY EXECUTED TIER (pence, metered only) ---")
        for tier, s in report["by_tier"].items():
            out.append(_spread_line(tier, s))

    if c["by_status"]:
        out.append("")
        out.append("--- CHECKS BY STATUS ---")
        for status, n in c["by_status"].items():
            out.append(f"  {status:<24}{n:>6}")
        if any(s in c["by_status"] for s in ("failed", "processing")):
            out.append(
                "  note: a failed check still spent the money it spent before failing,"
            )
            out.append(
                "        and its credit was refunded. Cost is real, revenue is not."
            )

    versions = c["stored_pricing_versions"]
    if len(versions) > 1 or (versions and report["pricing_version"] not in versions):
        out.append("")
        out.append(
            f"note: rows were saved under {len(versions)} pricing version(s) "
            f"({', '.join(versions)}); every figure above is recomputed at "
            f"{report['pricing_version']}."
        )

    return "\n".join(out)


# ---------------------------------------------------------------------------
# DB access + entry point
# ---------------------------------------------------------------------------


async def fetch_rows(
    db_url: str, days: Optional[int], limit: int
) -> List[Dict[str, Any]]:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    window = "AND created_at > now() - make_interval(days => :days)" if days else ""
    params: Dict[str, Any] = {"limit": limit}
    if days:
        params["days"] = days

    engine = create_async_engine(db_url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text(ROWS_SQL.format(window=window)), params)
            return [dict(r._mapping) for r in result]
    finally:
        await engine.dispose()


def resolve_db_url() -> str:
    """Env only — no app config import, so this runs under any Railway service."""
    url = (
        os.environ.get("COST_DB_URL")
        or os.environ.get("DATABASE_PUBLIC_URL")
        or os.environ.get("DATABASE_URL")
        or ""
    )
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


async def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--days", type=int, default=None, help="only checks from the last N days"
    )
    ap.add_argument(
        "--limit", type=int, default=5000, help="max rows to read (default 5000)"
    )
    ap.add_argument(
        "--gbp-usd",
        type=float,
        default=float(os.environ.get("GBP_USD_RATE") or DEFAULT_GBP_USD),
        help=f"GBP/USD rate for the margin table (default {DEFAULT_GBP_USD})",
    )
    ap.add_argument("--json", action="store_true", help="emit the report as JSON")
    args = ap.parse_args(argv)

    db_url = resolve_db_url()
    if not db_url:
        print(
            "No database URL. Set COST_DB_URL, or run:\n"
            "  railway run --service Postgres python -m scripts.cost_report",
            file=sys.stderr,
        )
        return 2

    rows = await fetch_rows(db_url, args.days, args.limit)
    if not rows:
        window = f"the last {args.days} day(s)" if args.days else "any window"
        print(f"No checks with cost telemetry in {window}.")
        return 0

    report = build_report(rows, args.gbp_usd)
    print(json.dumps(report, indent=2, default=str) if args.json else render(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
