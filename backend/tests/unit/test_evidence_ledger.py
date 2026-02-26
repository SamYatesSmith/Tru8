"""Tests for EvidenceLedger — pure data accumulation, no external deps."""

import json
import os
import pytest
from app.pipeline.evidence_ledger import EvidenceLedger, get_ledger


class TestEvidenceLedgerInit:
    def test_ledger_init(self):
        ledger = EvidenceLedger("chk-123")
        assert ledger.check_id == "chk-123"
        assert isinstance(ledger.timestamp, str)
        assert ledger.stages == {}
        assert ledger.per_claim == {}


class TestRecord:
    def test_record_stage(self):
        ledger = EvidenceLedger("chk-1")
        ledger.record("retrieve", total=50, sources=3)
        assert ledger.stages["retrieve"] == {"total": 50, "sources": 3}

    def test_record_claim(self):
        ledger = EvidenceLedger("chk-1")
        ledger.record_claim("0", "filter", removed=5, reason="duplicate")
        assert ledger.per_claim["0"]["filter"] == {"removed": 5, "reason": "duplicate"}

        # Second stage for the same claim extends the nested dict.
        ledger.record_claim("0", "score", total=10)
        assert "filter" in ledger.per_claim["0"]
        assert ledger.per_claim["0"]["score"] == {"total": 10}


class TestToDict:
    def test_to_dict_summary_dropped(self):
        ledger = EvidenceLedger("chk-1")
        ledger.record("retrieve", total=50)
        ledger.record("analyzer_input", total=30, snippet_fallbacks=2)
        d = ledger.to_dict()
        assert d["summary"]["evidence_entered_pipeline"] == 50
        assert d["summary"]["evidence_reached_analyzer"] == 30
        assert d["summary"]["total_dropped"] == 20

    def test_to_dict_summary_zero(self):
        ledger = EvidenceLedger("chk-1")
        d = ledger.to_dict()
        assert d["summary"]["evidence_entered_pipeline"] == 0
        assert d["summary"]["evidence_reached_analyzer"] == 0
        assert d["summary"]["total_dropped"] == 0

    def test_to_dict_snippet_fallbacks(self):
        ledger = EvidenceLedger("chk-1")
        ledger.record("analyzer_input", total=20, snippet_fallbacks=7)
        d = ledger.to_dict()
        assert d["summary"]["snippet_fallbacks_at_analyzer"] == 7

    def test_to_dict_shape(self):
        ledger = EvidenceLedger("chk-1")
        d = ledger.to_dict()
        assert set(d.keys()) == {
            "check_id",
            "timestamp",
            "summary",
            "stages",
            "per_claim",
        }


class TestSave:
    def test_save_creates_file(self, tmp_path, monkeypatch):
        ledger = EvidenceLedger("chk-save-test")
        ledger.record("retrieve", total=10)

        # Redirect the save path to tmp_path.
        def patched_save(self_inner) -> str:
            out_dir = str(tmp_path / "ledger")
            os.makedirs(out_dir, exist_ok=True)
            path = os.path.join(out_dir, f"{self_inner.check_id}.json")
            with open(path, "w") as f:
                json.dump(self_inner.to_dict(), f, indent=2, default=str)
            return path

        monkeypatch.setattr(EvidenceLedger, "save", patched_save)
        path = ledger.save()
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert data["check_id"] == "chk-save-test"
        assert data["summary"]["evidence_entered_pipeline"] == 10


class TestGetLedger:
    def test_get_ledger_enabled(self, monkeypatch):
        monkeypatch.setattr("app.pipeline.evidence_ledger.LEDGER_ENABLED", True)
        ledger = get_ledger("chk-enabled")
        assert isinstance(ledger, EvidenceLedger)
        assert ledger.check_id == "chk-enabled"

    def test_get_ledger_disabled(self, monkeypatch):
        monkeypatch.setattr("app.pipeline.evidence_ledger.LEDGER_ENABLED", False)
        result = get_ledger("chk-disabled")
        assert result is None
