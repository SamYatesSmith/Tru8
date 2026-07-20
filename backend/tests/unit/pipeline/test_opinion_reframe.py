"""Phase 1a (decoupling): opinion-reframe flag gating, hint plumbing, entry gate.

Pins the §16 design guarantees (audit/2026-07-15_decoupling_build_plan.md):
- flag OFF → extraction system prompt byte-identical (no reframe rule text);
- flag ON  → rule inserted exactly once at the Rule 6 anchor;
- ExtractedClaim round-trips the non-binding ``type_hint``;
- check 4 (subjective language) de-weights a hinted claim's confidence, never
  drops it. NOTE (verifier, 2026-07-16): checks 1-3 are NOT exempted — a
  hinted claim in a procedural-negative shape ("X failed to …") can still be
  dropped/stripped by check 1; that is in-spec for 1a and a Phase 1b battery
  case, not a pinned guarantee here;
- ``derive_entry_mode``: every single claim is "focused" now — the
  single-opinion confirm-pause was DROPPED (2026-07-20, founder). A normative
  hint no longer routes to the selection pause; the decoupling runs silently
  in phase 2. Everything else behaves exactly as before.
"""

import pytest

from app.core.config import settings
from app.pipeline.extract import (
    _OPINION_REFRAME_RULE,
    _RULE6_ANCHOR,
    ClaimExtractor,
    ExtractedClaim,
)
from app.pipeline.runner import derive_entry_mode


# ── Flag gating: prompt identity ─────────────────────────────────────────────


