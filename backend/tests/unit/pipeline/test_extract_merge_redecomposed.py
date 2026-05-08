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
    def test_no_merge_when_single_claim(self, extractor):
        claims = [_claim("BlackRock Q3 2023 inflows fell to $39bn", 0, "BlackRock")]
        result = extractor._merge_redecomposed_claims(claims)
        assert len(result) == 1
        assert result[0] is claims[0]

    def test_no_merge_when_distinct_subject_contexts(self, extractor):
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
        result = extractor._merge_redecomposed_claims(claims)
        assert len(result) == 2
        assert not result[0].get("was_merged")
        assert not result[1].get("was_merged")

    def test_pass1_merges_identical_subject_context_pair(self, extractor):
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
        result = extractor._merge_redecomposed_claims(claims)
        assert len(result) == 1
        assert result[0]["was_merged"] is True
        assert result[0]["merged_from"] == [0, 1]
        assert "$39 billion" in result[0]["text"]
        assert "$122 billion" in result[0]["text"]

    def test_pass1_merges_two_pairs_independently(self, extractor):
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
        result = extractor._merge_redecomposed_claims(claims)
        assert len(result) == 2
        # Order preserved by anchor position: inflows-pair (anchor=0) first
        assert "BlackRock" in result[0]["text"]
        assert "$39bn" in result[0]["text"]
        assert "Texas" in result[1]["text"]
        assert "Florida" in result[1]["text"]

    def test_pass1_merges_four_into_one(self, extractor):
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
        result = extractor._merge_redecomposed_claims(claims)
        assert len(result) == 1
        assert result[0]["was_merged"] is True
        assert result[0]["merged_from"] == [0, 1, 2, 3]

    def test_pass1_keeps_singleton_with_distinct_context(self, extractor):
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
        result = extractor._merge_redecomposed_claims(claims)
        assert len(result) == 2
        # Anchor sort: merged group anchor=0, standalone anchor=4
        assert result[0]["was_merged"] is True
        assert result[1].get("was_merged") is not True
        assert "disproportionality" in result[1]["text"].lower()

    def test_pass1_handles_none_subject_context(self, extractor):
        # None contexts must NOT group together
        claims = [
            _claim("Claim with no context A", 0, None),
            _claim("Claim with no context B", 1, None),
        ]
        result = extractor._merge_redecomposed_claims(claims)
        assert len(result) == 2

    def test_pass1_handles_empty_string_subject_context(self, extractor):
        claims = [
            _claim("Claim A", 0, ""),
            _claim("Claim B", 1, "   "),
            _claim("Claim C", 2, ".,;:"),
        ]
        result = extractor._merge_redecomposed_claims(claims)
        assert len(result) == 3  # all normalise to None, none group

    def test_pass1_normalisation_handles_case_and_trailing_punct(self, extractor):
        claims = [
            _claim("A", 0, "Russia Military Spending"),
            _claim("B", 1, "russia military spending."),
            _claim("C", 2, "RUSSIA MILITARY SPENDING ;"),
        ]
        result = extractor._merge_redecomposed_claims(claims)
        assert len(result) == 1
        assert result[0]["was_merged"] is True


# ---------- Pass 2: entity-overlap on remaining singletons ----------


class TestPass2EntityOverlap:
    def test_pass2_merges_org_plus_date_overlap(self, extractor):
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
        result = extractor._merge_redecomposed_claims(claims)
        assert len(result) == 1
        assert result[0]["was_merged"] is True
        assert "5.7%" in result[0]["text"]
        assert "9.4%" in result[0]["text"]

    def test_pass2_skips_date_only_overlap(self, extractor):
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
        result = extractor._merge_redecomposed_claims(claims)
        assert len(result) == 2  # no merge

    def test_pass2_skips_below_3_entity_threshold(self, extractor):
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
        result = extractor._merge_redecomposed_claims(claims)
        assert len(result) == 2  # 2-entity overlap insufficient

    def test_pass2_does_not_merge_unrelated_org_claims(self, extractor):
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
        result = extractor._merge_redecomposed_claims(claims)
        assert len(result) == 2

    def test_combined_pass1_then_pass2_runs_on_residual_singletons(self, extractor):
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
        result = extractor._merge_redecomposed_claims(claims)
        assert len(result) == 2, f"Expected 2 merged claims, got {len(result)}"
        # Anchor 0 = Pos 0+3 entity-merged; Anchor 1 = Pos 1+2 context-merged
        assert all(c["was_merged"] for c in result)


# ---------- Merge mechanics ----------


class TestMergeMechanics:
    def test_merge_concatenates_text_with_period_separator(self, extractor):
        claims = [
            _claim("First fact", 0, "shared"),
            _claim("Second fact", 1, "shared"),
        ]
        result = extractor._merge_redecomposed_claims(claims)
        assert result[0]["text"] == "First fact. Second fact."

    def test_merge_unions_key_entities_dedup(self, extractor):
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
        result = extractor._merge_redecomposed_claims(claims)
        ents = result[0]["key_entities"]
        # 3 unique: BlackRock(ORG), 2023(DATE), $39bn(AMOUNT)
        keys = {(e["text"].lower(), e["type"].upper()) for e in ents}
        assert len(keys) == 3

    def test_merge_takes_max_confidence(self, extractor):
        claims = [
            _claim("A", 0, "shared", confidence=70),
            _claim("B", 1, "shared", confidence=92),
            _claim("C", 2, "shared", confidence=85),
        ]
        result = extractor._merge_redecomposed_claims(claims)
        assert result[0]["confidence"] == 92

    def test_merge_sets_was_merged_and_merged_from(self, extractor):
        claims = [
            _claim("A", 5, "shared"),
            _claim("B", 9, "shared"),
        ]
        result = extractor._merge_redecomposed_claims(claims)
        assert result[0]["was_merged"] is True
        assert result[0]["merged_from"] == [5, 9]

    def test_singletons_do_not_get_was_merged_flag(self, extractor):
        claims = [
            _claim("Lonely", 0, "ctx-A"),
            _claim("Also lonely", 1, "ctx-B"),
        ]
        result = extractor._merge_redecomposed_claims(claims)
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
