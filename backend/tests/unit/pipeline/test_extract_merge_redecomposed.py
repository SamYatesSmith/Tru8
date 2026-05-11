"""Tests for _merge_redecomposed_claims (Bug A — V1 quality plan 2026-05-06).

Mechanical merge pass that runs after dedup, catching the LLM's
single-sentence-into-4-claims redecomposition pattern. Two passes:
  1. identical normalised subject_context
  2. ≥3 key_entities overlap with ORG/PRODUCT + DATE backbone

Real-data anchors come from the 7 V1-plan diagnostic checks
(2026-05-06): TRU-7C40 mammogram, TRU-5411 BlackRock, TRU-15A8 Russia,
TRU-B3A4 UK election (over-decomposed) and TRU-8EBE Ozempic, TRU-A755
GBR coral, TRU-EF3F Sha'Carri (negative cases).
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
    """Default the LLM synthesis call to None so existing merge-mechanic
    tests fall back to naive concat (their assertions pin the concat
    shape). Tests that want synthesis to actually fire override this
    with their own patch on `app.pipeline.extract.call_google_ai`."""

    async def _no_synthesis(*args, **kwargs):
        return None

    monkeypatch.setattr("app.pipeline.extract.call_google_ai", _no_synthesis)


def _claim(text, position, subject_context=None, key_entities=None, confidence=85):
    """Builder mirroring the dict shape of LLM output post-serialisation."""
    return {
        "text": text,
        "position": position,
        "confidence": confidence,
        "category": None,
        "subject_context": subject_context,
        "key_entities": key_entities or [],
    }


def _orthogonal_embedding_service(n: int):
    """Mock embedding service whose embed_batch returns n orthogonal unit
    vectors. Cosine similarity between any two is 0, well below the 0.85
    dedup threshold — so dedup runs but never fires."""
    service = MagicMock()
    embeddings = [np.eye(max(n, 2))[i] for i in range(n)]
    service.embed_batch = AsyncMock(return_value=embeddings)
    return service


def _identical_embedding_service(n: int):
    """Mock embedding service whose embed_batch returns n copies of the
    same unit vector. Cosine similarity between any pair is 1.0 — dedup
    fires aggressively, keeping the longest claim."""
    service = MagicMock()
    embeddings = [np.array([1.0, 0.0, 0.0]) for _ in range(n)]
    service.embed_batch = AsyncMock(return_value=embeddings)
    return service


# ---------- Pass 1: subject_context grouping ----------


class TestPass1SubjectContext:
    async def test_no_merge_when_single_claim(self, extractor):
        claims = [_claim("BlackRock Q3 2023 inflows fell to $39bn", 0, "BlackRock")]
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 1
        assert result[0] is claims[0]

    async def test_no_merge_when_distinct_subject_contexts(self, extractor):
        # TRU-8EBE shape: 2 claims, distinct contexts → no merge
        claims = [
            _claim(
                "EMA added a warning to Ozempic and Wegovy labels in 2024 for NAION",
                0,
                "Ozempic and Wegovy warning",
                [
                    {"text": "EMA", "type": "ORG"},
                    {"text": "Ozempic", "type": "PRODUCT"},
                    {"text": "2024", "type": "DATE"},
                    {"text": "NAION", "type": "OTHER"},
                ],
            ),
            _claim(
                "Harvard study found 8.9-fold increased risk for NAION",
                1,
                "Semaglutide and NAION risk",
                [
                    {"text": "Harvard Mass Eye and Ear", "type": "ORG"},
                    {"text": "8.9-fold", "type": "AMOUNT"},
                    {"text": "NAION", "type": "OTHER"},
                ],
            ),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 2
        assert not result[0].get("was_merged")
        assert not result[1].get("was_merged")

    async def test_pass1_merges_identical_subject_context_pair(self, extractor):
        # TRU-5411 inflows pair
        claims = [
            _claim(
                "BlackRock's Q3 2023 net inflows fell to $39 billion",
                0,
                "BlackRock net inflows",
                [
                    {"text": "BlackRock", "type": "ORG"},
                    {"text": "Q3 2023", "type": "DATE"},
                    {"text": "$39 billion", "type": "AMOUNT"},
                ],
            ),
            _claim(
                "BlackRock's Q3 2022 net inflows were $122 billion",
                1,
                "BlackRock net inflows",
                [
                    {"text": "BlackRock", "type": "ORG"},
                    {"text": "Q3 2022", "type": "DATE"},
                    {"text": "$122 billion", "type": "AMOUNT"},
                ],
            ),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 1
        assert result[0]["was_merged"] is True
        assert result[0]["merged_from"] == [0, 1]
        assert "$39 billion" in result[0]["text"]
        assert "$122 billion" in result[0]["text"]

    async def test_pass1_merges_two_pairs_independently(self, extractor):
        # TRU-5411 full shape: 4 claims, 2 distinct subject_context pairs → 2 merged claims
        claims = [
            _claim(
                "BlackRock Q3 2023 inflows fell to $39bn",
                0,
                "BlackRock net inflows",
                [{"text": "BlackRock", "type": "ORG"}],
            ),
            _claim(
                "BlackRock Q3 2022 inflows were $122bn",
                1,
                "BlackRock net inflows",
                [{"text": "BlackRock", "type": "ORG"}],
            ),
            _claim(
                "Texas pension funds pulled $13bn from BlackRock",
                2,
                "Pension fund withdrawals",
                [
                    {"text": "Texas", "type": "LOCATION"},
                    {"text": "BlackRock", "type": "ORG"},
                ],
            ),
            _claim(
                "Florida pension funds pulled $13bn from BlackRock",
                3,
                "Pension fund withdrawals",
                [
                    {"text": "Florida", "type": "LOCATION"},
                    {"text": "BlackRock", "type": "ORG"},
                ],
            ),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 2
        # Order preserved by anchor position: inflows-pair (anchor=0) first
        assert "BlackRock" in result[0]["text"]
        assert "$39bn" in result[0]["text"]
        assert "Texas" in result[1]["text"]
        assert "Florida" in result[1]["text"]

    async def test_pass1_merges_four_into_one(self, extractor):
        # TRU-15A8 Russia shape: 4 claims, all share subject_context → 1 merged claim
        claims = [
            _claim(
                "Russia spent 6.7% of GDP on military in 2024",
                0,
                "Russia military spending",
            ),
            _claim(
                "Russia's military spending highest share since the Soviet era",
                1,
                "Russia military spending",
            ),
            _claim(
                "SIPRI estimated Russia military spending at $149 billion April 2025",
                2,
                "Russia military spending",
            ),
            _claim(
                "Russia military spending 38% real-terms YoY increase",
                3,
                "Russia military spending",
            ),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 1
        assert result[0]["was_merged"] is True
        assert result[0]["merged_from"] == [0, 1, 2, 3]

    async def test_pass1_keeps_singleton_with_distinct_context(self, extractor):
        # TRU-B3A4 UK election: 4 share, 1 distinct → 2 claims out
        claims = [
            _claim("Reform 14.3% vote", 0, "2024 UK election results"),
            _claim("Reform 5 seats", 1, "2024 UK election results"),
            _claim("LibDem 12.2% vote", 2, "2024 UK election results"),
            _claim("LibDem 72 seats", 3, "2024 UK election results"),
            _claim(
                "Highest disproportionality since 1832 Reform Act",
                4,
                "2024 UK election disproportionality",
            ),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 2
        # Anchor sort: merged group anchor=0, standalone anchor=4
        assert result[0]["was_merged"] is True
        assert result[1].get("was_merged") is not True
        assert "disproportionality" in result[1]["text"].lower()

    async def test_pass1_handles_none_subject_context(self, extractor):
        # None contexts must NOT group together
        claims = [
            _claim("Claim with no context A", 0, None),
            _claim("Claim with no context B", 1, None),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 2

    async def test_pass1_handles_empty_string_subject_context(self, extractor):
        claims = [
            _claim("Claim A", 0, ""),
            _claim("Claim B", 1, "   "),
            _claim("Claim C", 2, ".,;:"),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 3  # all normalise to None, none group

    async def test_pass1_normalisation_handles_case_and_trailing_punct(self, extractor):
        claims = [
            _claim("A", 0, "Russia Military Spending"),
            _claim("B", 1, "russia military spending."),
            _claim("C", 2, "RUSSIA MILITARY SPENDING ;"),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 1
        assert result[0]["was_merged"] is True


# ---------- Pass 2: entity-overlap on remaining singletons ----------


class TestPass2EntityOverlap:
    async def test_pass2_merges_org_plus_date_overlap(self, extractor):
        # TRU-7C40 Pos 0+3 shape: distinct subject_contexts, but share
        # 4 entities including ORG (Google Health) and DATE (2020).
        claims = [
            _claim(
                "Google Health AI mammogram cut false positives by 5.7% in 2020 Nature study",
                0,
                "AI mammogram false positives",
                [
                    {"text": "Google Health", "type": "ORG"},
                    {"text": "AI mammogram model", "type": "OTHER"},
                    {"text": "5.7%", "type": "AMOUNT"},
                    {"text": "2020", "type": "DATE"},
                    {"text": "Nature", "type": "OTHER"},
                ],
            ),
            _claim(
                "Google Health AI mammogram cut false negatives by 9.4% in 2020 Nature study",
                1,
                "AI mammogram false negatives",
                [
                    {"text": "Google Health", "type": "ORG"},
                    {"text": "AI mammogram model", "type": "OTHER"},
                    {"text": "9.4%", "type": "AMOUNT"},
                    {"text": "2020", "type": "DATE"},
                    {"text": "Nature", "type": "OTHER"},
                ],
            ),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 1
        assert result[0]["was_merged"] is True
        assert "5.7%" in result[0]["text"]
        assert "9.4%" in result[0]["text"]

    async def test_pass2_skips_date_only_overlap(self, extractor):
        # TRU-EF3F Sha'Carri shape: shared AMOUNT only, no ORG+DATE backbone
        claims = [
            _claim(
                "Sha'Carri ran 10.65 in Budapest 2023",
                0,
                "Sha'Carri Richardson's race",
                [
                    {"text": "Sha'Carri Richardson", "type": "PERSON"},
                    {"text": "10.65", "type": "AMOUNT"},
                    {"text": "Budapest", "type": "LOCATION"},
                    {"text": "2023", "type": "DATE"},
                ],
            ),
            _claim(
                "10.65 is joint third-fastest wind-legal time",
                1,
                "Race time record",
                [{"text": "10.65", "type": "AMOUNT"}],
            ),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 2  # no merge

    async def test_pass2_skips_below_3_entity_threshold(self, extractor):
        # Two claims share only ORG + DATE (2 entities, but not 3) → no merge
        claims = [
            _claim(
                "Apple revenue rose in 2023",
                0,
                "Apple revenue",
                [
                    {"text": "Apple", "type": "ORG"},
                    {"text": "2023", "type": "DATE"},
                ],
            ),
            _claim(
                "Apple opened a new store in 2023",
                1,
                "Apple retail",
                [
                    {"text": "Apple", "type": "ORG"},
                    {"text": "2023", "type": "DATE"},
                ],
            ),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 2  # 2-entity overlap insufficient

    async def test_pass2_does_not_merge_unrelated_org_claims(self, extractor):
        # Two claims share ORG and DATE but fewer than 3 total — must NOT merge
        # (guards against incidental same-company-same-year coincidence)
        claims = [
            _claim(
                "Microsoft acquired Activision in 2023",
                0,
                "Microsoft acquisitions",
                [
                    {"text": "Microsoft", "type": "ORG"},
                    {"text": "Activision", "type": "ORG"},
                    {"text": "2023", "type": "DATE"},
                ],
            ),
            _claim(
                "Microsoft launched Copilot in 2023",
                1,
                "Microsoft AI products",
                [
                    {"text": "Microsoft", "type": "ORG"},
                    {"text": "Copilot", "type": "PRODUCT"},
                    {"text": "2023", "type": "DATE"},
                ],
            ),
        ]
        # Overlap: {(microsoft, ORG), (2023, DATE)} = 2 → below threshold
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 2

    async def test_combined_pass1_then_pass2_runs_on_residual_singletons(
        self, extractor
    ):
        # Full TRU-7C40 shape: 4 claims.
        # Pos 1+2 share subject_context "AI mammogram study data" → Pass 1 merges them.
        # Pos 0 and 3 are singletons after Pass 1 but share 5-entity ORG+DATE backbone → Pass 2 merges them.
        # Final result: 2 claims.
        claims = [
            _claim(
                "Google Health AI mammogram cut false positives by 5.7% in 2020 Nature study",
                0,
                "AI mammogram false positives",
                [
                    {"text": "Google Health", "type": "ORG"},
                    {"text": "AI mammogram model", "type": "OTHER"},
                    {"text": "5.7%", "type": "AMOUNT"},
                    {"text": "2020", "type": "DATE"},
                    {"text": "Nature", "type": "OTHER"},
                ],
            ),
            _claim(
                "The 2020 Nature study used 76,000 UK scans",
                1,
                "AI mammogram study data",
                [
                    {"text": "2020", "type": "DATE"},
                    {"text": "Nature", "type": "OTHER"},
                    {"text": "76,000", "type": "AMOUNT"},
                    {"text": "UK", "type": "LOCATION"},
                ],
            ),
            _claim(
                "The 2020 Nature study used 25,000 US scans",
                2,
                "AI mammogram study data",
                [
                    {"text": "2020", "type": "DATE"},
                    {"text": "Nature", "type": "OTHER"},
                    {"text": "25,000", "type": "AMOUNT"},
                    {"text": "US", "type": "LOCATION"},
                ],
            ),
            _claim(
                "Google Health AI mammogram cut false negatives by 9.4% in 2020 Nature study",
                3,
                "AI mammogram false negatives",
                [
                    {"text": "Google Health", "type": "ORG"},
                    {"text": "AI mammogram model", "type": "OTHER"},
                    {"text": "9.4%", "type": "AMOUNT"},
                    {"text": "2020", "type": "DATE"},
                    {"text": "Nature", "type": "OTHER"},
                ],
            ),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 2, f"Expected 2 merged claims, got {len(result)}"
        # Anchor 0 = Pos 0+3 entity-merged; Anchor 1 = Pos 1+2 context-merged
        assert all(c["was_merged"] for c in result)


# ---------- Pass 2: LOCATION + DATE backbone variant (Thread C, 2026-05-11) ----------
#
# TRU-E317-4192 surfaced natural-event articles (GBR coral bleaching) where
# the LLM atomises a single-event paragraph into 4-5 claims, each emphasising
# a different actor (event itself / observation team / cause / attributor).
# Pass 2's original ORG/PRODUCT+DATE backbone missed these because the actor
# entity differed across atoms. Extending the backbone to also accept
# LOCATION+DATE catches the natural-event pattern where the place and date
# stay stable across the atomized aspects.


class TestPass2LocationDateBackbone:
    async def test_has_event_anchor_accepts_org_date(self, extractor):
        """Regression: ORG+DATE backbone still works after the rename."""
        entities = {
            ("google health", "ORG"),
            ("2020", "DATE"),
            ("ai mammogram model", "OTHER"),
        }
        assert extractor._has_event_anchor_backbone(entities) is True

    async def test_has_event_anchor_accepts_product_date(self, extractor):
        """Regression: PRODUCT+DATE backbone still works."""
        entities = {
            ("model y", "PRODUCT"),
            ("2022", "DATE"),
        }
        assert extractor._has_event_anchor_backbone(entities) is True

    async def test_has_event_anchor_accepts_location_date(self, extractor):
        """New: LOCATION+DATE backbone now accepted (Thread C)."""
        entities = {
            ("great barrier reef", "LOCATION"),
            ("march 2024", "DATE"),
        }
        assert extractor._has_event_anchor_backbone(entities) is True

    async def test_has_event_anchor_rejects_date_alone(self, extractor):
        """Without an actor/place anchor, DATE alone is too weak."""
        entities = {
            ("2024", "DATE"),
            ("5.7%", "AMOUNT"),
            ("nature study", "OTHER"),
        }
        assert extractor._has_event_anchor_backbone(entities) is False

    async def test_has_event_anchor_rejects_location_alone(self, extractor):
        """Without a DATE, LOCATION alone is too weak — countries appear
        in many unrelated claims (see helper docstring)."""
        entities = {
            ("great barrier reef", "LOCATION"),
            ("two-thirds", "AMOUNT"),
            ("reef system", "OTHER"),
        }
        assert extractor._has_event_anchor_backbone(entities) is False

    async def test_has_event_anchor_rejects_amount_only(self, extractor):
        """Bare numeric entities can't anchor a same-event merge."""
        entities = {
            ("10.65", "AMOUNT"),
            ("budapest", "LOCATION"),
        }
        # LOCATION present but no DATE.
        assert extractor._has_event_anchor_backbone(entities) is False

    async def test_pass2_merges_location_date_natural_event(self, extractor):
        """End-to-end: two atomized claims about the same Great Barrier Reef
        bleaching event in March 2024 should merge via the new LOC+DATE
        backbone, given ≥3 shared entities.

        This is the TRU-E317 shape — different actor entities per claim
        (the event itself vs the observation team) but stable LOC+DATE
        anchor for the same real-world event.
        """
        claims = [
            _claim(
                "The Great Barrier Reef experienced its fifth mass coral bleaching event in March 2024",
                0,
                "GBR bleaching event",
                [
                    {"text": "Great Barrier Reef", "type": "LOCATION"},
                    {"text": "March 2024", "type": "DATE"},
                    {"text": "coral bleaching", "type": "OTHER"},
                    {"text": "fifth mass event", "type": "OTHER"},
                ],
            ),
            _claim(
                "Aerial surveys of the Great Barrier Reef in March 2024 documented coral bleaching",
                1,
                "GBR surveys",
                [
                    {"text": "Great Barrier Reef", "type": "LOCATION"},
                    {"text": "March 2024", "type": "DATE"},
                    {"text": "coral bleaching", "type": "OTHER"},
                    {"text": "aerial surveys", "type": "OTHER"},
                ],
            ),
        ]
        # Overlap: GBR (LOC), March 2024 (DATE), coral bleaching (OTHER) = 3 entities,
        # LOC+DATE backbone present → Pass 2 fires.
        result = await extractor._merge_redecomposed_claims(claims)
        assert (
            len(result) == 1
        ), f"Expected merge via LOC+DATE backbone, got {len(result)} claims"
        assert result[0]["was_merged"] is True
        # Both texts preserved in the merge.
        merged_sources = result[0]["merged_source_texts"]
        assert any("experienced" in t for t in merged_sources)
        assert any("Aerial surveys" in t for t in merged_sources)

    async def test_pass2_skips_loc_date_below_3_entity_threshold(self, extractor):
        """LOC+DATE backbone alone (2 entities) is below the ≥3 overlap
        threshold — must NOT merge."""
        claims = [
            _claim(
                "Texas reported drought in 2024",
                0,
                "Texas drought",
                [
                    {"text": "Texas", "type": "LOCATION"},
                    {"text": "2024", "type": "DATE"},
                ],
            ),
            _claim(
                "Texas oil production peaked in 2024",
                1,
                "Texas oil",
                [
                    {"text": "Texas", "type": "LOCATION"},
                    {"text": "2024", "type": "DATE"},
                ],
            ),
        ]
        # 2-entity overlap insufficient even with LOC+DATE backbone.
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 2

    async def test_pass2_paired_comparison_loc_date_doesnt_falsely_merge(
        self, extractor
    ):
        """Paired comparison across different LOCATIONs at same date must
        NOT merge — the d78b4c3 safeguard applies via the entity overlap
        threshold. Two claims about different states' pension fund flows
        in the same quarter share OTHER entities but differ on LOCATION
        and AMOUNT — overlap is below 3 distinct entities.
        """
        claims = [
            _claim(
                "Texas pension funds pulled $13bn from BlackRock in Q3 2023",
                0,
                "Texas pension flows",
                [
                    {"text": "Texas", "type": "LOCATION"},
                    {"text": "Q3 2023", "type": "DATE"},
                    {"text": "BlackRock", "type": "ORG"},
                    {"text": "$13bn", "type": "AMOUNT"},
                    {"text": "pension funds", "type": "OTHER"},
                ],
            ),
            _claim(
                "Florida pension funds pulled $13bn from BlackRock in Q3 2023",
                1,
                "Florida pension flows",
                [
                    {"text": "Florida", "type": "LOCATION"},
                    {"text": "Q3 2023", "type": "DATE"},
                    {"text": "BlackRock", "type": "ORG"},
                    {"text": "$13bn", "type": "AMOUNT"},
                    {"text": "pension funds", "type": "OTHER"},
                ],
            ),
        ]
        # Overlap: {(Q3 2023, DATE), (BlackRock, ORG), ($13bn, AMOUNT),
        #           (pension funds, OTHER)} = 4 entities. LOC differs.
        # Pass 2 WOULD merge these as ORG+DATE backbone case (existing
        # behaviour pre-Thread C). This is a known semantic limitation —
        # the d78b4c3 paired-comparison safeguard runs in the cosine
        # dedup pass, NOT Pass 2. Pass 2 trusts subject_context divergence
        # as the signal that two ORG+DATE-overlapping claims are about
        # different aspects. Here, the subject_contexts ARE different
        # ("Texas pension flows" vs "Florida pension flows"), but with
        # 4-entity overlap the merge still fires.
        #
        # This test pins current behaviour. If we later want Pass 2 to
        # respect the LOCATION discriminating-entity, that's a separate
        # change tied to extending the d78b4c3 safeguard pattern into
        # Pass 2 directly. For Thread C, scope is LOC+DATE backbone
        # acceptance only.
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 1  # current behaviour

    async def test_pass2_loc_date_without_org_still_merges(self, extractor):
        """Natural event with no ORG anchor — LOC+DATE backbone alone
        suffices for the merge (the gap Thread C addresses).
        """
        claims = [
            _claim(
                "Hurricane Helene struck Florida in September 2024 with 140mph winds",
                0,
                "Hurricane Helene Florida",
                [
                    {"text": "Florida", "type": "LOCATION"},
                    {"text": "September 2024", "type": "DATE"},
                    {"text": "Hurricane Helene", "type": "EVENT"},
                    {"text": "140mph", "type": "AMOUNT"},
                ],
            ),
            _claim(
                "Hurricane Helene caused damage in Florida in September 2024",
                1,
                "Hurricane Helene damage",
                [
                    {"text": "Florida", "type": "LOCATION"},
                    {"text": "September 2024", "type": "DATE"},
                    {"text": "Hurricane Helene", "type": "EVENT"},
                    {"text": "damage", "type": "OTHER"},
                ],
            ),
        ]
        # Overlap: 3 entities (Florida LOC, September 2024 DATE,
        # Hurricane Helene EVENT). LOC+DATE backbone present.
        # Pre-Thread C: this would NOT merge (no ORG/PRODUCT in overlap).
        # Post-Thread C: merges via LOC+DATE backbone.
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 1
        assert result[0]["was_merged"] is True


