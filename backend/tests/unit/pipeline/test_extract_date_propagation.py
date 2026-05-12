"""Tests for _propagate_article_dates (NF-20-B canonical fix, 2026-05-12).

The LLM produces per-claim entities and typically anchors DATE on one
claim when multiple claims describe aspects of the same event. The
propagation step computes the article-level DATE union and injects
inherited entries into dateless claims so downstream consumers
(_inject_freshness_for_historical_dates, adapter prepare_query paths)
see the article's temporal anchor on every claim.

Real-data anchor: TRU-E4C5-E295 (GBR coral 2026-05-12) — 4 claims, only
claim 0 carried "March 2024" DATE; claims 1-3 had no DATE, so B4
freshness inject silently no-op'd on them and the Open-Meteo / web
search pool for claim 2 returned generic content instead of March 2024
SST anomaly data.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from app.pipeline.extract import ClaimExtractor


@pytest.fixture
def extractor():
    return ClaimExtractor()


@pytest.fixture(autouse=True)
def _disable_synthesis_by_default(monkeypatch):
    """Default the LLM synthesis call to None — wired-seam tests below
    exercise _validate_and_refine_claims, which can call into merge's
    synthesis path. Keep tests deterministic."""

    async def _no_synthesis(*args, **kwargs):
        return None

    monkeypatch.setattr("app.pipeline.extract.call_google_ai", _no_synthesis)


def _claim(text, position, subject_context=None, key_entities=None, confidence=85):
    return {
        "text": text,
        "position": position,
        "confidence": confidence,
        "category": None,
        "subject_context": subject_context,
        "key_entities": key_entities or [],
    }


def _orthogonal_embedding_service(n: int):
    """Cosine 0 → dedup runs but never fires."""
    service = MagicMock()
    embeddings = [np.eye(max(n, 2))[i] for i in range(n)]
    service.embed_batch = AsyncMock(return_value=embeddings)
    return service


# ---------- Pure no-op behaviour ----------


class TestNoOpCases:
    """Propagation must not run when there is nothing to do."""

    def test_no_op_for_empty_list(self, extractor):
        result = extractor._propagate_article_dates([])
        assert result == []

    def test_no_op_for_single_claim(self, extractor):
        # Single-claim articles cannot have inheritance.
        claims = [
            _claim(
                "BP profits hit £23bn in 2022",
                0,
                "BP 2022 results",
                [
                    {"text": "BP", "type": "ORG"},
                    {"text": "2022", "type": "DATE"},
                ],
            )
        ]
        result = extractor._propagate_article_dates(claims)
        assert len(result) == 1
        # Entity bag unchanged.
        assert result[0]["key_entities"] == claims[0]["key_entities"]

    def test_no_op_when_no_claim_has_date(self, extractor):
        # If no claim has DATE, there's nothing to propagate.
        claims = [
            _claim("X happened", 0, "ctx", [{"text": "X", "type": "ORG"}]),
            _claim("Y happened", 1, "ctx", [{"text": "Y", "type": "ORG"}]),
        ]
        result = extractor._propagate_article_dates(claims)
        for original, returned in zip(claims, result):
            assert returned["key_entities"] == original["key_entities"]

    def test_no_op_when_all_claims_already_have_date(self, extractor):
        claims = [
            _claim(
                "X in 2022",
                0,
                "ctx",
                [{"text": "X", "type": "ORG"}, {"text": "2022", "type": "DATE"}],
            ),
            _claim(
                "Y in 2024",
                1,
                "ctx",
                [{"text": "Y", "type": "ORG"}, {"text": "2024", "type": "DATE"}],
            ),
        ]
        original_bags = [list(c["key_entities"]) for c in claims]
        result = extractor._propagate_article_dates(claims)
        for original, returned in zip(original_bags, result):
            assert returned["key_entities"] == original

    def test_idempotent_on_repeat_call(self, extractor):
        # After one propagation pass, all claims have DATE → no further
        # changes on the second pass.
        claims = [
            _claim(
                "GBR fifth mass bleaching March 2024",
                0,
                "GBR 2024",
                [
                    {"text": "Great Barrier Reef", "type": "LOCATION"},
                    {"text": "March 2024", "type": "DATE"},
                ],
            ),
            _claim(
                "1.5°C Coral Sea anomalies",
                1,
                "GBR 2024",
                [
                    {"text": "1.5°C", "type": "AMOUNT"},
                    {"text": "Coral Sea", "type": "LOCATION"},
                ],
            ),
        ]
        first = extractor._propagate_article_dates(claims)
        first_snapshot = [list(c["key_entities"]) for c in first]
        second = extractor._propagate_article_dates(first)
        for snap, after in zip(first_snapshot, second):
            assert after["key_entities"] == snap


# ---------- Core propagation behaviour ----------


class TestPropagation:
    """The TRU-E4C5-shape inheritance: one claim has DATE, others lack."""

    def test_inherits_single_date_to_dateless_claims(self, extractor):
        # TRU-E4C5-E295: claim 0 has March 2024, claims 1-3 have none.
        claims = [
            _claim(
                "GBR experienced fifth mass coral bleaching event in March 2024",
                0,
                "GBR 2024 bleaching",
                [
                    {"text": "Great Barrier Reef", "type": "LOCATION"},
                    {"text": "March 2024", "type": "DATE"},
                ],
            ),
            _claim(
                "GBRMPA aerial surveys documented two-thirds bleaching",
                1,
                "GBRMPA surveys",
                [
                    {"text": "GBRMPA", "type": "ORG"},
                    {"text": "two-thirds", "type": "AMOUNT"},
                ],
            ),
            _claim(
                "Ocean heat anomalies of 1.5°C above March average in Coral Sea",
                2,
                "Coral Sea anomalies",
                [
                    {"text": "1.5°C", "type": "AMOUNT"},
                    {"text": "Coral Sea", "type": "LOCATION"},
                ],
            ),
            _claim(
                "AIMS attributed bleaching to heat anomalies",
                3,
                "AIMS attribution",
                [{"text": "AIMS", "type": "ORG"}],
            ),
        ]
        result = extractor._propagate_article_dates(claims)

        # Claim 0 unchanged.
        assert {e["text"] for e in result[0]["key_entities"]} == {
            "Great Barrier Reef",
            "March 2024",
        }
        # Claims 1, 2, 3 each gain "March 2024" as DATE.
        for idx in (1, 2, 3):
            date_entries = [
                e for e in result[idx]["key_entities"] if e.get("type") == "DATE"
            ]
            assert len(date_entries) == 1
            assert date_entries[0]["text"] == "March 2024"

    def test_inherited_entries_carry_provenance_flag(self, extractor):
        claims = [
            _claim(
                "X in 2022",
                0,
                "ctx",
                [{"text": "X", "type": "ORG"}, {"text": "2022", "type": "DATE"}],
            ),
            _claim("Y happened", 1, "ctx", [{"text": "Y", "type": "ORG"}]),
        ]
        result = extractor._propagate_article_dates(claims)
        # Original claim 0 entries don't get the flag.
        for ent in result[0]["key_entities"]:
            assert "source" not in ent
        # Claim 1's inherited DATE carries the provenance flag.
        inherited = [e for e in result[1]["key_entities"] if e.get("type") == "DATE"]
        assert len(inherited) == 1
        assert inherited[0]["source"] == "article_inheritance"
        # Original non-DATE entities stay un-flagged.
        non_date = [e for e in result[1]["key_entities"] if e.get("type") != "DATE"]
        for ent in non_date:
            assert "source" not in ent

    def test_inherits_union_when_article_has_multiple_dates(self, extractor):
        # Mixed-date article: claim A explicit 2022, claim B explicit 2024,
        # claim C dateless. C inherits both as the article-level union.
        claims = [
            _claim(
                "X in 2022",
                0,
                "ctx-A",
                [{"text": "X", "type": "ORG"}, {"text": "2022", "type": "DATE"}],
            ),
            _claim(
                "Y in 2024",
                1,
                "ctx-B",
                [{"text": "Y", "type": "ORG"}, {"text": "2024", "type": "DATE"}],
            ),
            _claim("Z happened", 2, "ctx-C", [{"text": "Z", "type": "ORG"}]),
        ]
        result = extractor._propagate_article_dates(claims)
        c_dates = {
            e["text"] for e in result[2]["key_entities"] if e.get("type") == "DATE"
        }
        assert c_dates == {"2022", "2024"}
        # Claims A and B unchanged (each had its own DATE).
        assert {e["text"] for e in result[0]["key_entities"]} == {"X", "2022"}
        assert {e["text"] for e in result[1]["key_entities"]} == {"Y", "2024"}

    def test_does_not_override_claim_with_own_date(self, extractor):
        # Claim A has 2022. Claim B has 2024. Neither inherits — both are
        # left strictly as the LLM emitted them.
        claims = [
            _claim(
                "X in 2022",
                0,
                "ctx",
                [{"text": "X", "type": "ORG"}, {"text": "2022", "type": "DATE"}],
            ),
            _claim(
                "Y in 2024",
                1,
                "ctx",
                [{"text": "Y", "type": "ORG"}, {"text": "2024", "type": "DATE"}],
            ),
        ]
        result = extractor._propagate_article_dates(claims)
        a_dates = [
            e["text"] for e in result[0]["key_entities"] if e.get("type") == "DATE"
        ]
        b_dates = [
            e["text"] for e in result[1]["key_entities"] if e.get("type") == "DATE"
        ]
        assert a_dates == ["2022"]
        assert b_dates == ["2024"]

    def test_preserves_existing_non_date_entities(self, extractor):
        # The LOCATION + ORG + AMOUNT on claim 1 must survive intact when
        # the DATE is appended.
        claims = [
            _claim(
                "X in 2022",
                0,
                "ctx",
                [{"text": "X", "type": "ORG"}, {"text": "2022", "type": "DATE"}],
            ),
            _claim(
                "Y did Z",
                1,
                "ctx",
                [
                    {"text": "Y", "type": "ORG"},
                    {"text": "Z", "type": "LOCATION"},
                    {"text": "$100m", "type": "AMOUNT"},
                ],
            ),
        ]
        result = extractor._propagate_article_dates(claims)
        non_date = [
            (e["text"], e["type"])
            for e in result[1]["key_entities"]
            if e.get("type") != "DATE"
        ]
        assert ("Y", "ORG") in non_date
        assert ("Z", "LOCATION") in non_date
        assert ("$100m", "AMOUNT") in non_date


# ---------- Edge cases ----------


class TestEdgeCases:
    def test_handles_malformed_entity_dict(self, extractor):
        # Pre-existing entity bag contains malformed entries (missing
        # text or type, non-dict values). Propagation must not crash.
        claims = [
            _claim(
                "X in 2022",
                0,
                "ctx",
                [
                    {"text": "X", "type": "ORG"},
                    {"text": "2022", "type": "DATE"},
                ],
            ),
            _claim(
                "Y happened",
                1,
                "ctx",
                [
                    {"text": "Y", "type": "ORG"},
                    None,  # non-dict
                    {"text": None, "type": "DATE"},  # malformed
                    {},  # empty dict
                ],
            ),
        ]
        result = extractor._propagate_article_dates(claims)
        # Claim 1 should still get the inherited "2022" DATE. The
        # malformed entries (None, {text:None}, {}) survive in the bag
        # untouched — propagation skips them during DATE-union scanning
        # but does not filter them out. Downstream consumers
        # (retrieve.py:2046-2051, _extract_max_year_from_entities) all
        # apply `isinstance(e, dict)` guards.
        dates = [
            e["text"]
            for e in result[1]["key_entities"]
            if isinstance(e, dict) and e.get("type") == "DATE" and e.get("text")
        ]
        assert "2022" in dates

    def test_case_insensitive_dedup_of_article_dates(self, extractor):
        # If two claims have different-cased identical DATEs, the union
        # collapses them.
        claims = [
            _claim(
                "X in March 2024",
                0,
                "ctx",
                [{"text": "March 2024", "type": "DATE"}],
            ),
            _claim(
                "Y in march 2024",
                1,
                "ctx",
                [{"text": "march 2024", "type": "DATE"}],
            ),
            _claim("Z happened", 2, "ctx", [{"text": "Z", "type": "ORG"}]),
        ]
        result = extractor._propagate_article_dates(claims)
        z_dates = [
            e["text"] for e in result[2]["key_entities"] if e.get("type") == "DATE"
        ]
        assert len(z_dates) == 1  # case-insensitive dedup

    def test_handles_none_key_entities(self, extractor):
        # A claim with key_entities=None (defensive — the production
        # code path always emits []), shouldn't crash.
        claims = [
            _claim(
                "X in 2022",
                0,
                "ctx",
                [{"text": "2022", "type": "DATE"}],
            ),
            _claim("Y", 1, "ctx", None),
        ]
        result = extractor._propagate_article_dates(claims)
        # Claim 1's bag now contains exactly one inherited DATE.
        assert len(result[1]["key_entities"]) == 1
        assert result[1]["key_entities"][0]["text"] == "2022"


# ---------- Wired seam: _validate_and_refine_claims order ----------


class TestWiredSeam:
    """Locks the load-bearing order: dedup before propagate before merge.

    Validates that propagation is invoked from inside the chain and
    receives the post-dedup claim list, not the pre-dedup one.
    """

    async def test_propagation_runs_after_dedup_and_before_merge(self, extractor):
        # 3 claims: claim 0 has 2022 DATE; claim 1 is identical
        # text-similar to claim 0 (dedup would fire if discriminator
        # matched); claim 2 is dateless and unrelated. Orthogonal
        # embeddings keep cosine 0 → dedup does NOT fire even on
        # similar-text. Then propagation injects 2022 into claim 2.
        claims = [
            _claim(
                "Russia spent 6.7% GDP on military in 2024",
                0,
                "Russia 2024 spending",
                [
                    {"text": "Russia", "type": "LOCATION"},
                    {"text": "2024", "type": "DATE"},
                    {"text": "6.7%", "type": "AMOUNT"},
                ],
            ),
            _claim(
                "Russia spending reached new peak this year",
                1,
                "Russia 2024 spending",
                [{"text": "Russia", "type": "LOCATION"}],
            ),
            _claim(
                "SIPRI published the analysis",
                2,
                "SIPRI publication",
                [{"text": "SIPRI", "type": "ORG"}],
            ),
        ]
        with patch(
            "app.services.embeddings.get_embedding_service",
            new=AsyncMock(return_value=_orthogonal_embedding_service(len(claims))),
        ):
            result = await extractor._validate_and_refine_claims(claims)

        # Three claims survive (cosine 0 → no dedup; merge's Pass 1
        # collapses claims 0+1 via shared subject_context).
        # The merged claim and the SIPRI singleton remain.
        assert len(result) == 2

        # Find the claim that descends from claim 1 in the merge group.
        # That claim's bag must include the propagated 2024 DATE
        # because propagation ran on the post-dedup list before merge.
        merged_with_russia_topic = [
            r
            for r in result
            if any(e.get("text") == "Russia" for e in r["key_entities"])
        ]
        assert merged_with_russia_topic
        # Merged claim's entity union must contain 2024 (DATE).
        union_dates = {
            e["text"]
            for c in merged_with_russia_topic
            for e in c["key_entities"]
            if e.get("type") == "DATE"
        }
        assert "2024" in union_dates

        # The SIPRI singleton was dateless; after propagation it carries
        # inherited DATE 2024.
        sipri = next(
            r
            for r in result
            if any(e.get("text") == "SIPRI" for e in r["key_entities"])
        )
        sipri_dates = [e for e in sipri["key_entities"] if e.get("type") == "DATE"]
        assert len(sipri_dates) == 1
        assert sipri_dates[0]["text"] == "2024"
        # And the inherited DATE on SIPRI carries the provenance flag.
        assert sipri_dates[0].get("source") == "article_inheritance"

    async def test_dedup_discriminator_uses_raw_entities_not_propagated(
        self, extractor
    ):
        """Order check: if propagation ran BEFORE dedup, two claims that
        differ only in inherited DATE could falsely match the
        discriminator and trigger dedup. Order must be dedup-first.

        Distinct subject_contexts prevent Pass 1 merge from collapsing
        them — this test isolates the dedup safeguard specifically.
        """
        # Two near-paraphrase claims with different DATE entities — the
        # d78b4c3 paired-comparison safeguard must keep both.
        claims = [
            _claim(
                "Russia spent $109bn on military in 2022",
                0,
                "Russia 2022 spending",
                [
                    {"text": "Russia", "type": "LOCATION"},
                    {"text": "$109bn", "type": "AMOUNT"},
                    {"text": "2022", "type": "DATE"},
                ],
            ),
            _claim(
                "Russia spent $149bn on military in 2024",
                1,
                "Russia 2024 spending",
                [
                    {"text": "Russia", "type": "LOCATION"},
                    {"text": "$149bn", "type": "AMOUNT"},
                    {"text": "2024", "type": "DATE"},
                ],
            ),
        ]
        # Mock embeddings so cosine ~1.0 — dedup pass fires; the
        # discriminator-set safeguard must save both because AMOUNT
        # and DATE differ.
        service = MagicMock()
        service.embed_batch = AsyncMock(return_value=[np.array([1.0, 0.0, 0.0])] * 2)
        with patch(
            "app.services.embeddings.get_embedding_service",
            new=AsyncMock(return_value=service),
        ):
            result = await extractor._validate_and_refine_claims(claims)
        # Both claims must survive. Then propagation runs on a 2-claim
        # list where both claims already have DATE → no-op.
        assert len(result) == 2
        # Each survivor retains its own (different) DATE.
        date_per_claim = sorted(
            e["text"]
            for c in result
            for e in c["key_entities"]
            if e.get("type") == "DATE"
        )
        assert date_per_claim == ["2022", "2024"]
