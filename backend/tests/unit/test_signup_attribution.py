"""Attribution rules: what may be recorded, and when the window shuts.

The endpoint's safety lives in three places: the charset gate (a tag we did
not mint is refused), the time box (an old account cannot be re-attributed by
a later tagged visit), and the write-once UPDATE (guarded in the endpoint via
``WHERE signup_source IS NULL``, same shape as the lifecycle-email markers).
The first two are pure functions and are pinned here.
"""

from datetime import datetime, timedelta

import pytest

from app.core.attribution import (
    ATTRIBUTION_WINDOW,
    attribution_window_open,
    normalise_signup_source,
)


class TestNormaliseSignupSource:
    @pytest.mark.unit
    @pytest.mark.parametrize(
        "raw,expected",
        [
            ("outreach-jane", "outreach-jane"),
            ("  Outreach-Jane  ", "outreach-jane"),  # trimmed + lowercased
            ("smithery", "smithery"),
            ("hn_2026.08", "hn_2026.08"),
            ("a", "a"),
        ],
    )
    def test_valid_tags_normalise(self, raw, expected):
        assert normalise_signup_source(raw) == expected

    @pytest.mark.unit
    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "   ",
            "-leading-separator",
            "has space",
            "semi;colon",
            "<script>",
            "tag/with/slash",
            "x" * 65,  # over length
            None,
            42,
            ["list"],
        ],
    )
    def test_invalid_tags_are_refused_not_coerced(self, raw):
        assert normalise_signup_source(raw) is None

    @pytest.mark.unit
    def test_sixty_four_chars_is_the_boundary(self):
        assert normalise_signup_source("x" * 64) == "x" * 64
        assert normalise_signup_source("x" * 65) is None


class TestAttributionWindow:
    @pytest.mark.unit
    def test_open_just_after_signup(self):
        created = datetime(2026, 8, 11, 12, 0)
        assert attribution_window_open(created, created + timedelta(minutes=5))

    @pytest.mark.unit
    def test_open_at_exactly_the_window_edge(self):
        created = datetime(2026, 8, 11, 12, 0)
        assert attribution_window_open(created, created + ATTRIBUTION_WINDOW)

    @pytest.mark.unit
    def test_closed_beyond_the_window(self):
        """An existing user on a tagged link months later stays UNKNOWN."""
        created = datetime(2026, 5, 1, 12, 0)
        now = datetime(2026, 8, 11, 12, 0)
        assert not attribution_window_open(created, now)

    @pytest.mark.unit
    def test_closed_one_second_past(self):
        created = datetime(2026, 8, 11, 12, 0)
        assert not attribution_window_open(
            created, created + ATTRIBUTION_WINDOW + timedelta(seconds=1)
        )
