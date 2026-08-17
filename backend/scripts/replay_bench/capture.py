"""Parse structured pipeline log lines into a single Observation dict.

Attached as a logging.Handler so we capture only this bench run's output,
not concurrent pipelines. After the pipeline completes, .observation()
returns a dict shaped to match golden.json's assertion vocabulary.
"""

from __future__ import annotations

import ast
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse


# ---------- regexes ----------

RE_CLASSIFIER_INJECT = re.compile(
    r"\[CLASSIFICATION INJECT\]\s+"
    r"primary=(?P<primary>\S+)\s+"
    r"entity_derived=(?P<entity_derived>\[[^\]]*\])\s+"
    r"added=(?P<added>\[[^\]]*\])\s+"
    r"removed=(?P<removed>\[[^\]]*\])\s+"
    r"final_secondaries=(?P<final_secondaries>\[[^\]]*\])\s+"
    r"jurisdiction=(?P<jur_from>\S+)->(?P<jur_to>\S+)"
)

RE_FRESHNESS_INJECT = re.compile(
    r"\[FRESHNESS INJECT\]\s+claim=(?P<claim>\d+)\s+"
    r"max_year=(?P<max_year>\d+)\s+current_year=(?P<current_year>\d+)\s+"
    r"'(?P<from>[^']+)'->'(?P<to>[^']+)'"
)

RE_FINAL_ADAPTERS = re.compile(
    r"\[API DEBUG\] Final adapters to query:\s+(?P<adapters>\[[^\]]*\])"
)

RE_TIER_CAP = re.compile(
    r"\[TIER CAP\] domain=(?P<domain>\S+) cap=(?P<cap>\d+)\s+"
    r"\|\s+(?P<n_in>\d+) adapters → (?P<n_out>\d+):\s+"
    r"selected (?P<selected>\[[^\]]*\]),\s+"
    r"cap victims (?P<victims>\[[^\]]*\])"
)

RE_URL_LEDGER_KEPT = re.compile(
    r"\[URL LEDGER\] claim=(?P<claim>\d+)\s+kept\s+type=(?P<type>\S+)\s+"
    r"provider=(?P<provider>\S+)\s+url=(?P<url>\S+)"
)

RE_SCORER_AUDIT = re.compile(
    r"\[SCORER AUDIT\] claim=(?P<claim>\d+)\s+(?P<verdict>kept|excluded)\s+"
    r"score=(?P<score>\d+)\s+url=(?P<url>\S+)"
)

RE_LLM_SCORER_SUMMARY = re.compile(
    r"\[LLM SCORER\] Scored (?P<scored>\d+)/(?P<total>\d+) items,\s+"
    r"excluded (?P<excluded>\d+).*?keeping (?P<keeping>\d+)"
)

RE_CLASSIFIER_OVERRIDE = re.compile(
    r"\[CLASSIFIER OVERRIDE\]\s+(?P<url>\S+):\s+"
    r"LLM=(?P<llm_tier>\S+)/(?P<llm_type>\S+)\s+→\s+"
    r"(?P<final_tier>\S+)/(?P<final_type>\S+)"
)

RE_TIER_DIST = re.compile(
    r"\[EVIDENCE_CLASSIFIER\] Classification complete:.*?"
    r"Tiers:\s+(?P<tiers>\{[^}]+\}).*?Types:\s+(?P<types>\{[^}]+\})"
)

RE_ANALYZER_INPUT = re.compile(
    r"\[ANALYZER INPUT\] Final evidence:\s+(?P<items>\d+) items,\s+"
    r"(?P<urls>\d+) unique URLs,\s+(?P<domains>\d+) domains"
)

RE_DOMAIN_DIST = re.compile(
    r"\[ANALYZER INPUT\] Domain distribution:\s+(?P<dist>\{.*\})"
)

RE_B3_RECEIPTS = re.compile(
    r"\[B3 RECEIPTS\] shown=(?P<shown>\d+) unmapped=(?P<unmapped>\d+) "
    r"excluded=(?P<excluded>\d+)"
)

RE_PIPELINE_METRICS = re.compile(
    r"\[PIPELINE METRICS\] check=\S+ mode=\S+ "
    r"llm_calls=(?P<llm_calls>\d+) web_search=(?P<web_search>\d+) "
    r"api_adapters=(?P<api_adapters>\d+).*?"
    r"claims=(?P<claims>\d+) elements=(?P<elements>\d+) "
    r"sources_considered=(?P<sources_considered>\d+) "
    r"sources_included=(?P<sources_included>\d+)"
)

