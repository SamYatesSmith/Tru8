"""Our MCP identity is declared in four public places. They must agree.

WHY THIS FILE EXISTS
--------------------
Getting the namespace wrong has already cost us. The first registry publish
failed on a `server.json` whose namespace pointed at `tru8.io` — a domain that
does not exist — among four other faults that the JSON schema could not see.

The same invention was still being served publicly at
`/.well-known/mcp/server-card.json` as `io.tru8/mcp-server` until 2026-08-05,
and the card's version said 1.0.0 while PyPI was on 1.0.3. That card is what a
registry reads when its automatic scan fails, so a stranger cross-checking us
against the official registry would have found two different servers claiming
to be Tru8 — one of them on a domain nobody owns.

Nothing linked these declarations, so nothing noticed they had drifted. This
does.
"""

import json
import pathlib
import re

import tomllib

BACKEND = pathlib.Path(__file__).resolve().parents[2]

REGISTRY_NAMESPACE = "io.github.SamYatesSmith/tru8"


def _server_json():
    return json.loads((BACKEND / "server.json").read_text(encoding="utf-8"))


def _package_version():
    data = tomllib.loads(
        (BACKEND / "tru8_mcp" / "pyproject.toml").read_text(encoding="utf-8")
    )
    return data["project"]["version"]


def _server_card():
    """The card as actually served, imported rather than re-read from source."""
    from main import MCP_SERVER_CARD

    return MCP_SERVER_CARD


class TestNamespaceAgreement:
    def test_server_json_uses_the_registry_namespace(self):
        assert _server_json()["name"] == REGISTRY_NAMESPACE

    def test_pypi_ownership_marker_matches(self):
        """The registry proves ownership by finding this marker in the README.

        If it disagrees with server.json the publish is rejected.
        """
        readme = (BACKEND / "tru8_mcp" / "README.md").read_text(encoding="utf-8")
        marker = re.search(r"<!--\s*mcp-name:\s*(\S+)\s*-->", readme)
        assert marker, "PyPI ownership marker missing from the package README"
        assert marker.group(1) == REGISTRY_NAMESPACE

    def test_served_card_matches(self):
        """The regression that prompted this file: `io.tru8/mcp-server`."""
        assert _server_card()["serverInfo"]["name"] == REGISTRY_NAMESPACE

    def test_card_claims_no_domain_we_do_not_own(self):
        """`tru8.io` has never been ours. Guard the specific past mistake."""
        blob = json.dumps(_server_card())
        assert "tru8.io" not in blob
        assert "io.tru8" not in blob


class TestVersionAgreement:
    def test_card_version_matches_the_published_package(self):
        assert _server_card()["serverInfo"]["version"] == _package_version()

    def test_server_json_version_matches_the_published_package(self):
        sj = _server_json()
        assert sj["version"] == _package_version()
        assert sj["packages"][0]["version"] == _package_version()


class TestHostedEndpointIsDiscoverable:
    def test_card_advertises_the_streamable_http_endpoint(self):
        """A card with an identity but no endpoint tells a scanner nothing."""
        remotes = _server_card().get("remotes")
        assert remotes, "server card does not advertise the hosted endpoint"
        entry = remotes[0]
        assert entry["type"] == "streamable-http"
        assert entry["url"] == "https://api.trueight.com/mcp"

    def test_card_states_that_discovery_needs_no_credential(self):
        """Registries scan us unauthenticated; saying otherwise invites an
        OAuth handshake we do not implement."""
        auth = _server_card()["authentication"]
        assert auth["discoveryRequiresAuth"] is False
        assert auth["apiKey"]["header"] == "X-API-Key"


# ---------------------------------------------------------------------------
# serverInfo.version — ours, not the SDK's (2026-08-05)
# ---------------------------------------------------------------------------


def test_server_reports_our_version_not_the_sdk_version():
    """Smithery's scan advertised "name: tru8, version: 1.12.4" on our listing.

    That is the mcp library's version. FastMCP takes no `version` argument and
    the low-level Server defaults it to None, at which point the SDK reports
    itself during initialize — so the number readers take for Tru8's was
    whichever mcp release the image happened to resolve.
    """
    import importlib.metadata

    from tru8_mcp import __version__
    from tru8_mcp.server import mcp

    reported = mcp._mcp_server.version

    assert reported == __version__
    assert reported != importlib.metadata.version("mcp")


def test_package_version_matches_pyproject():
    """The constant and the packaging metadata must not drift.

    `__version__` exists because the hosted transport imports this package from
    the source tree, where importlib.metadata finds no installed distribution.
    Two places holding one version is exactly how the wrong number gets shipped.
    """
    import pathlib
    import re

    from tru8_mcp import __version__

    pyproject = (
        pathlib.Path(__file__).resolve().parents[2] / "tru8_mcp" / "pyproject.toml"
    ).read_text(encoding="utf-8")
    declared = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.M).group(1)

    assert __version__ == declared, (
        f"tru8_mcp.__version__ is {__version__} but pyproject declares {declared}"
    )
