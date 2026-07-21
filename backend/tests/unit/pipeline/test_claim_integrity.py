"""Claim-integrity tests (audit/CLAIM_INTEGRITY.md §4a).

E — recombine_single_thesis: a single-sentence declarative text submission
split into fragments is carried forward INTACT as one claim.
B — _context_block: decompose prompt carries the original submission so
elements anchor to the user's stated timeframe/scope.
"""

import pytest

from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer, _is_causal_link
from app.pipeline.extract import (
    is_single_declarative_sentence,
    recombine_single_thesis,
)

TECTONIC = (
    "Compared to the last 50 years, tectonic plate movement is extremely "
    "active currently, causing a large rise in volcanic eruptions and earthquakes"
)

FRAGMENTS = [
    {
        "text": "Tectonic plate movement is extremely active compared to the last 50 years",
        "position": 0,
        "confidence": 85,
        "category": "science",
        "subject_context": "tectonic activity",
        "key_entities": [{"text": "50 years", "type": "DATE"}],
        "type_hint": None,
    },
    {
        "text": "There is a large rise in volcanic eruptions",
        "position": 1,
        "confidence": 90,
        "category": "science",
        "subject_context": "volcanic eruptions",
        "key_entities": [
            {"text": "50 years", "type": "DATE"},  # duplicate — must dedup
            {"text": "volcanic eruptions", "type": "OTHER"},
        ],
        "type_hint": None,
    },
    {
        "text": "There is a large rise in earthquakes",
        "position": 2,
        "confidence": 88,
        "category": "science",
        "subject_context": "earthquakes",
        "key_entities": [{"text": "earthquakes", "type": "OTHER"}],
        "type_hint": None,
    },
]


class TestIsSingleDeclarativeSentence:
    def test_single_sentence_true(self):
        assert is_single_declarative_sentence(TECTONIC)

    def test_trailing_period_still_single(self):
        assert is_single_declarative_sentence(TECTONIC + ".")

    def test_question_false(self):
        assert not is_single_declarative_sentence("Is sea level rising 3mm per year?")

    def test_multi_sentence_false(self):
        assert not is_single_declarative_sentence(
            "GDP rose 2% in 2023. Arsenal won the league in the same year."
        )

    def test_empty_false(self):
        assert not is_single_declarative_sentence("   ")

    def test_abbreviation_fails_safe(self):
        # "U.S. Government" false-positives as a boundary → treated as
        # multi-sentence → caller keeps the split path. Safe direction.
        assert not is_single_declarative_sentence(
            "The U.S. Government raised tariffs in 2024, causing import prices to rise"
        )

    def test_decimal_not_a_boundary(self):
        assert is_single_declarative_sentence(
            "Inflation reached 3.5 percent in 2023, causing real wages to fall"
        )


class TestRecombineSingleThesis:
    def test_recombines_fragments_to_intact_claim(self):
        claim = recombine_single_thesis(TECTONIC, FRAGMENTS)
        assert claim is not None
        assert claim["text"] == TECTONIC  # user's sentence VERBATIM
        assert claim["position"] == 0
        assert claim["confidence"] == 90  # max of fragments
        assert claim["recombined_from"] == [f["text"] for f in FRAGMENTS]

    def test_entities_merged_and_deduped(self):
        claim = recombine_single_thesis(TECTONIC, FRAGMENTS)
        texts = [e["text"] for e in claim["key_entities"]]
        assert texts.count("50 years") == 1
        assert "volcanic eruptions" in texts and "earthquakes" in texts

    def test_single_claim_no_recombination(self):
        assert recombine_single_thesis(TECTONIC, FRAGMENTS[:1]) is None

    def test_multi_sentence_no_recombination(self):
        two_theses = "GDP rose 2% in 2023. Arsenal won the league."
        assert recombine_single_thesis(two_theses, FRAGMENTS) is None

    def test_question_no_recombination(self):
        assert recombine_single_thesis("Is the climate warming?", FRAGMENTS) is None

    def test_type_hint_preserved_for_grounds_gate(self):
        # §20 seam: a normative-hinted fragment keeps its hint on the intact
        # claim so should_apply_grounds still fires when the flag is on.
        frags = [dict(FRAGMENTS[0]), dict(FRAGMENTS[1], type_hint="normative")]
        claim = recombine_single_thesis(TECTONIC, frags)
        assert claim["type_hint"] == "normative"

    def test_carries_first_fragment_metadata(self):
        claim = recombine_single_thesis(TECTONIC, FRAGMENTS)
        assert claim["category"] == "science"
        assert claim["subject_context"] == "tectonic activity"