RE_COVERAGE_RECOVERY_FAIL = re.compile(
    r"\[COVERAGE RECOVERY\] Search failed for element"
)

RE_COVERAGE_RECOVERY_DONE = re.compile(
    r"\[COVERAGE RECOVERY\] Complete:\s+(?P<recovered>\d+) claims recovered,\s+"
    r"(?P<resolved>\d+) elements resolved"
)

RE_ALLOWLIST_BYPASS = re.compile(r"\[ALLOWLIST BYPASS\] (?P<domain>\S+)\s+—")

# V1 Step 5 — V3 quality signals per claim.
# Emitted in runner.py after [B3 RECEIPTS] / [DOMAIN CAP], format:
#   [B3 QUALITY] claim=N mapped=M unique_domains=K top_domain=X@Y% wikipedia=Z%
#   factual_weight=W% element_resolution=R% tier_mix={...} type_mix={...}
RE_B3_QUALITY = re.compile(
    r"\[B3 QUALITY\]\s+claim=(?P<claim>\d+)\s+"
    r"mapped=(?P<mapped>\d+)\s+"
    r"unique_domains=(?P<unique_domains>\d+)\s+"
    r"top_domain=(?P<top_domain>[^@\s]+)@(?P<top_share>\d+)%\s+"
    r"wikipedia=(?P<wikipedia>\d+)%\s+"
    r"factual_weight=(?P<factual_weight>\d+)%\s+"
    r"element_resolution=(?P<element_resolution>\d+)%\s+"
    r"tier_mix=(?P<tier_mix>\{[^}]*\})\s+"
    r"type_mix=(?P<type_mix>\{[^}]*\})"
)

# Per-claim domain concentration cap demote line:
#   [DOMAIN CAP] claim=N domain=X pre_pr_share=P% post_pr_share=Q% demoted=D
RE_DOMAIN_CAP_DEMOTE = re.compile(
    r"\[DOMAIN CAP\]\s+claim=(?P<claim>\d+)\s+domain=(?P<domain>\S+)\s+"
    r"pre_pr_share=(?P<pre>\d+)%\s+post_pr_share=(?P<post>\d+)%\s+"
    r"demoted=(?P<demoted>\d+)"
)

# Per-run aggregate cap summary:
#   [DOMAIN CAP] total demoted across all claims: N
RE_DOMAIN_CAP_TOTAL = re.compile(
    r"\[DOMAIN CAP\] total demoted across all claims:\s+(?P<total>\d+)"
)

# Coverage recovery hit its async timeout (emitted at WARNING level):
#   [COVERAGE RECOVERY] Timed out after Ns
RE_COVERAGE_RECOVERY_TIMEOUT = re.compile(
    r"\[COVERAGE RECOVERY\]\s+Timed out after (?P<seconds>\d+)s"
)

# F1 temporal scope gate fired on an element (2026-08-06):
#   [TEMPORAL SCOPE] elem=e1: 3 ref(s) scoped to context — element pins 2024-09
#
# WHY THIS IS OBSERVED AT ALL. The gate shipped, passed the bench at 135/2/1 and
# had fired ZERO times — the corpus contained no month-pinned claim, so the drift
# guard was blind to the only class the gate acts on. A fixture alone would not
# have fixed that: without this matcher the bench cannot see the gate, so a change
# that silently stopped it firing would still show green.
#
# The em dash is literal in the log line; the count is matched before it.
RE_TEMPORAL_SCOPE = re.compile(
    r"\[TEMPORAL SCOPE\]\s+elem=(?P<element>\S+?):\s+(?P<scoped>\d+)\s+ref\(s\)\s+"
    r"scoped to context\s+\S+\s+element pins (?P<period>\d{4}-\d{2})"
)

