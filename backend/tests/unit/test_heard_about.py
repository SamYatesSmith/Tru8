"""Self-reported "How did you hear about us?" (ACE Stage 4, 2026-10-01).

Write-once, optional, never re-asked after a skip. Only the code reaches
analytics; the "other" free text stays in the database.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1 import users
from app.core.attribution import HEARD_ABOUT_CODES, normalise_heard_about


class TestNormalise:
    @pytest.mark.parametrize("code", sorted(HEARD_ABOUT_CODES - {"other"}))
    def test_codes_keep_no_detail(self, code):
        assert normalise_heard_about(code, "ignored") == (code, None)

    def test_other_keeps_cleaned_capped_detail(self):
        code, detail = normalise_heard_about("other", "  a podcast\x07  ")
        assert (code, detail) == ("other", "a podcast")
        assert len(normalise_heard_about("other", "x" * 500)[1]) == 200

    def test_other_with_blank_detail(self):
        assert normalise_heard_about("other", "   ") == ("other", None)

    @pytest.mark.parametrize("bad", ["", "Search", "twitter", None, 3])
    def test_unknown_answers_refused(self, bad):
        assert normalise_heard_about(bad, None) is None


def _session(rowcount):
    session = AsyncMock()
    result = MagicMock()
    result.rowcount = rowcount
    session.execute = AsyncMock(return_value=result)
    session.commit = AsyncMock()
    return session


@pytest.fixture
def events(monkeypatch):
    sent = []
    monkeypatch.setattr(
        "app.services.product_analytics.schedule_event",
        lambda *a, **k: sent.append((a, k)),
    )
    return sent


def _user(monkeypatch, heard_about=None):
    user = SimpleNamespace(id="user_1", heard_about=heard_about)
    monkeypatch.setattr(users, "get_or_create_user", AsyncMock(return_value=user))
    return user


class TestEndpoint:
    @pytest.mark.asyncio
    async def test_records_once_and_emits_code_only(self, monkeypatch, events):
        _user(monkeypatch)
        session = _session(1)
        out = await users.record_heard_about(
            users.HeardAboutRequest(answer="other", detail="my private note"),
            {"id": "user_1"},
            session,
        )
        assert out == {"recorded": True, "reason": None}
        params = session.execute.call_args[0][1]
        assert params["answer"] == "other" and params["detail"] == "my private note"
        assert "heard_about IS NULL" in str(session.execute.call_args[0][0])
        assert events == [
            (
                ("heard_about_answered", "user_1", {"answer": "other"}),
                {"dedup_key": "user_1"},
            )
        ]

    @pytest.mark.asyncio
    async def test_skip_is_recorded_but_not_emitted(self, monkeypatch, events):
        _user(monkeypatch)
        out = await users.record_heard_about(
            users.HeardAboutRequest(answer="skipped"), {"id": "user_1"}, _session(1)
        )
        assert out["recorded"] is True
        assert events == []

    @pytest.mark.asyncio
    async def test_already_answered_is_refused(self, monkeypatch, events):
        _user(monkeypatch, heard_about="search")
        session = _session(1)
        out = await users.record_heard_about(
            users.HeardAboutRequest(answer="linkedin"), {"id": "user_1"}, session
        )
        assert out == {"recorded": False, "reason": "already_set"}
        session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_lost_race_is_refused(self, monkeypatch, events):
        _user(monkeypatch)
        out = await users.record_heard_about(
            users.HeardAboutRequest(answer="linkedin"), {"id": "user_1"}, _session(0)
        )
        assert out == {"recorded": False, "reason": "already_set"}
        assert events == []

    @pytest.mark.asyncio
    async def test_invalid_answer(self, monkeypatch, events):
        _user(monkeypatch)
        out = await users.record_heard_about(
            users.HeardAboutRequest(answer="tiktok"), {"id": "user_1"}, _session(1)
        )
        assert out == {"recorded": False, "reason": "invalid_answer"}


def test_frontend_options_match_backend_codes():
    """The dashboard card's option values and the stored codes stay in step."""
    import re
    from pathlib import Path

    card = (
        Path(__file__).resolve().parents[3]
        / "web/app/dashboard/components/heard-about-card.tsx"
    ).read_text(encoding="utf-8")
    values = set(re.findall(r"value: '([a-z_]+)'", card))
    assert values == HEARD_ABOUT_CODES - {"skipped"}
