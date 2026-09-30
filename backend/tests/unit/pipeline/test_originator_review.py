"""Originator review (A− H4 class D): lower-only, verified-cue, fail-safe.

Design: audit/2026-09-30_classify_originator_design.md. Hosts here are
invented; none comes from the held-out Astra pools the eval judges on.
"""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.services import originator_review as orv

CUE = "according to the Office for National Statistics"


def _item(i=0, **over):
    item = {
        "title": f"What the figures mean {i}",
        "url": f"https://explainer-{i}.example.org/guide",
        "snippet": f"Prices rose, {CUE}, in the year to May.",
        "tier": "primary",
        "evidence_type": "data",
        "classification_method": "llm",
    }
    item.update(over)
    return item


def _answer(*rows):
    return AsyncMock(return_value={"items": list(rows)})


@pytest.fixture(autouse=True)
def _enabled():
    with patch.object(orv.settings, "ENABLE_ORIGINATOR_REVIEW", True, create=True):
        yield


class TestCandidates:
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "over",
        [
            {"tier": "reporting"},
            {"tier": "commentary"},
            {"classification_method": "llm+override"},
            {"classification_method": "heuristic"},
            {"classification_method": "tracker_cap"},
            {"external_source_provider": "FRED"},
            {"url": "https://www.ons.gov.uk/economy/inflation"},
            {"metadata": {"originator_review": {"status": "reviewed"}}},
        ],
    )
    def test_not_a_candidate(self, over):
        assert not orv.is_candidate(_item(**over))

    @pytest.mark.unit
    def test_model_judged_primary_on_silent_host_is_a_candidate(self):
        assert orv.is_candidate(_item())


class TestDecisions:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_relays_with_verified_cue_lowers_to_reporting(self):
        item = _item()
        stats = await orv.review_originators(
            [item],
            _answer(
                {
                    "index": 0,
                    "originator": "Office for National Statistics",
                    "role": "relays",
                    "cue": CUE,
                }
            ),
        )
        assert item["tier"] == "reporting"
        assert item["classification_method"] == "originator_review"
        assert item["evidence_type"] == "data"  # type is never touched
        receipt = item["metadata"]["originator_review"]
        assert receipt["from_tier"] == "primary" and receipt["to_tier"] == "reporting"
        assert receipt["cue"] == CUE and receipt["cue_verified"]
        assert receipt["input_kind"] == "snippet"
        assert {k: stats[k] for k in ("candidates", "lowered", "calls")} == {
            "candidates": 1,
            "lowered": 1,
            "calls": 1,
        }
        assert len(stats["call_seconds"]) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_user_content_with_cue_lowers(self):
        item = _item(
            snippet="Posted by a user: we switched journal mode and it fixed our locks."
        )
        await orv.review_originators(
            [item],
            _answer(
                {
                    "index": 0,
                    "originator": "a forum user",
                    "role": "user_content",
                    "cue": "Posted by a user",
                }
            ),
        )
        assert item["tier"] == "reporting"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.parametrize("role", ["originates", "hosts_original", "unclear"])
    async def test_non_lowering_roles_keep_primary(self, role):
        item = _item()
        await orv.review_originators(
            [item],
            _answer(
                {
                    "index": 0,
                    # A verified cue, so only the role can keep the tier.
                    "originator": "Office for National Statistics",
                    "role": role,
                    "cue": CUE,
                }
            ),
        )
        assert item["tier"] == "primary"
        assert item["classification_method"] == "llm"
        assert item["metadata"]["originator_review"]["role"] == role

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "cue",
        [
            "according to the Office of Budget Responsibility",  # not in text
            "ONS said",  # shorter than 12 chars
            "",
            CUE.upper(),  # exact substring only, no normalisation
        ],
    )
    async def test_relays_without_verified_cue_changes_nothing(self, cue):
        item = _item()
        await orv.review_originators(
            [item],
            _answer(
                {
                    "index": 0,
                    "originator": "Office for National Statistics",
                    "role": "relays",
                    "cue": cue,
                }
            ),
        )
        assert item["tier"] == "primary"
        receipt = item["metadata"]["originator_review"]
        assert receipt["status"] == "invalid"
        assert receipt["invalid_reason"] == "cue_not_verified"
        assert receipt["cue"] == ""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unknown_role_is_invalid(self):
        item = _item()
        await orv.review_originators(
            [item],
            _answer({"index": 0, "originator": "x", "role": "explains", "cue": CUE}),
        )
        assert item["tier"] == "primary"
        assert item["metadata"]["originator_review"]["invalid_reason"] == "bad_role"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_missing_row_is_not_returned(self):
        items = [_item(0), _item(1)]
        await orv.review_originators(
            items,
            _answer(
                {
                    "index": 0,
                    "originator": "Office for National Statistics",
                    "role": "relays",
                    "cue": CUE,
                }
            ),
        )
        assert items[0]["tier"] == "reporting"
        assert items[1]["tier"] == "primary"
        assert (
            items[1]["metadata"]["originator_review"]["invalid_reason"]
            == "not_returned"
        )