# The four OTHER scope gates (Phase A, 2026-08-17). All five gates share one
# driver (`claim_map_analyzer._apply_scope_gates`) and emit an identically
# shaped line differing only in label and pins text:
#   [JURISDICTION SCOPE] elem=e2: 1 ref(s) scoped to context — claim pins GB
#   [MEASURE SCOPE] elem=e1: 2 ref(s) scoped to context — element measures ...
#   [INTERESTED PARTY] elem=e4: 2 ref(s) scoped to context — claim subjects: ...
#   [RECITAL] elem=e4: 4 ref(s) scoped to context — reference rests on ...
#
# WHY: the bench watched only [TEMPORAL SCOPE], so the other four gates had
# receipts but no drift signal — a change that silently stopped one firing
# would still show green (the exact blindness F1's matcher exists to prevent,
# recorded as interaction I-6 of the 2026-08-14 design review). One generic
# matcher keyed on label; TEMPORAL SCOPE deliberately excluded — it keeps its
# own matcher and golden vocabulary untouched.
#
# Keys mirror the basis receipt keys (`_SCOPE_RECEIPT_KEYS`), so a golden
# assertion and a basis receipt name the same gate the same way.
RE_SCOPE_GATE = re.compile(
    r"\[(?P<label>JURISDICTION SCOPE|MEASURE SCOPE|INTERESTED PARTY|RECITAL|ECHO)\]\s+"
    r"elem=(?P<element>\S+?):\s+(?P<scoped>\d+)\s+ref\(s\)\s+scoped to context"
)

SCOPE_GATE_KEYS = {
    "JURISDICTION SCOPE": "jurisdiction_scope",
    "MEASURE SCOPE": "measure_scope",
    "INTERESTED PARTY": "interested_party",
    "RECITAL": "recital_scope",
    "ECHO": "echo_scope",
}

RE_FACTCHECKS = re.compile(
    r"Found (?P<count>\d+) fact-checks for claim position (?P<position>\d+)"
)

RE_ARTICLE_CLASSIFIED = re.compile(
    r"Article classified via Google Gemini:\s+(?P<domain>\S+)\s+\(confidence"
)


def _parse_list(s: str) -> List[str]:
    """Parse a Python-repr list like "['a', 'b']" into a real list."""
    try:
        v = ast.literal_eval(s)
        return list(v) if isinstance(v, (list, tuple)) else []
    except Exception:
        return []


def _parse_dict(s: str) -> Dict[str, Any]:
    try:
        v = ast.literal_eval(s)
        return dict(v) if isinstance(v, dict) else {}
    except Exception:
        return {}


