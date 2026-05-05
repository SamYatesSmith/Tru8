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
    allowlist_bypassed_domains: Set[str] = field(default_factory=set)

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
            "allowlist_bypassed_domains": sorted(self.allowlist_bypassed_domains),
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
        _match_allowlist_bypass,
    ]
