"""A developer machine must be incapable of charging real customers.

Found 2026-08-03: ``backend/.env`` carried ``ENVIRONMENT=development`` alongside a
live ``sk_live_`` Stripe secret and a live webhook secret. Nothing leaked — that
file has never been committed — but every local run of the payments path was
pointed at real customers and real money. Clerk was correctly on a test key;
Stripe was not.

``Settings._refuse_live_stripe_outside_deployment`` discards a live secret key
outside a deployed environment. These tests pin all four corners, because the
dangerous failure is not "the guard does nothing" — it is "the guard also fires
in production and silently disables payments".
"""

import pytest

from app.core.config import Settings

_DB = "postgresql://u:p@localhost:5432/x"


def _settings(**overrides) -> Settings:
    """Build Settings from explicit values, ignoring the developer's real .env."""
    base = {
        # Required fields, supplied so the test never reads the developer's real
        # backend/.env — which is the very file this guard exists because of.
        "DATABASE_URL": _DB,
        "CLERK_SECRET_KEY": "sk_test_clerk",
        "CLERK_PUBLISHABLE_KEY": "pk_test_clerk",
        "CLERK_JWT_ISSUER": "https://example.clerk.accounts.dev",
        "SECRET_KEY": "test-secret",
        "ENVIRONMENT": "development",
        "STRIPE_SECRET_KEY": "",
        "ALLOW_LIVE_STRIPE_IN_DEV": False,
        "_env_file": None,  # hermetic: ignore backend/.env entirely
    }
    base.update(overrides)
    return Settings(**base)


class TestLiveStripeKeyRefusedInDevelopment:
    def test_live_key_is_discarded(self):
        s = _settings(ENVIRONMENT="development", STRIPE_SECRET_KEY="sk_live_abc123")
        assert s.STRIPE_SECRET_KEY == ""

    @pytest.mark.parametrize("env", ["development", "test", "local", "DEVELOPMENT"])
    def test_discarded_in_every_non_deployed_environment(self, env):
        """Anything that is not production/staging counts as a developer machine."""
        s = _settings(ENVIRONMENT=env, STRIPE_SECRET_KEY="sk_live_abc123")
        assert s.STRIPE_SECRET_KEY == ""

    def test_warning_is_emitted_to_stderr(self, capsys):
        _settings(ENVIRONMENT="development", STRIPE_SECRET_KEY="sk_live_abc123")
        err = capsys.readouterr().err
        assert "CRITICAL" in err
        assert "STRIPE_SECRET_KEY" in err
        # The message must say what to do, not merely that something happened.
        assert "test-mode" in err
        assert "ALLOW_LIVE_STRIPE_IN_DEV" in err


class TestGuardDoesNotOverreach:
    """The costly failure mode: a guard that breaks production payments."""

    @pytest.mark.parametrize("env", ["production", "staging", "PRODUCTION"])
    def test_live_key_survives_in_deployed_environments(self, env):
        s = _settings(ENVIRONMENT=env, STRIPE_SECRET_KEY="sk_live_abc123")
        assert s.STRIPE_SECRET_KEY == "sk_live_abc123"

    def test_test_mode_key_is_untouched_in_development(self):
        s = _settings(ENVIRONMENT="development", STRIPE_SECRET_KEY="sk_test_abc123")
        assert s.STRIPE_SECRET_KEY == "sk_test_abc123"

    def test_restricted_key_is_untouched(self):
        """rk_live_ is a restricted key; the guard targets sk_live_ only."""
        s = _settings(ENVIRONMENT="development", STRIPE_SECRET_KEY="rk_live_abc123")
        assert s.STRIPE_SECRET_KEY == "rk_live_abc123"

    def test_empty_key_is_a_no_op(self):
        s = _settings(ENVIRONMENT="development", STRIPE_SECRET_KEY="")
        assert s.STRIPE_SECRET_KEY == ""

    def test_explicit_override_is_honoured(self):
        """The escape hatch must work, or someone will delete the guard instead."""
        s = _settings(
            ENVIRONMENT="development",
            STRIPE_SECRET_KEY="sk_live_abc123",
            ALLOW_LIVE_STRIPE_IN_DEV=True,
        )
        assert s.STRIPE_SECRET_KEY == "sk_live_abc123"


class TestWebhookSecretIsDeliberatelyUnguarded:
    def test_webhook_secret_is_never_touched(self):
        """Stripe webhook secrets are `whsec_` in BOTH modes.

        There is no prefix that distinguishes live from test, so the guard cannot
        catch one and must not pretend to. Swapping it stays a manual step. This
        test exists so nobody "fixes" the omission by blanking every whsec_ value
        and thereby breaks signature verification in production.
        """
        s = _settings(
            ENVIRONMENT="development",
            STRIPE_SECRET_KEY="sk_live_abc123",
            STRIPE_WEBHOOK_SECRET="whsec_abc123",
        )
        assert s.STRIPE_SECRET_KEY == ""  # guard did fire
        assert s.STRIPE_WEBHOOK_SECRET == "whsec_abc123"  # and left this alone