@dataclass
class Observation:
    """All structured signals captured from a single pipeline run."""

    classifier_inject: Optional[Dict[str, Any]] = None
    article_classification: Optional[str] = None
    freshness_inject_per_claim: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    factchecks_per_claim: Dict[int, int] = field(default_factory=dict)
    final_adapter_set: List[str] = field(default_factory=list)
    tier_caps: List[Dict[str, Any]] = field(default_factory=list)
    url_ledger_per_claim: Dict[int, List[str]] = field(
        default_factory=lambda: defaultdict(list)
    )
    scorer_kept_per_claim: Dict[int, int] = field(
        default_factory=lambda: defaultdict(int)
    )
    scorer_excluded_per_claim: Dict[int, int] = field(
        default_factory=lambda: defaultdict(int)
    )
    scorer_summary: Optional[Dict[str, int]] = None
    classifier_overrides: List[Dict[str, str]] = field(default_factory=list)
    tier_distribution: Dict[str, int] = field(default_factory=dict)
    type_distribution: Dict[str, int] = field(default_factory=dict)
    analyzer_summary: Optional[Dict[str, int]] = None
    domain_distribution: Dict[str, int] = field(default_factory=dict)
    b3_receipts: Optional[Dict[str, int]] = None
    pipeline_metrics: Optional[Dict[str, int]] = None
    coverage_recovery_failures: int = 0
    coverage_recovery_done: Optional[Dict[str, int]] = None
    coverage_recovery_timed_out: bool = False
    coverage_recovery_timeout_seconds: Optional[int] = None
    allowlist_bypassed_domains: Set[str] = field(default_factory=set)
    # V1 Step 5 — V3 per-claim quality signals from [B3 QUALITY] log line.
    # Percentages stored as floats in 0.0-1.0 range.
    b3_quality_per_claim: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    # Per-claim DOMAIN CAP demote events. Shape per entry:
    #   {"claim": int, "domain": str, "pre_pr_share": float,
    #    "post_pr_share": float, "demoted": int}
    domain_cap_events: List[Dict[str, Any]] = field(default_factory=list)
    domain_cap_total: int = 0
    # F1 temporal scope gate events (2026-08-06). Shape per entry:
    #   {"element": str, "scoped": int, "period": "YYYY-MM"}
    temporal_scope_events: List[Dict[str, Any]] = field(default_factory=list)
    # The four other scope gates (2026-08-17), keyed by basis receipt key
    # (jurisdiction_scope / measure_scope / interested_party / recital_scope).
    # Shape per entry: {"element": str, "scoped": int}
    scope_gate_events: Dict[str, List[Dict[str, Any]]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "classifier_inject": self.classifier_inject,
            "article_classification": self.article_classification,
            "freshness_inject_per_claim": {
                str(k): v for k, v in self.freshness_inject_per_claim.items()
            },
            "factchecks_per_claim": {
                str(k): v for k, v in self.factchecks_per_claim.items()
            },
            "final_adapter_set": sorted(self.final_adapter_set),
            "tier_caps": self.tier_caps,
            "url_ledger_per_claim": {
                str(k): list(v) for k, v in self.url_ledger_per_claim.items()
            },
            "url_ledger_flat": sorted(
                {u for urls in self.url_ledger_per_claim.values() for u in urls}
            ),
            "scorer_kept_per_claim": {
                str(k): v for k, v in self.scorer_kept_per_claim.items()
            },
            "scorer_excluded_per_claim": {
                str(k): v for k, v in self.scorer_excluded_per_claim.items()
            },
            "scorer_summary": self.scorer_summary,
            "classifier_overrides": self.classifier_overrides,
            "tier_distribution": self.tier_distribution,
            "type_distribution": self.type_distribution,
            "analyzer_summary": self.analyzer_summary,
            "domain_distribution": self.domain_distribution,
            "domain_set": sorted(self.domain_distribution.keys()),
            "b3_receipts": self.b3_receipts,
            "pipeline_metrics": self.pipeline_metrics,
            "coverage_recovery_failures": self.coverage_recovery_failures,
            "coverage_recovery_done": self.coverage_recovery_done,
            "coverage_recovery_timed_out": self.coverage_recovery_timed_out,
            "coverage_recovery_timeout_seconds": self.coverage_recovery_timeout_seconds,
            "allowlist_bypassed_domains": sorted(self.allowlist_bypassed_domains),
            "b3_quality_per_claim": {
                str(k): v for k, v in self.b3_quality_per_claim.items()
            },
            "domain_cap_events": self.domain_cap_events,
            "domain_cap_total": self.domain_cap_total,
            "temporal_scope_events": self.temporal_scope_events,
            # Summary so a tolerant counter can address it by path. `elements` is
            # how many elements the gate acted on, `scoped_refs` how many
            # relationships it re-labelled in total.
            "temporal_scope_summary": {
                "elements": len(self.temporal_scope_events),
                "scoped_refs": sum(
                    int(e.get("scoped", 0)) for e in self.temporal_scope_events
                ),
            },
        }
        # The four other gates get the same events + summary vocabulary as
        # temporal, flat and per-gate, so goldens address them identically
        # (`<key>_events`, `<key>_summary.scoped_refs`). A gate that never
        # fired reads as a zero, not a missing key.
        for key in SCOPE_GATE_KEYS.values():
            events = list(self.scope_gate_events.get(key, []))
            d[f"{key}_events"] = events
            d[f"{key}_summary"] = {
                "elements": len(events),
                "scoped_refs": sum(int(e.get("scoped", 0)) for e in events),
            }
        return d