class TestFailures:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call_error_keeps_tiers(self):
        item = _item()
        await orv.review_originators([item], AsyncMock(side_effect=RuntimeError("503")))
        assert item["tier"] == "primary"
        assert item["metadata"]["originator_review"]["status"] == "failed"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_timeout_keeps_tiers(self):
        async def slow(_prompt):
            await asyncio.sleep(1)

        item = _item()
        with patch.object(
            orv.settings, "ORIGINATOR_REVIEW_TIMEOUT_S", 0.01, create=True
        ):
            await orv.review_originators([item], slow)
        assert item["tier"] == "primary"
        assert item["metadata"]["originator_review"]["status"] == "failed"

    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.parametrize("parsed", [None, {"items": "no"}, ["x"]])
    async def test_invalid_response_keeps_tiers(self, parsed):
        item = _item()
        await orv.review_originators([item], AsyncMock(return_value=parsed))
        assert item["tier"] == "primary"
        assert item["metadata"]["originator_review"]["status"] == "invalid_response"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cancellation_leaves_the_whole_pool_untouched(self):
        """Tier changes apply only after every call returns: a cancelled
        second chunk must not leave the first chunk's lowerings applied."""
        items = [_item(i) for i in range(orv.CALL_ITEMS + 1)]
        rows = [
            {
                "index": i,
                "originator": "Office for National Statistics",
                "role": "relays",
                "cue": CUE,
            }
            for i in range(orv.CALL_ITEMS)
        ]
        calls = []

        async def call(prompt):
            calls.append(prompt)
            if len(calls) == 2:
                raise asyncio.CancelledError
            return {"items": rows}

        with pytest.raises(asyncio.CancelledError):
            await orv.review_originators(items, call)
        assert all(i["tier"] == "primary" for i in items)
        assert not any("metadata" in i for i in items)


