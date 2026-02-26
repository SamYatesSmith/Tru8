"""
Main conftest.py for all tests

This file is automatically discovered by pytest and loads all fixtures.
It also sets up the Python path for importing from backend and mocks.

Created: 2025-11-03
"""

import sys
from pathlib import Path

# Add backend and mocks to Python path
backend_path = Path(__file__).resolve().parent.parent
tests_path = backend_path / "tests"
mocks_path = tests_path / "mocks"

sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(tests_path))
sys.path.insert(0, str(mocks_path))

# Import all fixtures from fixtures/conftest.py
from fixtures.conftest import *


@pytest.fixture(autouse=True)
def _reset_google_ai_client():
    """Reset the google_ai module-level singleton between tests.

    The shared httpx client in app.services.google_ai persists across tests,
    causing 'Event loop is closed' errors when different tests create new
    event loops. Resetting to None forces a fresh client per test.
    """
    yield
    try:
        import app.services.google_ai as _gai

        _gai._client = None
    except ImportError:
        pass