class TestDecomposeContextBlock:
    def test_context_appended(self):
        block = ClaimMapAnalyzer._context_block(TECTONIC, "There is a rise in X")
        assert "Original submission" in block
        assert "last 50 years" in block

    def test_no_context_empty(self):
        assert ClaimMapAnalyzer._context_block(None, "claim") == ""
        assert ClaimMapAnalyzer._context_block("  ", "claim") == ""

    def test_identical_to_claim_skipped(self):
        # E-recombined case: claim IS the submission — no redundant block.
        assert ClaimMapAnalyzer._context_block(TECTONIC, TECTONIC) == ""

    def test_context_bounded(self):
        block = ClaimMapAnalyzer._context_block("x" * 5000, "claim")
        assert len(block) < 1500


class TestCausalLinkTagger:
    """_is_causal_link (§4d fix 2): the mechanical gate deciding where the
    mapping SPECIFICITY CHECK rule applies. Positives = causal-link elements."""

    @pytest.mark.parametrize(
        "text",
        [
            "elevated tectonic activity is driving the rise in eruptions",
            "the fall in investment caused the rise in sewage discharges",
            "social media use is a primary contributing factor to anxiety",
            "warming led to melting",
            "declining ice leads to extreme winter weather",
            "the rise is due to privatisation",
            "measurement error is responsible for the discrepancy",
            "the spike resulted from the policy change",
        ],
    )
    def test_positives(self, text):
        assert _is_causal_link(text) is True

    @pytest.mark.parametrize(
        "text",
        [
            "tectonic plate movement is extremely active compared to the last 50 years",
            "there is a large rise in volcanic eruptions",
            "UK food prices have risen faster than the EU average",
            "Arctic sea ice has declined dramatically over the past decade",
            "",
        ],
    )
    def test_negatives(self, text):
        assert _is_causal_link(text) is False

    def test_non_string_is_false(self):
        assert _is_causal_link(None) is False


class TestCausalTagReachesPromptBuilders:
    """Every mapping/completion/recovery builder that serialises elements must
    append [CAUSAL LINK] to a causal element's line, else the SPECIFICITY CHECK
    rule (which references the tag) is inert on that pass (§4d fix 2 — verify)."""

    def _analyzer(self, captured):
        a = ClaimMapAnalyzer.__new__(ClaimMapAnalyzer)
        a.snippet_length = 200
        a.analyzer_temperature = 0.1
        a.analyzer_max_tokens = 2000
        a.max_elements = 5

        async def _fake(prompt, **kw):
            captured.append(prompt)
            return None  # short-circuit: prompt is built before this call

        a._call_llm = _fake
        return a

    def _cm(self, cid="c1"):
        from app.models.claim_map import ElementState

        return {
            "claim_id": cid,
            "normalised_claim": "Elevated activity is driving a rise in eruptions",
            "claim_type": "causal_interpretive",
            "elements": [
                {
                    "element_id": "e1",
                    "description": "Elevated activity is driving the rise in eruptions",
                    "evidence_refs": [],
                    "state": ElementState.unresolved,
                    "uncertainty": None,
                },
                {
                    "element_id": "e2",
                    "description": "There is a rise in eruptions",
                    "evidence_refs": [],
                    "state": ElementState.unresolved,
                    "uncertainty": None,
                },
            ],
            "metadata": {
                "decomposition_model": "t",
                "mapping_model": None,
                "element_count": 2,
                "completed_at": None,
            },
            "orientation": None,
        }

    def _ev(self):
        return {
            "evidence_id": "ev1",
            "title": "T",
            "snippet": "s",
            "tier": "reporting",
            "evidence_type": "article",
            "url": "https://example.com/x",
        }

    @pytest.mark.asyncio
    async def test_tag_in_every_builder(self):
        captured: list[str] = []
        a = self._analyzer(captured)

        async def _safe(coro):
            try:
                await coro
            except Exception:
                pass  # post-None processing is irrelevant — the prompt is built

        await _safe(a.map_evidence_to_elements(self._cm(), [self._ev()]))
        await _safe(
            a.map_evidence_batch(
                [
                    {"claim_map": self._cm("c1"), "evidence": [self._ev()]},
                    {"claim_map": self._cm("c2"), "evidence": [self._ev()]},
                ]
            )
        )
        await _safe(a._complete_unmapped_evidence(self._cm(), [self._ev()]))
        await _safe(
            a.map_evidence_to_specific_elements(self._cm(), ["e1", "e2"], [self._ev()])
        )

        assert captured, "no prompts were built"
        for prompt in captured:
            assert "driving the rise in eruptions [CAUSAL LINK]" in prompt
            # The non-causal element must NOT be tagged.
            assert "There is a rise in eruptions [CAUSAL LINK]" not in prompt
