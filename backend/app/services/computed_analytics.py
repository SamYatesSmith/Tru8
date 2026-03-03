"""
Pre-computed analytics for agent API responses.

When `?computed=true`, the check response includes a `_computed` block with
all view analytics that the frontend normally derives client-side. This lets
agents consume rich structured data in a single API call without replicating
six different computation paths.

Ported from the following frontend components:
- CartographerView.tsx  → tier grouping, corroboration, convergence, gaps, edges
- LibrarianView.tsx     → heatmap matrix, evidence-element mapping
- InterpreterView.tsx   → disposition grouping per element
- ChronologistView.tsx  → timeline clustering, date range, gap detection
- SeekerView.tsx        → element state counting, coverage
- diagnostic-value.ts   → ACH-inspired diagnostic values
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any
from urllib.parse import urlparse


def compute_analytics(claims_data: list[dict]) -> dict:
    """Build the _computed analytics block from serialized claim data.

    Args:
        claims_data: List of camelCase claim dicts (same shape as API response).
                     Each has claimMap, evidence[], position, etc.

    Returns:
        Dict with summary, evidenceByTier, heatmap, corroboration,
        diagnosticValues, timeline, and perClaim analytics.
    """
    all_evidence = _collect_deduplicated_evidence(claims_data)
    all_elements = _collect_all_elements(claims_data)

    return {
        "summary": _build_summary(claims_data, all_evidence, all_elements),
        "evidenceByTier": _count_by_field(all_evidence, "tier"),
        "evidenceByType": _count_by_field(all_evidence, "evidenceType"),
        "heatmap": _build_heatmap(all_evidence),
        "corroboration": _build_corroboration(all_evidence),
        "diagnosticValues": _compute_diagnostic_values(claims_data),
        "timeline": _build_timeline(all_evidence),
        "freshness": _build_freshness(all_evidence),
        "uniqueDomains": _count_unique_domains(all_evidence),
        "perClaim": [_build_per_claim(c) for c in claims_data],
    }


# ---------------------------------------------------------------------------
# Evidence / element collection
# ---------------------------------------------------------------------------


def _collect_deduplicated_evidence(claims_data: list[dict]) -> list[dict]:
    """Collect unique evidence across all claims by evidenceId."""
    seen: set[str] = set()
    result: list[dict] = []
    for claim in claims_data:
        for ev in claim.get("evidence") or []:
            eid = ev.get("evidenceId") or ev.get("id")
            if eid and eid not in seen:
                seen.add(eid)
                result.append(ev)
    return result


def _collect_all_elements(claims_data: list[dict]) -> list[dict]:
    """Collect all elements across all claims."""
    elements: list[dict] = []
    for claim in claims_data:
        cm = claim.get("claimMap")
        if cm and isinstance(cm.get("elements"), list):
            elements.extend(cm["elements"])
    return elements


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def _build_summary(
    claims_data: list[dict],
    all_evidence: list[dict],
    all_elements: list[dict],
) -> dict:
    states = Counter(el.get("state") or "unresolved" for el in all_elements)
    elements_with_evidence = sum(
        1
        for el in all_elements
        if el.get("evidenceRefs") and len(el["evidenceRefs"]) > 0
    )
    total_elements = len(all_elements)
    coverage = (elements_with_evidence / total_elements * 100) if total_elements else 0

    gap_elements = []
    for claim in claims_data:
        cm = claim.get("claimMap")
        if not cm:
            continue
        for el in cm.get("elements") or []:
            if not el.get("evidenceRefs"):
                gap_elements.append(
                    {
                        "claimPosition": claim.get("position"),
                        "elementId": el.get("elementId"),
                        "text": el.get("text"),
                    }
                )

    return {
        "totalClaims": len(claims_data),
        "totalEvidence": len(all_evidence),
        "totalElements": total_elements,
        "elementStates": {
            "supported": states.get("supported", 0),
            "disputed": states.get("disputed", 0),
            "unresolved": states.get("unresolved", 0),
        },
        "coveragePercent": round(coverage, 1),
        "gapElements": gap_elements,
    }


# ---------------------------------------------------------------------------
# Tier / type counting
# ---------------------------------------------------------------------------


def _count_by_field(evidence_list: list[dict], field: str) -> dict[str, int]:
    counts: dict[str, int] = Counter()
    for ev in evidence_list:
        val = ev.get(field)
        if val:
            counts[val] += 1
    return dict(counts)


# ---------------------------------------------------------------------------
# Heatmap (tier × type matrix)
# ---------------------------------------------------------------------------


def _build_heatmap(evidence_list: list[dict]) -> list[dict]:
    """Count evidence by (tier, type) pair — powers the Librarian heatmap."""
    counts: Counter = Counter()
    for ev in evidence_list:
        tier = ev.get("tier")
        etype = ev.get("evidenceType")
        if tier and etype:
            counts[(tier, etype)] += 1

    return [
        {"tier": tier, "type": etype, "count": count}
        for (tier, etype), count in sorted(counts.items())
    ]


# ---------------------------------------------------------------------------
# Corroboration
# ---------------------------------------------------------------------------


def _build_corroboration(evidence_list: list[dict]) -> dict:
    """Detect corroboration groups and count convergence points."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for ev in evidence_list:
        gid = ev.get("corroborationGroupId")
        if gid:
            groups[gid].append(ev)

    group_data = []
    convergence_count = 0
    for gid, members in groups.items():
        tiers = list({m.get("tier") for m in members if m.get("tier")})
        evidence_ids = [m.get("evidenceId") or m.get("id") for m in members]
        group_data.append(
            {
                "groupId": gid,
                "evidenceIds": evidence_ids,
                "tiers": sorted(tiers),
                "size": len(members),
            }
        )
        if len(members) >= 3:
            convergence_count += 1

    return {
        "groups": group_data,
        "convergenceCount": convergence_count,
    }