class TestInput:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_page_opening_is_read_never_text(self):
        item = _item(snippet="short snippet")
        item["text"] = "DISTILLED FACTS " + CUE
        item[orv.PAGE_OPENING_KEY] = "Opening of the page. " + CUE
        call = _answer(
            {
                "index": 0,
                "originator": "Office for National Statistics",
                "role": "relays",
                "cue": CUE,
            }
        )
        await orv.review_originators([item], call)
        prompt = call.await_args.args[0]
        assert "Opening of the page." in prompt
        assert "DISTILLED FACTS" not in prompt and "short snippet" not in prompt
        assert item["metadata"]["originator_review"]["input_kind"] == "page_opening"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_without_opening_reads_snippet_never_text(self):
        item = _item(snippet="Search snippet. " + CUE)
        item["text"] = "DISTILLED FACTS"
        call = _answer(
            {
                "index": 0,
                "originator": "Office for National Statistics",
                "role": "relays",
                "cue": CUE,
            }
        )
        await orv.review_originators([item], call)
        prompt = call.await_args.args[0]
        assert "Search snippet." in prompt and "DISTILLED FACTS" not in prompt
        assert item["metadata"]["originator_review"]["input_kind"] == "snippet"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cue_must_be_in_the_text_actually_sent(self):
        """A cue found only beyond the 1,200-char cut does not count."""
        item = _item(snippet="x" * orv.TEXT_CHARS + CUE)
        await orv.review_originators(
            [item],
            _answer(
                {
                    "index": 0,
                    "originator": "Office for National Statistics",
                    "role": "relays",
                    "cue": CUE,
                }
            ),
        )
        assert item["tier"] == "primary"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_prompt_never_carries_a_claim(self):
        call = _answer()
        await orv.review_originators([_item()], call)
        assert "claim" not in call.await_args.args[0].split("Items:")[1].lower()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_items_are_chunked(self):
        call = _answer()
        stats = await orv.review_originators(
            [_item(i) for i in range(orv.CALL_ITEMS * 2 + 1)], call
        )
        assert call.await_count == 3 and stats["calls"] == 3

    @pytest.mark.unit
    def test_copy_page_opening_only_when_enabled(self):
        item = {"_full_text": "A" * (orv.TEXT_CHARS + 50)}
        orv.copy_page_opening(item)
        assert item[orv.PAGE_OPENING_KEY] == "A" * orv.TEXT_CHARS
        off = {"_full_text": "A"}
        with patch.object(orv.settings, "ENABLE_ORIGINATOR_REVIEW", False):
            orv.copy_page_opening(off)
        assert orv.PAGE_OPENING_KEY not in off


