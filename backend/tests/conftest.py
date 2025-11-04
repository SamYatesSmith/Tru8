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