# ---------------------------------------------------------------------------
# Diagnostic values (ACH-inspired)
# ---------------------------------------------------------------------------


def _compute_diagnostic_values(claims_data: list[dict]) -> dict:
    """Port of web/lib/diagnostic-value.ts — rates evidence by analytical value.

    Evidence that both supports AND challenges different elements scores 1.0
    (maximally diagnostic). Context-only evidence scores 0.1.
    """
    # Build evidenceId → set of relationships
    evidence_rels: dict[str, set[str]] = defaultdict(set)
    for claim in claims_data:
        cm = claim.get("claimMap")
        if not cm:
            continue
        for el in cm.get("elements") or []:
            for ref in el.get("evidenceRefs") or []:
                eid = ref.get("evidenceId")
                rel = ref.get("relationship", "context")
                if eid:
                    evidence_rels[eid].add(rel)

    values: dict[str, float] = {}
    has_diagnostic_variance = False
    high_count = 0

    for eid, rels in evidence_rels.items():
        if "supports" in rels and "challenges" in rels:
            val = 1.0
            has_diagnostic_variance = True
        elif len(rels) == 1 and "context" in rels:
            val = 0.1
        elif len(rels) == 1:
            val = 0.6
            if "challenges" in rels:
                has_diagnostic_variance = True
        else:
            val = 0.2

        values[eid] = val
        if val > 0.7:
            high_count += 1

    return {
        "hasDiagnosticVariance": has_diagnostic_variance,
        "highCount": high_count,
        "totalCount": len(values),
        "values": values,
    }


# ---------------------------------------------------------------------------
# Timeline
# ---------------------------------------------------------------------------


def _build_timeline(evidence_list: list[dict]) -> dict:
    """Compute timeline metadata — date range, dated/undated split, gap zones."""
    dated: list[tuple[datetime, dict]] = []
    undated_count = 0

    for ev in evidence_list:
        raw = ev.get("publishedDate")
        if raw:
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                dated.append((dt, ev))
            except (ValueError, TypeError):
                undated_count += 1
        else:
            undated_count += 1

    total = len(evidence_list)
    dated_count = len(dated)
    below_threshold = total > 0 and (dated_count / total) < 0.5

    if not dated:
        return {
            "datedCount": 0,
            "undatedCount": undated_count,
            "dateRange": None,
            "belowThreshold": below_threshold,
            "gaps": [],
        }

    dated.sort(key=lambda x: x[0])
    earliest = dated[0][0]
    latest = dated[-1][0]

    # Gap detection: consecutive evidence gaps > 30 days
    gaps: list[dict] = []
    for i in range(1, len(dated)):
        delta = (dated[i][0] - dated[i - 1][0]).days
        if delta > 30:
            gaps.append(
                {
                    "afterDate": dated[i - 1][0].isoformat(),
                    "beforeDate": dated[i][0].isoformat(),
                    "gapDays": delta,
                }
            )

    return {
        "datedCount": dated_count,
        "undatedCount": undated_count,
        "dateRange": {
            "earliest": earliest.isoformat(),
            "latest": latest.isoformat(),
        },
        "belowThreshold": below_threshold,
        "gaps": gaps,
    }