class TestClassifyBatchWiring:
    """The review runs inside classify_batch, after every cap, and only there."""

    def _classifier(self, tier="primary"):
        from app.pipeline.evidence_classifier import EvidenceClassifier

        classifier = EvidenceClassifier()
        classifier._call_llm = AsyncMock(
            return_value={
                "classifications": [{"index": 0, "tier": tier, "type": "data"}]
            }
        )
        classifier._call_originator_review = AsyncMock(
            return_value={
                "items": [
                    {
                        "index": 0,
                        "originator": "Office for National Statistics",
                        "role": "relays",
                        "cue": CUE,
                    }
                ]
            }
        )
        return classifier

    def _pool(self):
        item = _item()
        for key in ("tier", "evidence_type", "classification_method"):
            item.pop(key)
        item[orv.PAGE_OPENING_KEY] = "Opening. " + CUE
        return [item]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_lowers_and_pops_the_page_opening(self):
        classifier = self._classifier()
        result = await classifier.classify_batch(self._pool())
        assert result[0]["tier"] == "reporting"
        assert result[0]["classification_method"] == "originator_review"
        assert orv.PAGE_OPENING_KEY not in result[0]
        assert classifier.originator_review_stats["lowered"] == 1
        assert "seconds" in classifier.originator_review_stats

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_recovery_marks_not_reviewed_and_makes_no_call(self):
        classifier = self._classifier()
        result = await classifier.classify_batch(self._pool(), review_originators=False)
        assert result[0]["tier"] == "primary"
        receipt = result[0]["metadata"]["originator_review"]
        assert receipt == {
            **receipt,
            "status": "not_reviewed",
            "reason": "recovery_budget",
        }
        classifier._call_originator_review.assert_not_awaited()
        assert orv.PAGE_OPENING_KEY not in result[0]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_flag_off_is_inert(self):
        classifier = self._classifier()
        with patch.object(orv.settings, "ENABLE_ORIGINATOR_REVIEW", False):
            result = await classifier.classify_batch(self._pool())
        assert result[0]["tier"] == "primary"
        assert "metadata" not in result[0]
        classifier._call_originator_review.assert_not_awaited()
        assert classifier.originator_review_stats is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_already_classified_items_are_not_reviewed(self):
        classifier = self._classifier()
        item = _item()
        item[orv.PAGE_OPENING_KEY] = "Opening. " + CUE
        result = await classifier.classify_batch([item])
        assert result[0]["tier"] == "primary"
        classifier._call_originator_review.assert_not_awaited()
        assert orv.PAGE_OPENING_KEY not in result[0]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_mixed_pool_reviews_only_items_classified_now(self):
        classifier = self._classifier()
        earlier = _item(9)  # classified by an earlier call: out of scope
        result = await classifier.classify_batch(self._pool() + [earlier])
        assert result[0]["tier"] == "reporting"
        assert result[1]["tier"] == "primary" and "metadata" not in result[1]
        assert classifier.originator_review_stats["candidates"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_never_raises_a_reporting_verdict(self):
        classifier = self._classifier(tier="reporting")
        classifier._call_originator_review = AsyncMock(
            return_value={
                "items": [
                    {"index": 0, "originator": "x", "role": "originates", "cue": ""}
                ]
            }
        )
        result = await classifier.classify_batch(self._pool())
        assert result[0]["tier"] == "reporting"
        classifier._call_originator_review.assert_not_awaited()


class TestSurfaces:
    @pytest.mark.unit
    def test_receipt_on_owner_payload_only(self):
        from app.api.v1.response_builder import _serialize_evidence

        receipt = {"status": "reviewed", "role": "relays"}
        ev = SimpleNamespace(
            **{
                k: None
                for k in (
                    "id evidence_id source url title snippet published_date "
                    "relevance_score tier evidence_type receipt_status "
                    "corroboration_group_id corroborating_evidence_ids "
                    "external_source_provider source_type archived_url "
                    "llm_relevance_score classification_method content_basis "
                    "text_provenance date_basis context_before context_after "
                    "factcheck_date factcheck_low_relevance factcheck_parse_success "
                    "factcheck_publisher factcheck_rating"
                ).split()
            },
            is_factcheck=False,
            api_metadata={"originator_review": receipt},
        )
        assert (
            _serialize_evidence(ev, include_originator_review=True)["originatorReview"]
            == receipt
        )
        assert "originatorReview" not in _serialize_evidence(
            ev, include_factcheck_detail=True
        )

    @pytest.mark.unit
    def test_fingerprint_names_the_review_only_when_on(self):
        from app.core.manifest_signer import compute_pipeline_fingerprint

        on = compute_pipeline_fingerprint()
        with patch.object(orv.settings, "ENABLE_ORIGINATOR_REVIEW", False):
            off = compute_pipeline_fingerprint()
        assert on != off
        with patch.object(orv, "CONTRACT", "v-next"):
            assert compute_pipeline_fingerprint() != on


class TestCallSiteWiring:
    """The call sites live in long orchestration functions; pin their shape."""

    @pytest.mark.unit
    def test_runner_copies_opening_before_classify_and_skips_recovery(self):
        import inspect

        from app.pipeline import runner

        src = inspect.getsource(runner)
        copy_at = src.index("copy_page_opening(item)")
        assert copy_at < src.index("capture_text_provenance(\n", copy_at)
        assert copy_at < src.index("async def _do_classify")
        recovery = src[src.index("async def _recover_prepare") :]
        call = recovery[recovery.index("classifier.classify_batch(") :][:120]
        assert "review_originators=False" in call

    @pytest.mark.unit
    def test_re_search_copies_opening_before_classify(self):
        import inspect

        from app.pipeline import re_search

        src = inspect.getsource(re_search)
        assert src.index("copy_page_opening(candidate)") < src.index(
            "EvidenceClassifier().classify_batch("
        )


class TestModelCall:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_call_sends_schema_own_model_and_thinking_headroom(self):
        """Thinking tokens count against maxOutputTokens: a 3,000 cap
        truncated 3.7-flash replies mid-JSON on eval 2 (2026-09-30)."""
        from app.pipeline import evidence_classifier as ec

        classifier = ec.EvidenceClassifier()
        classifier.google_ai_api_key = "k"
        fake = AsyncMock(
            return_value=({"items": []}, {"input_tokens": 1, "output_tokens": 1})
        )
        with patch.object(ec, "call_google_ai_with_usage", fake):
            await classifier._call_originator_review("prompt")
        kwargs = fake.await_args.kwargs
        assert kwargs["response_schema"] is orv.RESPONSE_SCHEMA
        assert kwargs["max_tokens"] >= 8192
        assert kwargs["model"] == orv.settings.ORIGINATOR_REVIEW_MODEL
