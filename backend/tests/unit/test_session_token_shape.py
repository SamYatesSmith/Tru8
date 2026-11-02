"""The dashboard session check accepts Clerk SESSION tokens and nothing else.

Why (2026-11-02, P0 of audit/2026-11-02_chatgpt_plugin_design.md): Clerk signs
its OAuth access tokens and OIDC ID tokens with the SAME instance keys and
issuer as session tokens. `_verify_jwt_token` checked only signature + issuer
(+ aud when CLERK_JWT_AUDIENCE is set), so on the dev instance it ACCEPTED both
an OAuth access token and an ID token as a dashboard session. With OAuth/CIMD
switched on, any website a user consented to would hold full dashboard power.

The claim shapes below are the ones observed on the dev instance that day.
"""

import logging
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.core import auth
from app.core.config import settings

ISSUER_HOST = "test-instance.clerk.accounts.dev"
ISSUER = f"https://{ISSUER_HOST}"

_PRIVATE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_PUBLIC = _PRIVATE.public_key()


class _Key:
    key = _PUBLIC


@pytest.fixture(autouse=True)
def _clerk(monkeypatch):
    monkeypatch.setattr(settings, "CLERK_JWT_ISSUER", ISSUER_HOST)
    monkeypatch.setattr(settings, "CLERK_JWT_AUDIENCE", "")
    monkeypatch.setattr(settings, "ENABLE_CLERK_AZP_ENFORCEMENT", False)
    monkeypatch.setattr(settings, "FRONTEND_URL", "https://www.trueight.com")
    monkeypatch.setattr(settings, "CORS_ORIGINS", ["https://www.trueight.com"])
    monkeypatch.setattr(auth.jwks_client, "get_signing_key_from_jwt", lambda _t: _Key())


def _mint(claims: dict, typ: str = "JWT") -> str:
    now = int(time.time())
    body = {"iss": ISSUER, "iat": now, "nbf": now - 5, "exp": now + 600}
    body.update(claims)
    return jwt.encode(body, _PRIVATE, algorithm="RS256", headers={"typ": typ})


SESSION_V2 = {
    "sub": "user_abc",
    "sid": "sess_abc",
    "v": 2,
    "fva": [0, -1],
    "sts": "active",
}
SESSION_V1 = {
    "sub": "user_abc",
    "sid": "sess_abc",
    "azp": "https://www.trueight.com",
}
ACCESS_TOKEN = {
    "sub": "user_abc",
    "client_id": "Q9quCYn4y9MmbOAK",
    "scope": "openid profile email offline_access",
    "jti": "oat_x",
}
ID_TOKEN = {
    "sub": "user_abc",
    "sid": "sess_abc",
    "aud": ["Q9quCYn4y9MmbOAK"],
    "at_hash": "abc",
    "email": "a@b.c",
}


async def _verify(token):
    return await auth._verify_jwt_token(token)


async def _rejected(token) -> str:
    with pytest.raises(HTTPException) as exc:
        await _verify(token)
    assert exc.value.status_code == 401
    return exc.value.detail


# --- accepted ---------------------------------------------------------------


@pytest.mark.asyncio
async def test_session_token_v2_is_accepted():
    assert (await _verify(_mint(SESSION_V2)))["sub"] == "user_abc"


@pytest.mark.asyncio
async def test_session_token_v1_without_v_claim_is_accepted():
    """Older instances issue v1 tokens (no `v`). Requiring `v` would sign
    every such user out, so the rule rejects foreign markers instead."""
    assert (await _verify(_mint(SESSION_V1)))["sub"] == "user_abc"


@pytest.mark.asyncio
async def test_session_with_configured_audience_is_accepted(monkeypatch):
    monkeypatch.setattr(settings, "CLERK_JWT_AUDIENCE", "tru8-api")
    assert await _verify(_mint({**SESSION_V2, "aud": "tru8-api"}))


# --- the P0 hazard ----------------------------------------------------------