# ---------------------------------------------------------------------------
# Freshness + domain diversity (M-02)
# ---------------------------------------------------------------------------


def _build_freshness(evidence_list: list[dict]) -> dict:
    """Compute freshness metrics from evidence published dates.

    Returns freshestDaysAgo, dateSpanDays, undatedCount.
    Naive datetimes assumed UTC.
    """
    now = datetime.utcnow()
    dated_dts: list[datetime] = []
    undated_count = 0

    for ev in evidence_list:
        raw = ev.get("publishedDate")
        if raw:
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                # Strip timezone for comparison with utcnow
                dated_dts.append(dt.replace(tzinfo=None) if dt.tzinfo else dt)
            except (ValueError, TypeError):
                undated_count += 1
        else:
            undated_count += 1

    if not dated_dts:
        return {
            "freshestDaysAgo": None,
            "dateSpanDays": None,
            "undatedCount": undated_count,
        }

    dated_dts.sort()
    freshest = max(dated_dts)
    oldest = min(dated_dts)
    freshest_days = max(0, (now - freshest).days)
    span_days = max(0, (freshest - oldest).days)

    return {
        "freshestDaysAgo": freshest_days,
        "dateSpanDays": span_days,
        "undatedCount": undated_count,
    }


def _count_unique_domains(evidence_list: list[dict]) -> int:
    """Count unique URL hostnames from evidence, stripping www. prefix."""
    domains: set[str] = set()
    for ev in evidence_list:
        url = ev.get("url", "")
        if url:
            try:
                host = urlparse(url).hostname
                if host:
                    host = host.lower()
                    if host.startswith("www."):
                        host = host[4:]
                    domains.add(host)
            except (ValueError, TypeError):
                pass
    return len(domains)


# ---------------------------------------------------------------------------
# Per-claim analytics
# ---------------------------------------------------------------------------


def _build_per_claim(claim: dict) -> dict:
    """Analytics scoped to a single claim — element states, dispositions, tier counts."""
    cm = claim.get("claimMap")
    elements = (cm.get("elements") or []) if cm else []
    evidence = claim.get("evidence") or []

    # Element states
    states = Counter(el.get("state") or "unresolved" for el in elements)

    # Coverage
    with_evidence = sum(
        1 for el in elements if el.get("evidenceRefs") and len(el["evidenceRefs"]) > 0
    )
    total_el = len(elements)
    coverage = (with_evidence / total_el * 100) if total_el else 0

    # Evidence by tier
    tier_counts = Counter(ev.get("tier") for ev in evidence if ev.get("tier"))

    # Dispositions: per-element grouping of evidence by relationship
    dispositions: dict[str, dict[str, list[str]]] = {}
    for el in elements:
        el_id = el.get("elementId")
        if not el_id:
            continue
        groups: dict[str, list[str]] = {"supports": [], "challenges": [], "context": []}
        for ref in el.get("evidenceRefs") or []:
            eid = ref.get("evidenceId")
            rel = ref.get("relationship", "context")
            if eid and rel in groups:
                groups[rel].append(eid)
        dispositions[el_id] = groups

    return {
        "claimPosition": claim.get("position"),
        "elementCount": total_el,
        "evidenceCount": len(evidence),
        "elementStates": {
            "supported": states.get("supported", 0),
            "disputed": states.get("disputed", 0),
            "unresolved": states.get("unresolved", 0),
        },
        "coveragePercent": round(coverage, 1),
        "evidenceByTier": dict(tier_counts),
        "dispositions": dispositions,
    }