class PipelineCaptureHandler(logging.Handler):
    """Logging handler that parses pipeline log messages into an Observation.

    Attach to root before the pipeline runs, detach when done. Then call
    .observation() to get the structured result.
    """

    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.obs = Observation()

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        try:
            msg = record.getMessage()
        except Exception:
            return
        self._dispatch(msg)

    def observation(self) -> Observation:
        return self.obs

    # ---- dispatch helpers (one matcher per signal) ----

    def _dispatch(self, msg: str) -> None:
        for matcher in self._matchers:
            matcher(self, msg)

    def _match_classifier_inject(self, msg: str) -> None:
        m = RE_CLASSIFIER_INJECT.search(msg)
        if not m:
            return
        self.obs.classifier_inject = {
            "primary": m.group("primary"),
            "entity_derived": _parse_list(m.group("entity_derived")),
            "added": _parse_list(m.group("added")),
            "removed": _parse_list(m.group("removed")),
            "final_secondaries": _parse_list(m.group("final_secondaries")),
            "jurisdiction_from": m.group("jur_from"),
            "jurisdiction_to": m.group("jur_to"),
        }

    def _match_article_classification(self, msg: str) -> None:
        m = RE_ARTICLE_CLASSIFIED.search(msg)
        if m and not self.obs.article_classification:
            self.obs.article_classification = m.group("domain")

    def _match_freshness_inject(self, msg: str) -> None:
        m = RE_FRESHNESS_INJECT.search(msg)
        if not m:
            return
        self.obs.freshness_inject_per_claim[int(m.group("claim"))] = {
            "fired": True,
            "max_year": int(m.group("max_year")),
            "current_year": int(m.group("current_year")),
            "from": m.group("from"),
            "to": m.group("to"),
        }

    def _match_factchecks(self, msg: str) -> None:
        m = RE_FACTCHECKS.search(msg)
        if not m:
            return
        self.obs.factchecks_per_claim[int(m.group("position"))] = int(m.group("count"))

    def _match_final_adapters(self, msg: str) -> None:
        m = RE_FINAL_ADAPTERS.search(msg)
        if not m:
            return
        adapters = _parse_list(m.group("adapters"))
        if adapters and not self.obs.final_adapter_set:
            self.obs.final_adapter_set = adapters

    def _match_tier_cap(self, msg: str) -> None:
        m = RE_TIER_CAP.search(msg)
        if not m:
            return
        rec = {
            "domain": m.group("domain"),
            "cap": int(m.group("cap")),
            "n_in": int(m.group("n_in")),
            "n_out": int(m.group("n_out")),
            "selected": _parse_list(m.group("selected")),
            "victims": _parse_list(m.group("victims")),
        }
        if rec not in self.obs.tier_caps:
            self.obs.tier_caps.append(rec)

    def _match_url_ledger(self, msg: str) -> None:
        m = RE_URL_LEDGER_KEPT.search(msg)
        if not m:
            return
        claim = int(m.group("claim"))
        url = m.group("url")
        if url not in self.obs.url_ledger_per_claim[claim]:
            self.obs.url_ledger_per_claim[claim].append(url)

    def _match_scorer_audit(self, msg: str) -> None:
        m = RE_SCORER_AUDIT.search(msg)
        if not m:
            return
        claim = int(m.group("claim"))
        if m.group("verdict") == "kept":
            self.obs.scorer_kept_per_claim[claim] += 1
        else:
            self.obs.scorer_excluded_per_claim[claim] += 1

    def _match_scorer_summary(self, msg: str) -> None:
        m = RE_LLM_SCORER_SUMMARY.search(msg)
        if not m:
            return
        self.obs.scorer_summary = {
            "scored": int(m.group("scored")),
            "total": int(m.group("total")),
            "excluded": int(m.group("excluded")),
            "keeping": int(m.group("keeping")),
        }

    def _match_classifier_override(self, msg: str) -> None:
        m = RE_CLASSIFIER_OVERRIDE.search(msg)
        if not m:
            return
        self.obs.classifier_overrides.append(
            {
                "url_prefix": m.group("url"),
                "from_tier": m.group("llm_tier"),
                "from_type": m.group("llm_type"),
                "to_tier": m.group("final_tier"),
                "to_type": m.group("final_type"),
            }
        )

    def _match_tier_dist(self, msg: str) -> None:
        m = RE_TIER_DIST.search(msg)
        if not m:
            return
        self.obs.tier_distribution = {
            k: int(v) for k, v in _parse_dict(m.group("tiers")).items()
        }
        self.obs.type_distribution = {
            k: int(v) for k, v in _parse_dict(m.group("types")).items()
        }

    def _match_analyzer(self, msg: str) -> None:
        m = RE_ANALYZER_INPUT.search(msg)
        if m:
            self.obs.analyzer_summary = {
                "items": int(m.group("items")),
                "urls": int(m.group("urls")),
                "domains": int(m.group("domains")),
            }
            return
        m2 = RE_DOMAIN_DIST.search(msg)
        if m2:
            self.obs.domain_distribution = {
                str(k): int(v) for k, v in _parse_dict(m2.group("dist")).items()
            }

    def _match_b3_receipts(self, msg: str) -> None:
        m = RE_B3_RECEIPTS.search(msg)
        if not m:
            return
        self.obs.b3_receipts = {
            "shown": int(m.group("shown")),
            "unmapped": int(m.group("unmapped")),
            "excluded": int(m.group("excluded")),
        }

    def _match_pipeline_metrics(self, msg: str) -> None:
        m = RE_PIPELINE_METRICS.search(msg)
        if not m:
            return
        self.obs.pipeline_metrics = {
            "llm_calls": int(m.group("llm_calls")),
            "web_search": int(m.group("web_search")),
            "api_adapters": int(m.group("api_adapters")),
            "claims": int(m.group("claims")),
            "elements": int(m.group("elements")),
            "sources_considered": int(m.group("sources_considered")),
            "sources_included": int(m.group("sources_included")),
        }

    def _match_coverage_recovery(self, msg: str) -> None:
        if RE_COVERAGE_RECOVERY_FAIL.search(msg):
            self.obs.coverage_recovery_failures += 1
            return
        m = RE_COVERAGE_RECOVERY_DONE.search(msg)
        if m:
            self.obs.coverage_recovery_done = {
                "recovered": int(m.group("recovered")),
                "resolved": int(m.group("resolved")),
            }

    def _match_allowlist_bypass(self, msg: str) -> None:
        m = RE_ALLOWLIST_BYPASS.search(msg)
        if m:
            self.obs.allowlist_bypassed_domains.add(m.group("domain"))

    def _match_b3_quality(self, msg: str) -> None:
        m = RE_B3_QUALITY.search(msg)
        if not m:
            return
        claim = int(m.group("claim"))
        self.obs.b3_quality_per_claim[claim] = {
            "mapped": int(m.group("mapped")),
            "unique_domains": int(m.group("unique_domains")),
            "top_domain": m.group("top_domain"),
            "top_domain_share": int(m.group("top_share")) / 100.0,
            "wikipedia_share": int(m.group("wikipedia")) / 100.0,
            "factual_weight_share": int(m.group("factual_weight")) / 100.0,
            "element_resolution": int(m.group("element_resolution")) / 100.0,
            "tier_mix": _parse_dict(m.group("tier_mix")),
            "type_mix": _parse_dict(m.group("type_mix")),
        }

    def _match_domain_cap(self, msg: str) -> None:
        # Match the per-claim demote line first (more specific) before the
        # total summary line — both start with "[DOMAIN CAP]" but only the
        # demote line has claim=/domain=.
        m = RE_DOMAIN_CAP_DEMOTE.search(msg)
        if m:
            self.obs.domain_cap_events.append(
                {
                    "claim": int(m.group("claim")),
                    "domain": m.group("domain"),
                    "pre_pr_share": int(m.group("pre")) / 100.0,
                    "post_pr_share": int(m.group("post")) / 100.0,
                    "demoted": int(m.group("demoted")),
                }
            )
            return
        m2 = RE_DOMAIN_CAP_TOTAL.search(msg)
        if m2:
            self.obs.domain_cap_total = int(m2.group("total"))

    def _match_coverage_recovery_timeout(self, msg: str) -> None:
        m = RE_COVERAGE_RECOVERY_TIMEOUT.search(msg)
        if not m:
            return
        self.obs.coverage_recovery_timed_out = True
        self.obs.coverage_recovery_timeout_seconds = int(m.group("seconds"))

    def _match_temporal_scope(self, msg: str) -> None:
        m = RE_TEMPORAL_SCOPE.search(msg)
        if not m:
            return
        self.obs.temporal_scope_events.append(
            {
                "element": m.group("element"),
                "scoped": int(m.group("scoped")),
                "period": m.group("period"),
            }
        )

    def _match_scope_gate(self, msg: str) -> None:
        m = RE_SCOPE_GATE.search(msg)
        if not m:
            return
        key = SCOPE_GATE_KEYS[m.group("label")]
        self.obs.scope_gate_events[key].append(
            {
                "element": m.group("element"),
                "scoped": int(m.group("scoped")),
            }
        )

    # Order matters only for shared regex prefixes; each matcher is independent.
    _matchers = [
        _match_classifier_inject,
        _match_article_classification,
        _match_freshness_inject,
        _match_factchecks,
        _match_final_adapters,
        _match_tier_cap,
        _match_url_ledger,
        _match_scorer_audit,
        _match_scorer_summary,
        _match_classifier_override,
        _match_tier_dist,
        _match_analyzer,
        _match_b3_receipts,
        _match_pipeline_metrics,
        _match_coverage_recovery,
        _match_coverage_recovery_timeout,
        _match_allowlist_bypass,
        _match_b3_quality,
        _match_domain_cap,
        _match_temporal_scope,
        _match_scope_gate,
    ]
