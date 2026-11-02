"""/metrics is private; public PDF export is rate-limited.

Security sweep 2026-11-02, #7: /metrics was mounted with no auth (a leak
waiting to grow as metrics are added), and the public PDF route ran a
WeasyPrint render per request under only the default per-IP limit.
"""

import pytest
from httpx import ASGITransport, AsyncClient

import main
from app.core.config import settings
from app.core.rate_limit import limiter


@pytest.fixture(autouse=True)
def _fresh_limits():
    limiter.reset()
    yield
    limiter.reset()


async def _get(path, headers=None):
    async with AsyncClient(
        transport=ASGITransport(app=main.app), base_url="http://test"
    ) as c:
        return await c.get(path, headers=headers or {})


@pytest.mark.asyncio
async def test_metrics_is_404_when_no_token_is_configured(monkeypatch):
    monkeypatch.setattr(settings, "METRICS_TOKEN", "")
    r = await _get("/metrics/")
    assert r.status_code == 404
    assert "python_gc" not in r.text


@pytest.mark.asyncio
async def test_metrics_needs_the_configured_token(monkeypatch):
    monkeypatch.setattr(settings, "METRICS_TOKEN", "s3cret-scraper-token")
    assert (await _get("/metrics/")).status_code == 404
    assert (
        await _get("/metrics/", {"Authorization": "Bearer wrong"})
    ).status_code == 404
    ok = await _get("/metrics/", {"Authorization": "Bearer s3cret-scraper-token"})
    assert ok.status_code == 200
    assert "python_gc" in ok.text or "process_" in ok.text


def test_public_pdf_export_has_a_tight_limit():
    """Pinned on the route itself: the decorator registers the limit."""
    from app.api.v1 import checks

    name = f"{checks.export_public_check_pdf.__module__}.export_public_check_pdf"
    limits = limiter._route_limits.get(name, [])
    assert limits, "public PDF export has no explicit rate limit"
    assert any(l.limit.amount <= 6 for l in limits)


def test_authenticated_pdf_export_is_limited_too():
    from app.api.v1 import checks

    name = f"{checks.export_check_pdf.__module__}.export_check_pdf"
    assert limiter._route_limits.get(name), "authenticated PDF export has no limit"
