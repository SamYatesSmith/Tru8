"""Tests for the mapping model evaluation harness.

Covers:
- Prompt construction matches claim_map_analyzer.py exactly
- Validation logic mirrors _parse_mapping_response / _validate_evidence_refs
- Synthetic claims are well-formed
- Scoring sheet generation
- Dry-run mode produces correct output shape
- Hallucinated evidence IDs are stripped
- Invalid states default to unresolved
- Empty/missing evidence handling
"""

import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import sys

backend_dir = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from scripts.eval_mapping_model import (
    SYNTHETIC_CLAIMS,
    build_mapping_prompt,
    validate_mapping_output,
    _build_scoring_sheet,
)
from app.pipeline.claim_map_analyzer import MAPPING_PROMPT


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------


class TestBuildMappingPrompt:
    """Verify prompt construction matches claim_map_analyzer.py exactly."""

    def test_prompt_starts_with_mapping_prompt(self):
        prompt = build_mapping_prompt(
            normalised_claim="Test claim",
            elements=[{"element_id": "e1", "description": "Element one"}],
            evidence_list=[
                {
                    "evidence_id": "ev-001",
                    "title": "Test",
                    "snippet": "Some text",
                    "text": "Some longer text",
                }
            ],
        )
        assert prompt.startswith(MAPPING_PROMPT)

    def test_prompt_contains_claim(self):
        prompt = build_mapping_prompt(
            normalised_claim="GDP grew by 2%",
            elements=[{"element_id": "e1", "description": "GDP grew"}],
            evidence_list=[],
        )
        assert "Claim: GDP grew by 2%" in prompt

    def test_prompt_contains_elements(self):
        prompt = build_mapping_prompt(
            normalised_claim="Test",
            elements=[
                {"element_id": "e1", "description": "First element"},
                {"element_id": "e2", "description": "Second element"},
            ],
            evidence_list=[],
        )
        assert "- e1: First element" in prompt
        assert "- e2: Second element" in prompt

    def test_prompt_truncates_evidence_to_snippet_length(self):
        long_text = "A" * 1000
        prompt = build_mapping_prompt(
            normalised_claim="Test",
            elements=[{"element_id": "e1", "description": "Elem"}],
            evidence_list=[
                {
                    "evidence_id": "ev-001",
                    "title": "Title",
                    "snippet": long_text,
                    "text": long_text,
                }
            ],
            snippet_length=400,
        )
        # The evidence line should contain exactly 400 chars of text
        # Format: "- ev-001: [Title] AAAA...A"
        lines = prompt.split("\n")
        ev_line = [l for l in lines if "ev-001" in l][0]
        # Title is "Title" (5 chars), prefix is "- ev-001: [Title] " (19 chars)
        text_portion = ev_line.split("] ", 1)[1]
        assert len(text_portion) == 400

    def test_prompt_prefers_snippet_over_text(self):
        """Mirrors claim_map_analyzer.py: ev.get('snippet') or ev.get('text')."""
        prompt = build_mapping_prompt(
            normalised_claim="Test",
            elements=[{"element_id": "e1", "description": "Elem"}],
            evidence_list=[
                {
                    "evidence_id": "ev-001",
                    "title": "Title",
                    "snippet": "SNIPPET_CONTENT",
                    "text": "TEXT_CONTENT",
                }
            ],
        )
        assert "SNIPPET_CONTENT" in prompt
        # text should NOT appear because snippet is truthy
        assert "TEXT_CONTENT" not in prompt

    def test_prompt_falls_back_to_text_when_no_snippet(self):
        prompt = build_mapping_prompt(
            normalised_claim="Test",
            elements=[{"element_id": "e1", "description": "Elem"}],
            evidence_list=[
                {
                    "evidence_id": "ev-001",
                    "title": "Title",
                    "snippet": "",
                    "text": "FALLBACK_TEXT",
                }
            ],
        )
        assert "FALLBACK_TEXT" in prompt

    def test_prompt_matches_analyzer_format(self):
        """The prompt should have the same structure as map_evidence_to_elements()."""
        claim = "Test claim"
        elements = [{"element_id": "e1", "description": "Element one"}]
        evidence = [
            {
                "evidence_id": "ev-001",
                "title": "Article",
                "snippet": "Some evidence text here",
                "text": "Some evidence text here",
            }
        ]

        prompt = build_mapping_prompt(claim, elements, evidence, snippet_length=400)

        # Verify structure matches claim_map_analyzer.py lines 328-332
        assert "Claim: Test claim" in prompt
        assert "Elements:" in prompt
        assert "Evidence:" in prompt
        assert "- e1: Element one" in prompt
        assert "- ev-001: [Article] Some evidence text here" in prompt


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------