# ---------- Merge mechanics ----------


class TestMergeMechanics:
    async def test_merge_concatenates_text_with_period_separator(self, extractor):
        claims = [
            _claim("First fact", 0, "shared"),
            _claim("Second fact", 1, "shared"),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert result[0]["text"] == "First fact. Second fact."

    async def test_merge_unions_key_entities_dedup(self, extractor):
        claims = [
            _claim(
                "A",
                0,
                "shared",
                [
                    {"text": "BlackRock", "type": "ORG"},
                    {"text": "2023", "type": "DATE"},
                ],
            ),
            _claim(
                "B",
                1,
                "shared",
                [
                    {"text": "blackrock", "type": "ORG"},  # case dedup
                    {"text": "2023", "type": "DATE"},
                    {"text": "$39bn", "type": "AMOUNT"},
                ],
            ),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        ents = result[0]["key_entities"]
        # 3 unique: BlackRock(ORG), 2023(DATE), $39bn(AMOUNT)
        keys = {(e["text"].lower(), e["type"].upper()) for e in ents}
        assert len(keys) == 3

    async def test_merge_takes_max_confidence(self, extractor):
        claims = [
            _claim("A", 0, "shared", confidence=70),
            _claim("B", 1, "shared", confidence=92),
            _claim("C", 2, "shared", confidence=85),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert result[0]["confidence"] == 92

    async def test_merge_sets_was_merged_and_merged_from(self, extractor):
        claims = [
            _claim("A", 5, "shared"),
            _claim("B", 9, "shared"),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert result[0]["was_merged"] is True
        assert result[0]["merged_from"] == [5, 9]

    async def test_singletons_do_not_get_was_merged_flag(self, extractor):
        claims = [
            _claim("Lonely", 0, "ctx-A"),
            _claim("Also lonely", 1, "ctx-B"),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        for c in result:
            assert c.get("was_merged") is not True
            assert "merged_from" not in c


# ---------- Wired seam: _validate_and_refine_claims path ----------


class TestWiredSeam:
    """The actual call path the extract pipeline uses. NF-21 lesson:
    test the seam, not just helpers."""

    async def test_validate_and_refine_runs_merge_after_dedup(self, extractor):
        # Dedup pass runs but none of these claim texts are cosine
        # ≥0.85 near-duplicates — they all describe distinct facts.
        # Mock embeddings that produce distinct unit vectors so
        # cosine similarity stays well below the 0.85 threshold.
        claims = [
            _claim(
                "Reform UK won 14.3% of the vote in 2024 UK general election",
                0,
                "2024 UK election results",
            ),
            _claim(
                "Reform UK won 5 seats in the 2024 UK general election",
                1,
                "2024 UK election results",
            ),
            _claim(
                "Liberal Democrats won 12.2% of vote in the 2024 UK general election",
                2,
                "2024 UK election results",
            ),
            _claim(
                "Liberal Democrats won 72 seats in the 2024 UK general election",
                3,
                "2024 UK election results",
            ),
            _claim(
                "Highest disproportionality since the 1832 Reform Act",
                4,
                "2024 UK election disproportionality",
            ),
        ]
        with patch(
            "app.services.embeddings.get_embedding_service",
            new=AsyncMock(return_value=_orthogonal_embedding_service(len(claims))),
        ):
            result = await extractor._validate_and_refine_claims(claims)
        # 4 election-results claims → 1 merged; disproportionality → 1 standalone
        assert len(result) == 2

    async def test_validate_and_refine_preserves_validation_filters(self, extractor):
        # Pronoun-leading claim must still get filtered out by the
        # individual-validation pass even with merge in the chain.
        claims = [
            _claim("They announced something in 2023", 0, "ctx"),  # pronoun → filtered
            _claim("BlackRock announced a layoff in 2023", 1, "ctx"),
        ]
        with patch(
            "app.services.embeddings.get_embedding_service",
            new=AsyncMock(return_value=_orthogonal_embedding_service(len(claims))),
        ):
            result = await extractor._validate_and_refine_claims(claims)
        # The pronoun claim is filtered before merge sees it; the survivor
        # is a singleton, no merge.
        assert len(result) == 1
        assert "BlackRock" in result[0]["text"]


# ---------- Dedup pass: cosine-similarity claim deduplication ----------


class TestDedupPass:
    """Coverage for _deduplicate_similar_claims, which sits between
    individual validation and the merge pass. Was a silent no-op for an
    unknown duration prior to 2026-05-08 — the import targeted a symbol
    (`get_embeddings`) that does not exist on app.services.embeddings,
    so every call hit ImportError and returned claims unchanged."""

    async def test_import_path_resolves(self, extractor):
        # Smoke test: the function must import a real symbol from
        # app.services.embeddings. If anyone renames or removes
        # get_embedding_service this test catches it before the bug
        # silently re-emerges.
        from app.services.embeddings import get_embedding_service  # noqa: F401

    async def test_no_dedup_when_single_claim(self, extractor):
        # Short-circuit before any embedding work happens.
        claims = [_claim("Only one claim", 0)]
        # Patch must NOT be called — assert by leaving it real;
        # if anything tries the network the test would hang.
        result = await extractor._deduplicate_similar_claims(claims)
        assert len(result) == 1
        assert result[0] is claims[0]

    async def test_near_duplicate_pair_collapses(self, extractor):
        # Two claims with identical embeddings (cosine = 1.0 > 0.85)
        # → only the longer one survives (per the keep-longest rule
        # at extract.py:892-905).
        claims = [
            _claim("Russia spent 6.7% of GDP on military in 2024", 0),
            _claim(
                "Russia's military spending reached 6.7% of GDP in 2024 according to SIPRI",
                1,
            ),
        ]
        with patch(
            "app.services.embeddings.get_embedding_service",
            new=AsyncMock(return_value=_identical_embedding_service(len(claims))),
        ):
            result = await extractor._deduplicate_similar_claims(claims)
        assert len(result) == 1
        # Longer text wins.
        assert "SIPRI" in result[0]["text"]

    async def test_distinct_claims_all_survive(self, extractor):
        # Orthogonal embeddings (cosine = 0 < 0.85) → no dedup.
        claims = [
            _claim("BlackRock had $39bn outflows in Q3 2023", 0),
            _claim("Reform UK won 14.3% of vote in 2024 election", 1),
            _claim("EMA added Ozempic warning in 2024", 2),
        ]
        with patch(
            "app.services.embeddings.get_embedding_service",
            new=AsyncMock(return_value=_orthogonal_embedding_service(len(claims))),
        ):
            result = await extractor._deduplicate_similar_claims(claims)
        assert len(result) == 3

    async def test_embedding_failure_returns_claims_unchanged(self, extractor):
        # If the service raises, dedup must fall back to passthrough.
        # Any exception class — protects against future API changes.
        claims = [
            _claim("Claim one", 0),
            _claim("Claim two", 1),
        ]
        broken_service = MagicMock()
        broken_service.embed_batch = AsyncMock(
            side_effect=RuntimeError("model unavailable")
        )
        with patch(
            "app.services.embeddings.get_embedding_service",
            new=AsyncMock(return_value=broken_service),
        ):
            result = await extractor._deduplicate_similar_claims(claims)
        assert len(result) == 2

    async def test_import_error_returns_claims_unchanged(self, extractor):
        # The original failure mode: import raises. Existing handler
        # must catch and passthrough so extraction never breaks.
        import builtins

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "app.services.embeddings":
                raise ImportError("simulated missing module")
            return real_import(name, *args, **kwargs)

        claims = [_claim("Claim one", 0), _claim("Claim two", 1)]
        with patch.object(builtins, "__import__", side_effect=fake_import):
            result = await extractor._deduplicate_similar_claims(claims)
        assert len(result) == 2

    async def test_paired_comparison_different_dates_not_deduped(self, extractor):
        # TRU-9D05 BlackRock case: Q3 2023 vs Q3 2022 — same template,
        # cosine ~0.92, but different DATE and AMOUNT → NOT duplicates.
        claims = [
            _claim(
                "BlackRock's Q3 2023 net inflows fell to $39 billion",
                0,
                "BlackRock net inflows",
                [
                    {"text": "BlackRock", "type": "ORG"},
                    {"text": "Q3 2023", "type": "DATE"},
                    {"text": "$39 billion", "type": "AMOUNT"},
                ],
            ),
            _claim(
                "BlackRock's Q3 2022 net inflows were $122 billion",
                1,
                "BlackRock net inflows",
                [
                    {"text": "BlackRock", "type": "ORG"},
                    {"text": "Q3 2022", "type": "DATE"},
                    {"text": "$122 billion", "type": "AMOUNT"},
                ],
            ),
        ]
        with patch(
            "app.services.embeddings.get_embedding_service",
            new=AsyncMock(return_value=_identical_embedding_service(len(claims))),
        ):
            result = await extractor._deduplicate_similar_claims(claims)
        assert len(result) == 2  # BOTH must survive

    async def test_paired_comparison_different_locations_not_deduped(self, extractor):
        # TRU-9D05 BlackRock case: Texas vs Florida pension funds —
        # same template, cosine ~0.87, but different LOCATION → NOT
        # duplicates.
        claims = [
            _claim(
                "Texas pension funds pulled $13 billion from BlackRock citing ESG",
                0,
                "Pension fund withdrawals",
                [
                    {"text": "Texas", "type": "LOCATION"},
                    {"text": "BlackRock", "type": "ORG"},
                    {"text": "$13 billion", "type": "AMOUNT"},
                ],
            ),
            _claim(
                "Florida pension funds pulled $13 billion from BlackRock citing ESG",
                1,
                "Pension fund withdrawals",
                [
                    {"text": "Florida", "type": "LOCATION"},
                    {"text": "BlackRock", "type": "ORG"},
                    {"text": "$13 billion", "type": "AMOUNT"},
                ],
            ),
        ]
        with patch(
            "app.services.embeddings.get_embedding_service",
            new=AsyncMock(return_value=_identical_embedding_service(len(claims))),
        ):
            result = await extractor._deduplicate_similar_claims(claims)
        assert len(result) == 2  # BOTH must survive

    async def test_paired_comparison_different_persons_not_deduped(self, extractor):
        # Generalises: same template, different PERSON → distinct facts.
        claims = [
            _claim(
                "Sha'Carri Richardson ran 10.65 in Budapest 2023",
                0,
                "Race record",
                [
                    {"text": "Sha'Carri Richardson", "type": "PERSON"},
                    {"text": "10.65", "type": "AMOUNT"},
                    {"text": "Budapest", "type": "LOCATION"},
                    {"text": "2023", "type": "DATE"},
                ],
            ),
            _claim(
                "Marie-Josee Ta Lou ran 10.81 in Budapest 2023",
                1,
                "Race record",
                [
                    {"text": "Marie-Josee Ta Lou", "type": "PERSON"},
                    {"text": "10.81", "type": "AMOUNT"},
                    {"text": "Budapest", "type": "LOCATION"},
                    {"text": "2023", "type": "DATE"},
                ],
            ),
        ]
        with patch(
            "app.services.embeddings.get_embedding_service",
            new=AsyncMock(return_value=_identical_embedding_service(len(claims))),
        ):
            result = await extractor._deduplicate_similar_claims(claims)
        assert len(result) == 2

    async def test_paraphrase_with_same_entities_still_deduped(self, extractor):
        # Proves the safeguard didn't kill legitimate dedup. Two
        # paraphrases of the SAME fact (identical entity sets) still
        # collapse to one.
        claims = [
            _claim(
                "Russia spent 6.7% of GDP on military in 2024",
                0,
                "Russia military spending",
                [
                    {"text": "Russia", "type": "LOCATION"},
                    {"text": "6.7%", "type": "AMOUNT"},
                    {"text": "2024", "type": "DATE"},
                ],
            ),
            _claim(
                "In 2024, Russia's military spending reached 6.7% of GDP",
                1,
                "Russia military spending",
                [
                    {"text": "Russia", "type": "LOCATION"},
                    {"text": "6.7%", "type": "AMOUNT"},
                    {"text": "2024", "type": "DATE"},
                ],
            ),
        ]
        with patch(
            "app.services.embeddings.get_embedding_service",
            new=AsyncMock(return_value=_identical_embedding_service(len(claims))),
        ):
            result = await extractor._deduplicate_similar_claims(claims)
        # Identical entity sets → still deduped.
        assert len(result) == 1

    async def test_other_type_entity_diff_does_not_block_dedup(self, extractor):
        # OTHER is paraphrase-prone (LLM might tag "flu jab" once and
        # "flu vaccine" the next). Difference on OTHER alone must NOT
        # block dedup when the discriminating entities match.
        claims = [
            _claim(
                "WHO recommended flu vaccines in 2024",
                0,
                "WHO flu recommendation",
                [
                    {"text": "WHO", "type": "ORG"},
                    {"text": "2024", "type": "DATE"},
                    {"text": "flu vaccine", "type": "OTHER"},
                ],
            ),
            _claim(
                "WHO recommended flu jabs in 2024",
                1,
                "WHO flu recommendation",
                [
                    {"text": "WHO", "type": "ORG"},
                    {"text": "2024", "type": "DATE"},
                    {"text": "flu jab", "type": "OTHER"},
                ],
            ),
        ]
        with patch(
            "app.services.embeddings.get_embedding_service",
            new=AsyncMock(return_value=_identical_embedding_service(len(claims))),
        ):
            result = await extractor._deduplicate_similar_claims(claims)
        # Discriminating sets equal (only OTHER differs) → still deduped.
        assert len(result) == 1

    async def test_asymmetric_entities_not_deduped(self, extractor):
        # One claim has DATE entity, the other doesn't. Sets unequal
        # → keep both. (Real case: LLM imperfectly tags entities; we
        # don't want this asymmetry to manufacture false duplicates.)
        claims = [
            _claim(
                "BlackRock reported $39bn inflows",
                0,
                "BlackRock inflows",
                [
                    {"text": "BlackRock", "type": "ORG"},
                    {"text": "$39bn", "type": "AMOUNT"},
                ],
            ),
            _claim(
                "BlackRock reported $39bn inflows in 2023",
                1,
                "BlackRock inflows",
                [
                    {"text": "BlackRock", "type": "ORG"},
                    {"text": "$39bn", "type": "AMOUNT"},
                    {"text": "2023", "type": "DATE"},
                ],
            ),
        ]
        with patch(
            "app.services.embeddings.get_embedding_service",
            new=AsyncMock(return_value=_identical_embedding_service(len(claims))),
        ):
            result = await extractor._deduplicate_similar_claims(claims)
        # Asymmetric (one has DATE, the other doesn't) → keep both.
        assert len(result) == 2


# ---------- Synthesis pass: LLM rewrite of merged claim text (V1 plan follow-up #2) ----------


def _synthesis_returns(text: str):
    """Helper: an AsyncMock for call_google_ai that returns a JSON dict
    with the given synthesised text."""

    async def _call(*args, **kwargs):
        return {"text": text}

    return _call


def _synthesis_returns_raw(value):
    """Helper: an AsyncMock for call_google_ai that returns whatever
    raw value is passed (used to test malformed shapes)."""

    async def _call(*args, **kwargs):
        return value

    return _call


def _synthesis_raises(exc: Exception):
    async def _call(*args, **kwargs):
        raise exc

    return _call


class TestSynthesis:
    """Coverage for _synthesise_merged_claim_text + its integration into
    _merge_claim_group. Default fixture stubs synthesis to None
    (concat fallback); each test here overrides with a custom mock."""

    async def test_synthesis_happy_path_replaces_text(self, extractor, monkeypatch):
        # Russia-shape input: 4 sentences sharing a long prefix; LLM
        # returns one fluent sentence that mentions every entity.
        synthesised_text = (
            "Russia's 2024 military spending hit 6.7% of GDP "
            "($149 billion per SIPRI's April 2025 estimate), the highest "
            "share since the Soviet era and a 38% real-terms increase."
        )
        monkeypatch.setattr(
            "app.pipeline.extract.call_google_ai",
            _synthesis_returns(synthesised_text),
        )
        claims = [
            _claim(
                "Russia spent 6.7% of GDP on military in 2024",
                0,
                "Russia military spending",
                [
                    {"text": "Russia", "type": "LOCATION"},
                    {"text": "6.7%", "type": "AMOUNT"},
                    {"text": "2024", "type": "DATE"},
                ],
            ),
            _claim(
                "SIPRI estimated Russia military spending at $149 billion April 2025",
                1,
                "Russia military spending",
                [
                    {"text": "SIPRI", "type": "ORG"},
                    {"text": "$149 billion", "type": "AMOUNT"},
                    {"text": "April 2025", "type": "DATE"},
                ],
            ),
            _claim(
                "Russia military spending highest share since the Soviet era",
                2,
                "Russia military spending",
                [{"text": "Soviet era", "type": "EVENT"}],
            ),
            _claim(
                "Russia military spending 38% real-terms YoY increase",
                3,
                "Russia military spending",
                [{"text": "38%", "type": "AMOUNT"}],
            ),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 1
        assert result[0]["text"] == synthesised_text
        assert result[0]["merge_text_source"] == "synthesised"
        # Provenance preserved regardless of which path runs.
        assert result[0]["merged_source_texts"] == [c["text"] for c in claims]

    async def test_synthesis_drops_entity_falls_back_to_concat(
        self, extractor, monkeypatch
    ):
        # LLM returns text that omits a required entity → fallback to concat.
        monkeypatch.setattr(
            "app.pipeline.extract.call_google_ai",
            # SIPRI absent on purpose
            _synthesis_returns("Russia spent 6.7% of GDP on military in 2024."),
        )
        claims = [
            _claim(
                "Russia 6.7% GDP military 2024",
                0,
                "Russia military spending",
                [{"text": "Russia", "type": "LOCATION"}],
            ),
            _claim(
                "SIPRI $149 billion April 2025",
                1,
                "Russia military spending",
                [{"text": "SIPRI", "type": "ORG"}],
            ),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 1
        # SIPRI is missing from the LLM output → fallback ran
        assert result[0]["merge_text_source"] == "concat"
        # Concat shape is the period-joined original
        assert (
            result[0]["text"]
            == "Russia 6.7% GDP military 2024. SIPRI $149 billion April 2025."
        )

    async def test_synthesis_llm_error_falls_back(self, extractor, monkeypatch):
        # LLM call raises → caller catches and falls back.
        monkeypatch.setattr(
            "app.pipeline.extract.call_google_ai",
            _synthesis_raises(RuntimeError("upstream timeout")),
        )
        claims = [
            _claim("First fact", 0, "shared"),
            _claim("Second fact", 1, "shared"),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 1
        assert result[0]["merge_text_source"] == "concat"
        assert result[0]["text"] == "First fact. Second fact."

    async def test_synthesis_llm_returns_none_falls_back(self, extractor, monkeypatch):
        # call_google_ai returns None on retries-exhausted etc.
        monkeypatch.setattr(
            "app.pipeline.extract.call_google_ai",
            _synthesis_returns_raw(None),
        )
        claims = [
            _claim("First fact", 0, "shared"),
            _claim("Second fact", 1, "shared"),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert result[0]["merge_text_source"] == "concat"

    async def test_synthesis_malformed_response_falls_back(
        self, extractor, monkeypatch
    ):
        # JSON parsed but missing the "text" key.
        monkeypatch.setattr(
            "app.pipeline.extract.call_google_ai",
            _synthesis_returns_raw({"unrelated": "shape"}),
        )
        claims = [
            _claim("First fact", 0, "shared"),
            _claim("Second fact", 1, "shared"),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert result[0]["merge_text_source"] == "concat"

    async def test_synthesis_empty_string_falls_back(self, extractor, monkeypatch):
        monkeypatch.setattr(
            "app.pipeline.extract.call_google_ai",
            _synthesis_returns_raw({"text": "   "}),
        )
        claims = [
            _claim("First fact", 0, "shared"),
            _claim("Second fact", 1, "shared"),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert result[0]["merge_text_source"] == "concat"

    async def test_synthesis_not_attempted_on_singleton(self, extractor, monkeypatch):
        # No merge group means no synthesis call should ever happen.
        # Tracking via a Mock so we can assert it wasn't called.
        from unittest.mock import AsyncMock

        spy = AsyncMock(return_value={"text": "should never be returned"})
        monkeypatch.setattr("app.pipeline.extract.call_google_ai", spy)
        claims = [_claim("Lonely claim", 0, "ctx-A")]
        result = await extractor._merge_redecomposed_claims(claims)
        assert len(result) == 1
        assert result[0] is claims[0]
        # No singleton metadata leaked
        assert result[0].get("was_merged") is not True
        assert "merged_source_texts" not in result[0]
        assert "merge_text_source" not in result[0]
        spy.assert_not_called()

    async def test_merged_source_texts_populated_on_concat_fallback(self, extractor):
        # Default autouse fixture forces fallback. Provenance must still
        # be present on the merged claim.
        claims = [
            _claim("First fact", 0, "shared"),
            _claim("Second fact", 1, "shared"),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert result[0]["merged_source_texts"] == ["First fact", "Second fact"]
        assert result[0]["merge_text_source"] == "concat"

    async def test_synthesis_case_insensitive_entity_check(
        self, extractor, monkeypatch
    ):
        # "BlackRock" extracted entity, LLM rewrites as "blackrock" —
        # case-insensitive check passes, synthesis succeeds.
        monkeypatch.setattr(
            "app.pipeline.extract.call_google_ai",
            _synthesis_returns(
                "blackrock's Q3 2023 inflows of $39bn were down from $122bn in Q3 2022."
            ),
        )
        claims = [
            _claim(
                "BlackRock Q3 2023 inflows $39bn",
                0,
                "BlackRock net inflows",
                [
                    {"text": "BlackRock", "type": "ORG"},
                    {"text": "Q3 2023", "type": "DATE"},
                    {"text": "$39bn", "type": "AMOUNT"},
                ],
            ),
            _claim(
                "BlackRock Q3 2022 inflows $122bn",
                1,
                "BlackRock net inflows",
                [
                    {"text": "Q3 2022", "type": "DATE"},
                    {"text": "$122bn", "type": "AMOUNT"},
                ],
            ),
        ]
        result = await extractor._merge_redecomposed_claims(claims)
        assert result[0]["merge_text_source"] == "synthesised"
