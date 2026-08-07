"""`mapping_model` must name the model that did the mapping.

WHY THIS FILE EXISTS
--------------------
Four production checks on 2026-08-05 reported `mappingModel` as
`gemini-2.5-flash-lite` three times and `gemini-2.5-flash` once, from the same
endpoint at the same tier, with `MAPPING_GOOGLE_MODEL=gemini-2.5-flash`
configured. The obvious reading — that mapping sometimes falls back to the
cheaper model — was wrong. The metadata was lying.

`_last_model_used` is instance state on the analyzer, written by EVERY LLM call
and read after the fact:

    map_evidence_batch     -> _call_llm(label="batch_mapping")  # mapping model
    _run_completion        -> _call_llm(label="map_completion") # NOT in the
                                                               # is_mapping set,
                                                               # so google_model
    metadata["mapping_model"] = self._last_model_used           # completion's

So whenever the completion pass ran, the mapping model was misreported as the
completion model. Both mapping paths had it — batch (line ~1776) and per-claim
(line ~1528, where `_complete_unmapped_evidence` is called at ~1515).

This matters beyond tidiness: `mapping_model` is the telemetry we would use to
judge whether a mapping-quality change worked, and Flash-Lite vs Flash is a
measured quality difference (50.7% vs 17.2% parrot rate). Telemetry that names
the wrong model makes that judgement impossible.

NOTE: the fix records the model at the point of the mapping call. It does NOT
change which model runs. That `map_completion` and `recovery_mapping` do mapping
work on the cheaper model is a separate, open finding — see
audit/2026-08-05_agent_tier_quality_findings.md (F4b).
"""

import pytest

from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer

MAPPING_MODEL = "gemini-2.5-flash"
COMPLETION_MODEL = "gemini-2.5-flash-lite"


class _StubAnalyzer(ClaimMapAnalyzer):
    """Analyzer whose LLM calls record a model per label, like the real one.

    Mirrors the production behaviour that caused the defect: the mapping call
    and the completion call set `_last_model_used` to different values, and the
    completion call happens second.
    """

    def __init__(self):
        super().__init__()
        self.calls = []

    async def _call_llm(self, prompt, temperature, max_tokens, label):
        self.calls.append(label)
        is_mapping = label in ("mapping", "batch_mapping")
        self._last_model_used = MAPPING_MODEL if is_mapping else COMPLETION_MODEL

        mapped_element = {
            "element_id": "e1",
            "evidence_refs": [
                {
                    "evidence_id": "ev-1",
                    "relationship": "supports",
                    "reasoning": "The source states the thing.",
                }
            ],
        }
        if label == "batch_mapping":
            return {"claims": [{"claim_index": 0, "elements": [mapped_element]}]}
        return {"elements": [mapped_element]}


def _claim_map():
    return {
        "claim_id": "0",
        "normalised_claim": "A testable claim.",
        "elements": [
            {
                "element_id": "e1",
                "description": "Something checkable.",
                "evidence_refs": [],
                "state": "unresolved",
            }
        ],
        "metadata": {},
    }


def _evidence():
    """Two items, of which the stub maps only one.

    The leftover is what makes the completion pass do work — and the completion
    pass is the thing that used to overwrite the recorded mapping model. With a
    single, fully-mapped item there is nothing to complete and the defect is
    never exercised.
    """
    return [
        {
            "evidence_id": "ev-1",
            "title": "A source",
            "snippet": "Some text.",
            "tier": "primary",
            "evidence_type": "official",
        },
        {
            "evidence_id": "ev-2",
            "title": "An unmapped source",
            "snippet": "Text the main pass left alone.",
            "tier": "reporting",
            "evidence_type": "news",
        },
    ]


@pytest.mark.asyncio
async def test_per_claim_mapping_reports_the_mapping_model():
    """The completion pass runs after mapping and must not claim the credit."""
    analyzer = _StubAnalyzer()

    result = await analyzer.map_evidence_to_elements(_claim_map(), _evidence())

    assert (
        "map_completion" in analyzer.calls
    ), "test is not exercising the defect — the completion pass did not run"
    assert result["metadata"]["mapping_model"] == MAPPING_MODEL


@pytest.mark.asyncio
async def test_batch_mapping_reports_the_mapping_model():
    """Same defect on the batch path, which is what production uses."""
    analyzer = _StubAnalyzer()
    claim_data = [{"claim_map": _claim_map(), "evidence": _evidence()}]

    await analyzer.map_evidence_batch(claim_data)

    assert (
        "map_completion" in analyzer.calls
    ), "test is not exercising the defect — the completion pass did not run"
    assert claim_data[0]["claim_map"]["metadata"]["mapping_model"] == MAPPING_MODEL


@pytest.mark.asyncio
async def test_the_completion_pass_is_what_would_overwrite_it():
    """Pins the mechanism, so a future reader knows why the capture is early.

    If `_last_model_used` no longer differs across labels this test is
    meaningless — and so is the fix — so assert the premise directly.
    """
    analyzer = _StubAnalyzer()

    await analyzer.map_evidence_to_elements(_claim_map(), _evidence())

    assert (
        analyzer._last_model_used == COMPLETION_MODEL
    ), "the last call should still be the completion pass — that is the trap"
