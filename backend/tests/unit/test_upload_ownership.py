"""An image check may only read a file the same caller uploaded.

Security sweep 2026-11-02, #5: `file_path` was any string. Local paths were
opened with a bare `open()`, so a caller could OCR any image on the server's
disk (and learn from the error whether a file existed), or another user's
upload if its key leaked.
"""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.services import upload_ownership as uo


class _FakeRedis:
    store = {}

    async def setex(self, k, ttl, v):
        _FakeRedis.store[k] = v

    async def get(self, k):
        return _FakeRedis.store.get(k)

    async def aclose(self):
        pass


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    _FakeRedis.store = {}
    monkeypatch.setattr(uo, "_redis", lambda: _FakeRedis())


# --- the ownership record ----------------------------------------------------


@pytest.mark.asyncio
async def test_uploader_owns_their_file():
    await uo.register_upload("s3://bucket/uploads/a.png", "user_alice")
    assert await uo.is_owned_by("s3://bucket/uploads/a.png", "user_alice")


@pytest.mark.asyncio
async def test_another_user_does_not():
    await uo.register_upload("s3://bucket/uploads/a.png", "user_alice")
    assert not await uo.is_owned_by("s3://bucket/uploads/a.png", "user_mallory")


@pytest.mark.asyncio
async def test_a_path_never_issued_is_refused():
    assert not await uo.is_owned_by("/etc/passwd", "user_alice")
    assert not await uo.is_owned_by("uploads/../../app/secret.png", "user_alice")


@pytest.mark.asyncio
async def test_redis_failure_fails_closed(monkeypatch):
    class _Down(_FakeRedis):
        async def get(self, k):
            raise ConnectionError("redis down")

    monkeypatch.setattr(uo, "_redis", lambda: _Down())
    assert not await uo.is_owned_by("s3://bucket/uploads/a.png", "user_alice")


@pytest.mark.asyncio
async def test_missing_inputs_are_refused():
    assert not await uo.is_owned_by(None, "user_alice")
    assert not await uo.is_owned_by("s3://bucket/uploads/a.png", "")


# --- enforced where checks are created ---------------------------------------


@pytest.mark.asyncio
async def test_image_check_with_someone_elses_file_is_refused(monkeypatch):
    from app.api.v1 import checks

    await uo.register_upload("s3://bucket/uploads/a.png", "user_alice")

    async def _user(session, cu):
        return SimpleNamespace(id=cu["id"], email="m@x.co")

    async def _limit(session, user, context):
        return user

    monkeypatch.setattr(checks, "get_or_create_user", _user)
    monkeypatch.setattr(checks, "enforce_usage_limit", _limit)
    monkeypatch.setattr(
        checks, "_require_frozen_evidence_permission", lambda b, u: None
    )
    body = SimpleNamespace(
        input_type="image",
        file_path="s3://bucket/uploads/a.png",
        url=None,
        content=None,
        frozen_evidence=None,
    )
    with pytest.raises(HTTPException) as exc:
        await checks._validate_and_create_check(body, {"id": "user_mallory"}, None)
    assert exc.value.status_code == 400
    assert "upload" in exc.value.detail.lower()


# --- the OCR stage never opens an arbitrary local path ------------------------


@pytest.mark.asyncio
async def test_ocr_refuses_a_local_path_outside_uploads(tmp_path, monkeypatch):
    from app.pipeline.ingest import ImageIngester

    secret = tmp_path / "secret.png"
    secret.write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "uploads").mkdir()
    result = await ImageIngester().process(str(secret))
    assert result["success"] is False
    assert result["error"] == "Image not found"  # the guard, not a decode failure


@pytest.mark.asyncio
async def test_ocr_refuses_traversal_out_of_uploads(tmp_path, monkeypatch):
    from app.pipeline.ingest import ImageIngester

    (tmp_path / "uploads").mkdir()
    (tmp_path / "outside.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    monkeypatch.chdir(tmp_path)
    result = await ImageIngester().process("uploads/../outside.png")
    assert result["success"] is False
    assert result["error"] == "Image not found"  # the guard, not a decode failure