def test_flag_off_prompt_has_no_reframe_rule(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_OPINION_REFRAME", False)
    prompt = ClaimExtractor().system_prompt
    assert "EVALUATIVE MAIN-PREDICATE CLAIMS" not in prompt
    assert "type_hint" not in prompt
    assert _RULE6_ANCHOR in prompt  # anchor present so the ON path can insert


def test_flag_on_inserts_rule_once_at_anchor(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_OPINION_REFRAME", True)
    prompt = ClaimExtractor().system_prompt
    assert prompt.count(_OPINION_REFRAME_RULE) == 1
    # Inserted AT the anchor: anchor immediately followed by the rule.
    assert (_RULE6_ANCHOR + _OPINION_REFRAME_RULE) in prompt


def test_flag_on_prompt_differs_only_by_the_rule(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_OPINION_REFRAME", False)
    off = ClaimExtractor().system_prompt
    monkeypatch.setattr(settings, "ENABLE_OPINION_REFRAME", True)
    on = ClaimExtractor().system_prompt
    # Removing the inserted rule from ON must reproduce OFF byte-for-byte.
    assert on.replace(_OPINION_REFRAME_RULE, "", 1) == off


def test_rule_text_is_format_safe():
    # The system prompt goes through .format(); a stray single brace in the
    # inserted rule would raise at extraction time.
    assert "{" not in _OPINION_REFRAME_RULE.replace("{{", "").replace("}}", "")


# ── Schema round-trip ────────────────────────────────────────────────────────


def test_extracted_claim_type_hint_roundtrip():
    c = ExtractedClaim(
        text="The proposed merger is a real danger to American democracy",
        type_hint="normative",
    )
    assert c.type_hint == "normative"


def test_extracted_claim_type_hint_defaults_none():
    c = ExtractedClaim(text="UK inflation fell below 3% in 2024")
    assert c.type_hint is None


# ── Validation never drops a hinted claim ────────────────────────────────────


@pytest.mark.asyncio
async def test_validation_preserves_hinted_claim_and_never_drops(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_OPINION_REFRAME", True)
    extractor = ClaimExtractor()
    claims = [
        {
            "text": (
                "The Warner Bros-Paramount merger is arguably a real danger "
                "to American democracy"
            ),
            "position": 0,
            "confidence": 90,
            "category": None,
            "subject_context": "media merger",
            "key_entities": [],
            "type_hint": "normative",
        }
    ]
    validated = await extractor._validate_and_refine_claims(claims)
    assert len(validated) == 1, "check 4 must de-weight, never drop"
    assert validated[0]["type_hint"] == "normative"
    # "arguably" is in the subjective-word list → confidence de-weighted ×0.75.
    assert validated[0]["confidence"] == int(90 * 0.75)
    assert validated[0]["has_subjective_language"] is True


# ── Entry-mode gate ──────────────────────────────────────────────────────────


def test_single_plain_claim_stays_focused():
    assert derive_entry_mode([{"text": "x", "position": 0}]) == "focused"


def test_single_normative_hinted_claim_stays_focused_pause_dropped(monkeypatch):
    # 2026-07-20: the single-opinion confirm-pause was DROPPED. A normative
    # single claim now flows focused like any other — the decoupling runs
    # silently in phase 2. True regardless of the flag.
    monkeypatch.setattr(settings, "ENABLE_OPINION_REFRAME", True)
    assert (
        derive_entry_mode([{"text": "x", "position": 0, "type_hint": "normative"}])
        == "focused"
    )


def test_hinted_claim_with_flag_off_stays_focused(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_OPINION_REFRAME", False)
    assert (
        derive_entry_mode([{"text": "x", "position": 0, "type_hint": "normative"}])
        == "focused"
    )


def test_single_claim_with_other_hint_value_stays_focused(monkeypatch):
    # Every single claim is focused now — no hint value routes to a pause.
    monkeypatch.setattr(settings, "ENABLE_OPINION_REFRAME", True)
    assert (
        derive_entry_mode([{"text": "x", "position": 0, "type_hint": "legal"}])
        == "focused"
    )
    assert (
        derive_entry_mode([{"text": "x", "position": 0, "type_hint": None}])
        == "focused"
    )


def test_multi_claim_always_article_regardless_of_hints():
    claims = [
        {"text": "a", "position": 0, "type_hint": "normative"},
        {"text": "b", "position": 1},
    ]
    assert derive_entry_mode(claims) == "article"


# ── D-1 cache half: extraction cache identity varies with the flag ───────────


@pytest.mark.asyncio
async def test_extraction_cache_key_fingerprints_the_flag(monkeypatch):
    from app.workers.pipeline import extract_claims_with_cache

    seen_model_names = []

    class FakeCache:
        async def get_cached_claim_extraction(self, content, model_name):
            seen_model_names.append(model_name)
            # Short-circuit so no LLM call is made.
            return [{"text": "cached claim about something", "position": 0}]

    monkeypatch.setattr(settings, "ENABLE_OPINION_REFRAME", False)
    await extract_claims_with_cache("some content", {}, FakeCache())
    monkeypatch.setattr(settings, "ENABLE_OPINION_REFRAME", True)
    await extract_claims_with_cache("some content", {}, FakeCache())
    # Flag off keeps today's key untouched; flag on gets its own namespace.
    assert seen_model_names == ["gpt-4o-mini", "gpt-4o-mini+reframe"]


# ── §20 slice 2: the grounds-stage wiring gate ───────────────────────────────


def test_grounds_gate_flag_off_never_fires(monkeypatch):
    from app.pipeline.runner import should_apply_grounds

    monkeypatch.setattr(settings, "ENABLE_OPINION_REFRAME", False)
    # Even a persisted stale hint must not trigger after a rollback (D-1 rule).
    assert should_apply_grounds({"text": "x", "type_hint": "normative"}) is False
    assert should_apply_grounds({"text": "x"}) is False


def test_grounds_gate_flag_on_requires_the_hint(monkeypatch):
    from app.pipeline.runner import should_apply_grounds

    monkeypatch.setattr(settings, "ENABLE_OPINION_REFRAME", True)
    assert should_apply_grounds({"text": "x", "type_hint": "normative"}) is True
    assert should_apply_grounds({"text": "x", "type_hint": None}) is False
    assert should_apply_grounds({"text": "x"}) is False
    # Empirical claims never reach the stage regardless of other metadata.
    assert should_apply_grounds({"text": "x", "claim_type": "statistical"}) is False


def test_claim_model_persists_type_hint():
    """§20.6(3a): the hint must survive the selection pause — the phase-2 DB
    reload is the ONLY path a hinted claim takes (confirm step always pauses).
    Pins the column's existence; the reload dict is pinned by inspection of
    runner.py (type_hint included in the claim_dict rebuild)."""
    from app.models.check import Claim

    claim = Claim(check_id="c1", text="t", position=0, type_hint="normative")
    assert claim.type_hint == "normative"
    assert Claim(check_id="c1", text="t", position=0).type_hint is None
