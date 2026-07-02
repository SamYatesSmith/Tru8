"""Tests for the replay-bench cassette signature date normalisation.

The bench broke silently for ~2 weeks because three pipeline prompts embed
the wall-clock date, drifting every cassette body-hash daily. These tests pin
the fix: signatures are date-boilerplate-invariant, but still distinguish
genuinely different requests.
"""

import httpx
import pytest

from scripts.replay_bench.cassette import (
    _canonical_signature,
    _normalise_body_for_signature,
)


def _req(
    body: str, url: str = "https://example.com/v1/generate?key=SECRET"
) -> httpx.Request:
    return httpx.Request("POST", url, content=body.encode("utf-8"))


PROMPT_TEMPLATE = (
    '{{"contents": [{{"parts": [{{"text": "Extract claims.\\n'
    "Today's date is {date} (Year: {year}).\\nArticle: gilt yields rose."
    '"}}]}}]}}'
)


class TestDateNormalisation:
    def test_extract_boilerplate_dates_produce_same_signature(self):
        """Same request on different days → same signature (the fix)."""
        a = _req(PROMPT_TEMPLATE.format(date="2026-06-17", year="2026"))
        b = _req(PROMPT_TEMPLATE.format(date="2026-07-02", year="2026"))
        c = _req(PROMPT_TEMPLATE.format(date="2027-01-01", year="2027"))
        assert _canonical_signature(a) == _canonical_signature(b)
        assert _canonical_signature(b) == _canonical_signature(c)

    def test_query_planner_boilerplate_normalised(self):
        a = _req(
            '{"text": "TODAY\'S DATE: 2026-06-17 (CURRENT YEAR: 2026)\\nPlan queries."}'
        )
        b = _req(
            '{"text": "TODAY\'S DATE: 2026-07-02 (CURRENT YEAR: 2026)\\nPlan queries."}'
        )
        assert _canonical_signature(a) == _canonical_signature(b)

    def test_different_content_still_distinct(self):
        """Normalisation must NOT alias genuinely different requests."""
        a = _req(PROMPT_TEMPLATE.format(date="2026-07-02", year="2026"))
        other = PROMPT_TEMPLATE.format(date="2026-07-02", year="2026").replace(
            "gilt yields rose", "inflation fell sharply"
        )
        b = _req(other)
        assert _canonical_signature(a) != _canonical_signature(b)

    def test_bare_iso_dates_in_content_not_normalised(self):
        """Only the exact boilerplates are rewritten — dates that are part of
        the actual query/content (e.g. climate date windows) stay distinct."""
        a = _req('{"q": "temperature 2020-01-01 to 2020-12-31"}')
        b = _req('{"q": "temperature 2021-01-01 to 2021-12-31"}')
        assert _canonical_signature(a) != _canonical_signature(b)

    def test_url_query_dates_not_normalised(self):
        a = _req("", url="https://api.example.com/data?start=2026-06-01&end=2026-06-30")
        b = _req("", url="https://api.example.com/data?start=2026-07-01&end=2026-07-31")
        assert _canonical_signature(a) != _canonical_signature(b)

    def test_secret_query_params_still_excluded(self):
        a = _req("{}", url="https://api.example.com/gen?key=AAA&q=x")
        b = _req("{}", url="https://api.example.com/gen?key=BBB&q=x")
        assert _canonical_signature(a) == _canonical_signature(b)

    def test_non_utf8_body_passthrough(self):
        raw = b"\xff\xfe\x00\x01 not utf8"
        assert _normalise_body_for_signature(raw) == raw

    def test_empty_body(self):
        assert _normalise_body_for_signature(b"") == b""


class TestMappingSchemaDeterminism:
    def test_schema_enums_are_sorted_lists(self):
        """The mapping response schema's enums must be deterministic across
        interpreter processes — list(set) followed the per-process hash seed
        and made every mapping request body unreplayable (5 processes → 5
        different body hashes, found 2026-07-02)."""
        from app.pipeline.claim_map_analyzer import (
            _BATCH_MAPPING_RESPONSE_SCHEMA,
            _MAPPING_RESPONSE_SCHEMA,
        )

        def walk(node):
            if isinstance(node, dict):
                if "enum" in node:
                    assert node["enum"] == sorted(node["enum"]), node["enum"]
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(_MAPPING_RESPONSE_SCHEMA)
        walk(_BATCH_MAPPING_RESPONSE_SCHEMA)
