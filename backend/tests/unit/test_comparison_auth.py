"""COMPARE: the surface wall (design §7.7).

CREATE is dashboard-only. The mechanism is structural, not a runtime check:
the endpoints depend on `get_current_user` — the JWT-only dependency used by
file upload and API-key management — NOT `get_current_user_or_api_key`. An
API key therefore cannot reach comparisons at all, which is what keeps the
feature off the Agent API and MCP without a deny-list to maintain.

If someone "upgrades" the dependency to dual auth, these tests are the
tripwire. The public list variant is the deliberate exception: it is
unauthenticated and read-only, serving /r/.
"""

import inspect

from app.api.v1 import comparisons
from app.core.auth import get_current_user


def _dependency_names(endpoint):
    return {
        param.default.dependency.__name__
        for param in inspect.signature(endpoint).parameters.values()
        if getattr(param.default, "dependency", None) is not None
    }


class TestSurfaceWall:
    def test_create_is_jwt_only(self):
        deps = _dependency_names(comparisons.create_comparison)
        assert "get_current_user" in deps
        assert "get_current_user_or_api_key" not in deps

    def test_create_uses_the_exact_jwt_dependency(self):
        # Same callable, not a lookalike.
        for param in inspect.signature(
            comparisons.create_comparison
        ).parameters.values():
            dep = getattr(param.default, "dependency", None)
            if dep is not None and dep.__name__ == "get_current_user":
                assert dep is get_current_user
                return
        raise AssertionError("get_current_user dependency not found")

    def test_authenticated_list_is_jwt_only(self):
        deps = _dependency_names(comparisons.list_comparisons)
        assert "get_current_user" in deps
        assert "get_current_user_or_api_key" not in deps

    def test_public_list_has_no_user_dependency(self):
        # /r/ read path: session only, no auth of any kind.
        deps = _dependency_names(comparisons.list_comparisons_public)
        assert "get_current_user" not in deps
        assert "get_current_user_or_api_key" not in deps

    def test_no_api_key_dependency_anywhere_in_module(self):
        source = inspect.getsource(comparisons)
        assert "get_current_user_or_api_key" not in source