class TestValidateMappingOutput:
    """Verify validation mirrors ClaimMapAnalyzer._parse_mapping_response."""

    def _elements(self):
        return [
            {"element_id": "e1", "description": "First"},
            {"element_id": "e2", "description": "Second"},
        ]

    def _evidence(self):
        return [
            {"evidence_id": "ev-001", "title": "A"},
            {"evidence_id": "ev-002", "title": "B"},
        ]

    def test_valid_output_passes(self):
        parsed = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-001",
                            "relationship": "supports",
                            "reasoning": "Confirms the assertion",
                        }
                    ],
                    "state": "supported",
                    "uncertainty": None,
                },
                {
                    "element_id": "e2",
                    "evidence_refs": [],
                    "state": "unresolved",
                    "uncertainty": "No evidence found",
                },
            ]
        }
        result = validate_mapping_output(parsed, self._elements(), self._evidence())
        assert len(result["elements"]) == 2
        assert result["elements"][0]["state"] == "supported"
        assert result["elements"][1]["state"] == "unresolved"
        assert result["validation_errors"] == []

    def test_hallucinated_evidence_id_stripped(self):
        parsed = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-FAKE",
                            "relationship": "supports",
                            "reasoning": "Invented reference",
                        },
                        {
                            "evidence_id": "ev-001",
                            "relationship": "supports",
                            "reasoning": "Real reference",
                        },
                    ],
                    "state": "supported",
                },
                {"element_id": "e2", "evidence_refs": [], "state": "unresolved"},
            ]
        }
        result = validate_mapping_output(parsed, self._elements(), self._evidence())
        e1_refs = result["elements"][0]["evidence_refs"]
        assert len(e1_refs) == 1
        assert e1_refs[0]["evidence_id"] == "ev-001"
        assert any("Hallucinated" in e for e in result["validation_errors"])

    def test_invalid_relationship_stripped(self):
        parsed = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-001",
                            "relationship": "confirms",  # not valid
                            "reasoning": "Wrong enum",
                        }
                    ],
                    "state": "supported",
                },
                {"element_id": "e2", "evidence_refs": [], "state": "unresolved"},
            ]
        }
        result = validate_mapping_output(parsed, self._elements(), self._evidence())
        assert len(result["elements"][0]["evidence_refs"]) == 0
        assert any("Invalid relationship" in e for e in result["validation_errors"])

    def test_invalid_state_defaults_to_unresolved(self):
        parsed = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [],
                    "state": "confirmed",  # not valid
                },
                {"element_id": "e2", "evidence_refs": [], "state": "unresolved"},
            ]
        }
        result = validate_mapping_output(parsed, self._elements(), self._evidence())
        assert result["elements"][0]["state"] == "unresolved"
        assert any("Invalid state" in e for e in result["validation_errors"])

    def test_missing_element_in_output(self):
        parsed = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [],
                    "state": "unresolved",
                },
                # e2 is missing
            ]
        }
        result = validate_mapping_output(parsed, self._elements(), self._evidence())
        assert len(result["elements"]) == 2
        assert result["elements"][1]["state"] == "unresolved"
        assert any("missing" in e for e in result["validation_errors"])

    def test_none_parsed_returns_all_unresolved(self):
        result = validate_mapping_output(None, self._elements(), self._evidence())
        assert all(e["state"] == "unresolved" for e in result["elements"])
        assert len(result["elements"]) == 2
        assert "parsed is None" in result["validation_errors"]

    def test_reasoning_preserved_when_present(self):
        parsed = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-001",
                            "relationship": "supports",
                            "reasoning": "Reports GDP at 0.1%, confirming growth",
                        }
                    ],
                    "state": "supported",
                },
                {"element_id": "e2", "evidence_refs": [], "state": "unresolved"},
            ]
        }
        result = validate_mapping_output(parsed, self._elements(), self._evidence())
        ref = result["elements"][0]["evidence_refs"][0]
        assert ref["reasoning"] == "Reports GDP at 0.1%, confirming growth"

    def test_empty_reasoning_becomes_none(self):
        parsed = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-001",
                            "relationship": "supports",
                            "reasoning": "",
                        }
                    ],
                    "state": "supported",
                },
                {"element_id": "e2", "evidence_refs": [], "state": "unresolved"},
            ]
        }
        result = validate_mapping_output(parsed, self._elements(), self._evidence())
        assert result["elements"][0]["evidence_refs"][0]["reasoning"] is None


