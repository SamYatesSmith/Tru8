"""Tru8 MCP server — structured evidence research tools for AI agents."""

# Kept in step with pyproject.toml by tests/unit/test_mcp_identity.py. It exists
# because the version has to be readable when the package is imported from the
# source tree — which is how the API imports it to serve the hosted transport,
# where importlib.metadata finds no installed distribution.
__version__ = "1.0.3"
