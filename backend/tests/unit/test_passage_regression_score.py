import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "passage_score",
    Path(__file__).resolve().parents[2] / "scripts/score_passage_regressions.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def result(relationship):
    return {
        "claim_map": {
            "metadata": {"passage_review": {"status": "complete"}},
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {
                            "evidence_id": "source",
                            "relationship": relationship,
                            "citations": [{"quote": "an exactly matching quote"}],
                        }
                    ],
                }
            ],
        }
    }


NEGATIVE = [
    {
        "id": "clock",
        "element": "e1",
        "source": "source",
        "forbid": ["supports", "challenges"],
    }
]
POSITIVE = [
    {"id": "change", "element": "e1", "source": "source", "require": ["supports"]}
]


def test_complete_and_exact_quote_do_not_override_semantic_failure():
    assert not module.assess(result("supports"), NEGATIVE)[0]["passed"]
    assert not module.assess(result("challenges"), NEGATIVE)[0]["passed"]
    assert module.assess(result("context"), NEGATIVE)[0]["passed"]


def test_blanket_context_fails_positive_control():
    assert not module.assess(result("context"), POSITIVE)[0]["passed"]
    assert module.assess(result("supports"), POSITIVE)[0]["passed"]


def test_missing_element_is_not_negative_success():
    assert not module.assess({"claim_map": {"elements": []}}, NEGATIVE)[0]["passed"]


def test_missing_run_cannot_pass(tmp_path):
    scored = module.score(tmp_path, {"version": 1, "cases": {"missing": NEGATIVE}})
    assert len(scored["rows"]) == 4
    assert not scored["combined_arm_passed"]


def test_empty_expectations_cannot_pass(tmp_path):
    assert not module.score(tmp_path, {"version": 1, "cases": {}})["passed"]


def test_changed_source_version_cannot_reuse_review(tmp_path):
    value = result("supports")
    value["case_id"] = "case"
    value["claim_map"]["normalised_claim"] = "A dated change"
    value["claim_map"]["elements"][0]["description"] = "Change"
    value["evidence"] = [
        {
            "evidence_id": "source",
            "url": "https://example.invalid",
            "text_provenance": {"extraction_sha256": "a" * 64},
        }
    ]
    signature = module.input_signature(value)
    expectations = {
        "version": 1,
        "cases": {"case": POSITIVE},
        "input_signatures": {"case": {"0": signature, "1": signature}},
    }
    for s, p in ((0, 0), (1, 0), (0, 1), (1, 1)):
        value.update(structured=bool(s), passage=bool(p))
        (tmp_path / f"case-s{s}-p{p}.json").write_text(json.dumps(value))
    assert module.score(tmp_path, expectations)["passed"]
    value["evidence"][0]["text_provenance"]["extraction_sha256"] = "b" * 64
    (tmp_path / "case-s1-p1.json").write_text(json.dumps(value))
    scored = module.score(tmp_path, expectations)
    assert not scored["combined_arm_passed"]
    assert "source/element versions" in scored["rows"][-1]["error"]