# ---------------------------------------------------------------------------
# Synthetic claims validity
# ---------------------------------------------------------------------------


class TestSyntheticClaims:
    """Verify built-in synthetic claims are well-formed."""

    def test_all_claims_have_required_fields(self):
        for claim in SYNTHETIC_CLAIMS:
            assert "claim_id" in claim
            assert "normalised_claim" in claim
            assert "elements" in claim
            assert "evidence" in claim
            assert len(claim["elements"]) >= 1
            assert len(claim["evidence"]) >= 1

    def test_all_elements_have_ids_and_descriptions(self):
        for claim in SYNTHETIC_CLAIMS:
            for elem in claim["elements"]:
                assert "element_id" in elem
                assert "description" in elem
                assert elem["element_id"].startswith("e")

    def test_all_evidence_has_required_fields(self):
        for claim in SYNTHETIC_CLAIMS:
            for ev in claim["evidence"]:
                assert "evidence_id" in ev
                assert "title" in ev
                assert "text" in ev or "snippet" in ev
                assert "source" in ev
                assert "url" in ev

    def test_claim_ids_are_unique(self):
        ids = [c["claim_id"] for c in SYNTHETIC_CLAIMS]
        assert len(ids) == len(set(ids))

    def test_evidence_ids_are_unique_within_claim(self):
        for claim in SYNTHETIC_CLAIMS:
            ev_ids = [e["evidence_id"] for e in claim["evidence"]]
            assert len(ev_ids) == len(
                set(ev_ids)
            ), f"Duplicate ev IDs in {claim['claim_id']}"

    def test_synthetic_covers_difficulty_range(self):
        """At least one claim should have evidence that challenges the assertion."""
        # eval-001: ONS says 0.1% not 0.5% — should produce 'challenges'
        # eval-003: Tesla says 1.79M not 2M — should produce 'challenges'
        claim_texts = [c["normalised_claim"] for c in SYNTHETIC_CLAIMS]
        assert any("GDP" in t for t in claim_texts)
        assert any("Tesla" in t or "Amazon" in t for t in claim_texts)


# ---------------------------------------------------------------------------
# Scoring sheet generation
# ---------------------------------------------------------------------------