@pytest.mark.asyncio
async def test_oauth_access_token_is_rejected():
    detail = await _rejected(_mint(ACCESS_TOKEN, typ="at+jwt"))
    assert "session" in detail.lower()


@pytest.mark.asyncio
async def test_oauth_access_token_is_rejected_even_with_a_plain_typ():
    """The header is a hint, not the only gate: the OAuth claims alone reject."""
    await _rejected(_mint({**ACCESS_TOKEN, "sid": "sess_abc"}, typ="JWT"))


@pytest.mark.asyncio
async def test_oidc_id_token_is_rejected():
    """An ID token carries `sid` (observed on the dev instance), so `sid`
    alone cannot tell it from a session token — `aud` / `at_hash` do."""
    await _rejected(_mint(ID_TOKEN))


@pytest.mark.asyncio
async def test_id_token_rejected_even_when_an_audience_is_configured(monkeypatch):
    monkeypatch.setattr(settings, "CLERK_JWT_AUDIENCE", "tru8-api")
    await _rejected(_mint(ID_TOKEN))


@pytest.mark.asyncio
async def test_token_without_a_session_id_is_rejected():
    await _rejected(_mint({"sub": "user_abc"}))


@pytest.mark.asyncio
async def test_unconfigured_audience_on_a_token_is_rejected():
    await _rejected(_mint({**SESSION_V2, "aud": "someone-else"}))


@pytest.mark.parametrize("marker", ["client_id", "scope", "at_hash", "nonce"])
@pytest.mark.asyncio
async def test_each_foreign_marker_alone_rejects(marker):
    await _rejected(_mint({**SESSION_V2, marker: "x"}))


# --- unchanged guards still hold --------------------------------------------


@pytest.mark.asyncio
async def test_wrong_issuer_still_rejected():
    await _rejected(_mint({**SESSION_V2, "iss": "https://evil.example"}))


@pytest.mark.asyncio
async def test_expired_still_rejected():
    await _rejected(_mint({**SESSION_V2, "exp": int(time.time()) - 3600}))


# --- azp: observed first, enforced later ------------------------------------


@pytest.mark.asyncio
async def test_unknown_azp_is_logged_not_rejected_while_observing(caplog):
    caplog.set_level(logging.WARNING, logger="app.core.auth")
    token = _mint({**SESSION_V1, "azp": "https://evil.example"})
    assert await _verify(token)
    assert any("azp" in r.getMessage() for r in caplog.records)


@pytest.mark.asyncio
async def test_unknown_azp_is_rejected_when_enforced(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_CLERK_AZP_ENFORCEMENT", True)
    await _rejected(_mint({**SESSION_V1, "azp": "https://evil.example"}))


@pytest.mark.asyncio
async def test_known_azp_passes_when_enforced(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_CLERK_AZP_ENFORCEMENT", True)
    assert await _verify(_mint(SESSION_V1))


@pytest.mark.asyncio
async def test_missing_azp_passes_when_enforced(monkeypatch):
    """Server-minted session tokens carry no azp (observed). Only a PRESENT,
    unknown azp is suspicious."""
    monkeypatch.setattr(settings, "ENABLE_CLERK_AZP_ENFORCEMENT", True)
    assert await _verify(_mint(SESSION_V2))


@pytest.mark.asyncio
async def test_media_type_form_of_at_jwt_is_rejected_on_the_header_alone():
    """RFC 9068 allows `application/at+jwt`; the header must reject by itself."""
    await _rejected(_mint(SESSION_V2, typ="application/at+jwt"))


@pytest.mark.asyncio
async def test_plain_at_jwt_header_alone_rejects_a_session_shaped_token():
    await _rejected(_mint(SESSION_V2, typ="at+jwt"))


@pytest.mark.asyncio
async def test_list_azp_is_a_401_not_a_500():
    await _rejected(_mint({**SESSION_V1, "azp": ["https://www.trueight.com"]}))
