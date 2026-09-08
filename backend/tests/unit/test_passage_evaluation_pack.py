"""Preparation must never hide changed inputs or leak reviewer answers."""

import importlib.util
import json
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/prepare_passage_evaluation.py"
spec = importlib.util.spec_from_file_location("prepare_pack", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_synthetic_values_vary_without_changing_the_control_structure():
    first, review = module.synthetic_controls(1)
    second, _ = module.synthetic_controls(2)
    assert len(first["cases"]) == len(second["cases"]) == 8
    assert first != second
    assert all(c["synthetic"] for c in first["cases"])
    assert all(s["url"].endswith(".invalid") for c in first["cases"] for s in c["sources"])
    assert "review_guidance" not in json.dumps(first)
    assert all(r["quality_result"] == "not_run" for r in review)


def fixture(tmp_path):
    text = b"<html><body><p>Test source</p></body></html>"
    (tmp_path / "s.html").write_bytes(text)
    module.write_json(
        tmp_path / "manifest.json",
        {
            "sources": [
                {
                    "id": "s",
                    "status": "captured",
                    "content_type": "text/html",
                    "encoding": "utf-8",
                    "file": "s.html",
                    "sha256": module.digest(text),
                    "url": "https://example.invalid",
                    "title": "Test",
                }
            ]
        },
    )
    module.write_json(
        tmp_path / "spec.json",
        {
            "cases": [
                {
                    "id": "case",
                    "claim": "Claim",
                    "elements": [],
                    "source_ids": ["s", "missing"],
                    "review_guidance": "SECRET_EXPECTATION",
                }
            ]
        },
    )


def test_changed_source_bytes_are_rejected(tmp_path):
    fixture(tmp_path)
    (tmp_path / "s.html").write_bytes(b"changed")
    with pytest.raises(ValueError, match="Source bytes changed"):
        module.prepare(tmp_path)


def test_expectations_are_separate_and_missing_sources_stay_visible(
    tmp_path, monkeypatch
):
    from app.services.evidence import EvidenceExtractor

    fixture(tmp_path)
    monkeypatch.setattr(
        EvidenceExtractor,
        "_extract_main_content",
        lambda *args: "Exact source material. " * 30,
    )
    module.prepare(tmp_path)
    inputs = (tmp_path / "prepared/inputs.json").read_text(encoding="utf-8")
    assert "SECRET_EXPECTATION" not in inputs
    assert json.loads(inputs)[0]["missing_source_ids"] == ["missing"]
    review = json.loads((tmp_path / "prepared/review.json").read_text())
    assert review[0]["quality_result"] == "not_run"
    assert review[0]["source_availability"] == "incomplete"
    with pytest.raises(FileExistsError):
        module.prepare(tmp_path)
