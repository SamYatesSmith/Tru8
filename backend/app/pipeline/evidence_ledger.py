"""
Evidence Loss Ledger — PR 0 observability artifact.

Pure instrumentation. Does NOT change any pipeline scoring or filtering logic.
Activated by DEBUG_EVIDENCE_LEDGER=1 environment variable.

Produces a structured JSON artifact per check run with evidence_in/out
counts per stage, exclusion reasons, and corruption indicators.
"""
import json
import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

LEDGER_ENABLED = os.environ.get("DEBUG_EVIDENCE_LEDGER", "0") == "1"


class EvidenceLedger:
    """Accumulates evidence pipeline metrics for a single check run."""

    def __init__(self, check_id: str):
        self.check_id = check_id
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.stages: Dict[str, Any] = {}
        self.per_claim: Dict[str, Dict[str, Any]] = {}

    def record(self, stage: str, **kwargs):
        """Record metrics for a pipeline stage."""
        self.stages[stage] = kwargs

    def record_claim(self, claim_pos: str, stage: str, **kwargs):
        """Record per-claim metrics."""
        if claim_pos not in self.per_claim:
            self.per_claim[claim_pos] = {}
        self.per_claim[claim_pos][stage] = kwargs

    def to_dict(self) -> dict:
        retrieve_in = self.stages.get("retrieve", {}).get("total", 0)
        judge_in = self.stages.get("judge_input", {}).get("total", 0)
        snippet_fb = self.stages.get("judge_input", {}).get("snippet_fallbacks", 0)
        return {
            "check_id": self.check_id,
            "timestamp": self.timestamp,
            "summary": {
                "evidence_entered_pipeline": retrieve_in,
                "evidence_reached_judge": judge_in,
                "total_dropped": max(0, retrieve_in - judge_in),
                "snippet_fallbacks_at_judge": snippet_fb,
            },
            "stages": self.stages,
            "per_claim": self.per_claim,
        }

    def save(self) -> str:
        """Write ledger JSON to backend/data/ledger/{check_id}.json."""
        out_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "data", "ledger"
        )
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, f"{self.check_id}.json")
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2, default=str)
        logger.info(f"[LEDGER] Saved evidence ledger to {path}")
        return path


def get_ledger(check_id: str) -> Optional[EvidenceLedger]:
    """Create a ledger if DEBUG_EVIDENCE_LEDGER=1, else return None."""
    if LEDGER_ENABLED:
        logger.info(f"[LEDGER] Evidence Loss Ledger ENABLED for check {check_id}")
        return EvidenceLedger(check_id)
    return None