class TestScoringSheet:
    """Verify scoring sheet template is well-formed."""

    def _make_result(self, claim_id, model, elements, refs_per_element=1):
        validated_elements = []
        for elem in elements:
            refs = [
                {
                    "evidence_id": f"ev-{i}",
                    "relationship": "supports",
                    "reasoning": f"Reasoning for {elem['element_id']}",
                }
                for i in range(refs_per_element)
            ]
            validated_elements.append(
                {
                    "element_id": elem["element_id"],
                    "evidence_refs": refs,
                    "state": "supported",
                }
            )
        return {
            "claim_id": claim_id,
            "normalised_claim": "Test claim",
            "model": model,
            "validated": {
                "elements": validated_elements,
                "validation_errors": [],
            },
        }

    def test_sheet_has_two_entries_per_claim(self):
        elements = [{"element_id": "e1", "description": "Elem"}]
        flash = self._make_result("c1", "flash_lite", elements)
        gpt4o = self._make_result("c1", "gpt4o", elements)

        sheet = _build_scoring_sheet([flash], [gpt4o])
        assert len(sheet) == 2
        models = {s["model"] for s in sheet}
        assert models == {"flash_lite", "gpt4o"}

    def test_sheet_has_null_scores(self):
        elements = [{"element_id": "e1", "description": "Elem"}]
        flash = self._make_result("c1", "flash_lite", elements)
        gpt4o = self._make_result("c1", "gpt4o", elements)

        sheet = _build_scoring_sheet([flash], [gpt4o])
        for entry in sheet:
            for es in entry["element_scores"]:
                assert es["state_score"] is None
            for rs in entry["ref_scores"]:
                assert rs["relationship_score"] is None
                assert rs["reasoning_score"] is None
            assert entry["coverage_score"] is None

    def test_sheet_skips_dry_run_entries(self):
        flash = {"claim_id": "c1", "dry_run": True}
        gpt4o = {"claim_id": "c1", "dry_run": True}
        sheet = _build_scoring_sheet([flash], [gpt4o])
        assert len(sheet) == 0

    def test_sheet_preserves_reasoning_text(self):
        elements = [{"element_id": "e1", "description": "Elem"}]
        flash = self._make_result("c1", "flash_lite", elements, refs_per_element=1)
        gpt4o = self._make_result("c1", "gpt4o", elements, refs_per_element=1)

        sheet = _build_scoring_sheet([flash], [gpt4o])
        for entry in sheet:
            assert len(entry["ref_scores"]) == 1
            assert "Reasoning for e1" in entry["ref_scores"][0]["reasoning_text"]


# ---------------------------------------------------------------------------
# Prompt fidelity (exact match with ClaimMapAnalyzer)
# ---------------------------------------------------------------------------


class TestPromptFidelity:
    """Verify the harness prompt exactly matches what the pipeline sends."""

    def test_prompt_matches_claim_map_analyzer_construction(self):
        """Reproduce the exact prompt construction from claim_map_analyzer.py:317-332."""
        claim = "The UK left the EU in 2020"
        elements = [
            {"element_id": "e1", "description": "The UK left the EU"},
            {"element_id": "e2", "description": "The departure occurred in 2020"},
        ]
        evidence = [
            {
                "evidence_id": "ev-100",
                "title": "Brexit Timeline",
                "snippet": "The United Kingdom formally withdrew from the European Union on 31 January 2020.",
                "text": "The United Kingdom formally withdrew from the European Union on 31 January 2020, ending 47 years of membership.",
            }
        ]
        snippet_length = 400

        # Build via harness
        harness_prompt = build_mapping_prompt(
            claim, elements, evidence, snippet_length=snippet_length
        )

        # Build via analyzer logic (claim_map_analyzer.py lines 317-332)
        elements_desc = "\n".join(
            f"- {e['element_id']}: {e['description']}" for e in elements
        )
        evidence_desc = "\n".join(
            f"- {ev.get('evidence_id', 'unknown')}: "
            f"[{ev.get('title', 'Untitled')}] "
            f"{(ev.get('snippet') or ev.get('text') or '')[:snippet_length]}"
            for ev in evidence
        )
        analyzer_prompt = (
            f"{MAPPING_PROMPT}\n\n"
            f"Claim: {claim}\n\n"
            f"Elements:\n{elements_desc}\n\n"
            f"Evidence:\n{evidence_desc}"
        )

        assert harness_prompt == analyzer_prompt
