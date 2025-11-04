"""
Shared pytest fixtures for Tru8 Pipeline Testing

Created: 2025-11-03 15:05:00 UTC
Last Updated: 2025-11-03 15:05:00 UTC
Code Version: commit 388ac66
Purpose: Centralized fixtures for database, mocks, and test data
Tested with: pytest 8.x, Python 3.12, SQLAlchemy 2.x

This file provides reusable fixtures for all tests:
- Database fixtures (test DB setup/teardown)
- Mock fixtures (OpenAI, Search APIs, Fact-Check API)
- Sample data fixtures (content, claims, evidence)
- Client fixtures (API clients, services)

Phase: Phase 0 (Infrastructure)
Status: Production-ready
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Import mock libraries
import sys
from pathlib import Path

# Add project root and mocks to path
backend_path = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(backend_path / "tests" / "mocks"))

try:
    from app.models.base import Base
    from app.models.check import Check
    from app.models.claim import Claim
    from app.models.evidence import Evidence
    from app.models.user import User
except ImportError:
    # Models may not be available during early testing
    Base = None
    Check = Claim = Evidence = User = None

# ==================== PYTEST CONFIGURATION ====================

def pytest_configure(config):
    """Configure pytest with custom settings"""
    # Set testing mode
    import os
    os.environ["TESTING"] = "True"
    os.environ["PYTEST_RUNNING"] = "True"


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add automatic markers"""
    for item in items:
        # Auto-mark slow tests
        if "slow" in item.nodeid:
            item.add_marker(pytest.mark.slow)

        # Auto-mark by directory
        if "/unit/" in item.nodeid:
            item.add_marker(pytest.mark.unit)
        if "/integration/" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        if "/performance/" in item.nodeid:
            item.add_marker(pytest.mark.performance)
        if "/regression/" in item.nodeid:
            item.add_marker(pytest.mark.regression)


# ==================== DATABASE FIXTURES ====================

@pytest.fixture(scope="session")
def test_db_engine():
    """
    Create an in-memory SQLite database engine for testing

    Scope: session (one database for entire test session)
    Created: 2025-11-03
    """
    if Base is None:
        pytest.skip("Database models not available")

    # In-memory SQLite database
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False  # Set to True for SQL debugging
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_db_engine):
    """
    Create a new database session for each test

    Scope: function (fresh session per test)
    Created: 2025-11-03
    Usage: def test_something(db_session): ...
    """
    if Base is None:
        pytest.skip("Database models not available")

    # Create session factory
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db_engine)
    session = SessionLocal()

    # Enable nested transactions for isolation
    connection = test_db_engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)

    yield session

    # Rollback and cleanup
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def clean_db(db_session):
    """
    Ensure database is clean before test

    Scope: function
    Created: 2025-11-03
    Usage: def test_something(clean_db): ...
    """
    # Delete all data
    if Evidence:
        db_session.query(Evidence).delete()
    if Claim:
        db_session.query(Claim).delete()
    if Check:
        db_session.query(Check).delete()
    if User:
        db_session.query(User).delete()
    db_session.commit()

    yield db_session


# ==================== MOCK API FIXTURES ====================

@pytest.fixture
def mock_openai_client():
    """
    Mock OpenAI API client for LLM calls

    Created: 2025-11-03
    Returns: AsyncMock configured with realistic responses
    Usage: def test_extract(mock_openai_client): ...
    """
    mock_client = AsyncMock()

    # Import mock responses
    try:
        from llm_responses import MOCK_CLAIM_EXTRACTION, MOCK_JUDGMENT, MOCK_QUERY_ANSWER

        # Configure mock responses
        mock_client.chat.completions.create = AsyncMock(
            return_value=Mock(
                choices=[Mock(message=Mock(content=MOCK_CLAIM_EXTRACTION))]
            )
        )
    except ImportError:
        # Fallback if mock library not yet created
        mock_client.chat.completions.create = AsyncMock(
            return_value=Mock(
                choices=[Mock(message=Mock(content='{"claims": []}'))]
            )
        )

    return mock_client


@pytest.fixture
def mock_search_api():
    """
    Mock Brave Search / SERP API

    Created: 2025-11-03
    Returns: Mock configured with realistic search results
    Usage: def test_retrieve(mock_search_api): ...
    """
    mock_api = Mock()

    try:
        from search_results import MOCK_SEARCH_RESULTS
        mock_api.search = Mock(return_value=MOCK_SEARCH_RESULTS)
    except ImportError:
        # Fallback
        mock_api.search = Mock(return_value={"results": []})

    return mock_api


@pytest.fixture
def mock_factcheck_api():
    """
    Mock Google Fact Check Explorer API

    Created: 2025-11-03
    Returns: Mock configured with fact-check data
    Usage: def test_factcheck(mock_factcheck_api): ...
    """
    mock_api = Mock()

    try:
        from factcheck_data import MOCK_FACTCHECK_RESULTS
        mock_api.search = Mock(return_value=MOCK_FACTCHECK_RESULTS)
    except ImportError:
        # Fallback
        mock_api.search = Mock(return_value={"claims": []})

    return mock_api


@pytest.fixture
def mock_nli_model():
    """
    Mock BART-MNLI model for NLI verification

    Created: 2025-11-03
    Returns: Mock model with predict method
    Usage: def test_verify(mock_nli_model): ...
    """
    mock_model = Mock()

    # Mock entailment scores
    mock_model.predict = Mock(
        return_value={
            "entailment": 0.85,
            "contradiction": 0.10,
            "neutral": 0.05
        }
    )

    return mock_model


@pytest.fixture
def mock_redis_client():
    """
    Mock Redis client for caching

    Created: 2025-11-03
    Returns: Mock Redis client
    Usage: def test_caching(mock_redis_client): ...
    """
    mock_redis = Mock()

    # In-memory cache for testing
    cache_store = {}

    def mock_get(key):
        return cache_store.get(key)

    def mock_set(key, value, ex=None):
        cache_store[key] = value
        return True

    def mock_delete(key):
        cache_store.pop(key, None)
        return True

    def mock_exists(key):
        return key in cache_store

    mock_redis.get = Mock(side_effect=mock_get)
    mock_redis.set = Mock(side_effect=mock_set)
    mock_redis.delete = Mock(side_effect=mock_delete)
    mock_redis.exists = Mock(side_effect=mock_exists)

    return mock_redis


# ==================== SAMPLE DATA FIXTURES ====================

@pytest.fixture
def sample_url():
    """Sample URL for testing"""
    return "https://www.bbc.com/news/example-article"


@pytest.fixture
def sample_text_content():
    """
    Sample text content for testing

    Created: 2025-11-03
    Returns: Realistic article text with verifiable claims
    """
    return """
    The global climate summit concluded yesterday with 195 countries agreeing to reduce carbon emissions
    by 45% by 2030. Scientists have confirmed that global temperatures have risen by 1.1°C since
    pre-industrial times. The agreement includes $100 billion in annual funding for developing nations
    to transition to renewable energy sources.

    According to the International Energy Agency, renewable energy capacity grew by 9.6% in 2023,
    with solar power leading the expansion. Wind energy installations increased by 50 gigawatts globally.

    However, critics argue that the targets are insufficient to limit warming to 1.5°C as outlined
    in the Paris Agreement. Environmental groups are calling for more ambitious goals and faster
    implementation timelines.
    """.strip()


@pytest.fixture
def sample_claims():
    """
    Sample extracted claims for testing

    Created: 2025-11-03
    Returns: List of claim dictionaries
    """
    try:
        from sample_content import SAMPLE_CLAIMS
        return SAMPLE_CLAIMS
    except ImportError:
        # Fallback
        return [
            {
                "text": "195 countries agreed to reduce carbon emissions by 45% by 2030",
                "position": 0,
                "subject_context": "Climate agreement",
                "key_entities": ["195 countries", "45%", "2030"],
                "is_verifiable": True,
                "claim_type": "factual"
            },
            {
                "text": "Global temperatures have risen by 1.1°C since pre-industrial times",
                "position": 1,
                "subject_context": "Climate change",
                "key_entities": ["1.1°C", "pre-industrial times"],
                "is_verifiable": True,
                "claim_type": "factual"
            }
        ]


@pytest.fixture
def sample_evidence():
    """
    Sample evidence for testing

    Created: 2025-11-03
    Returns: List of evidence dictionaries
    """
    try:
        from sample_content import SAMPLE_EVIDENCE
        return SAMPLE_EVIDENCE
    except ImportError:
        # Fallback
        return [
            {
                "source": "BBC News",
                "url": "https://www.bbc.com/news/science-environment-12345",
                "title": "Climate summit reaches historic agreement",
                "snippet": "195 countries have agreed to reduce emissions by 45% by 2030...",
                "published_date": "2024-11-01",
                "relevance_score": 0.95,
                "credibility_score": 0.90,
                "is_factcheck": False
            },
            {
                "source": "Reuters",
                "url": "https://www.reuters.com/climate/agreement-2024",
                "title": "World leaders commit to emissions cuts",
                "snippet": "The agreement includes binding targets for carbon reduction...",
                "published_date": "2024-11-01",
                "relevance_score": 0.92,
                "credibility_score": 0.88,
                "is_factcheck": False
            }
        ]


@pytest.fixture
def sample_check(db_session):
    """
    Create a sample Check record in database

    Created: 2025-11-03
    Usage: def test_something(sample_check): ...
    """
    if Check is None:
        pytest.skip("Check model not available")

    check = Check(
        id=1,
        user_id="test_user_123",
        input_type="text",
        input_content="Sample text for testing",
        status="pending",
        created_at=datetime.utcnow()
    )
    db_session.add(check)
    db_session.commit()
    db_session.refresh(check)

    return check


@pytest.fixture
def sample_user(db_session):
    """
    Create a sample User record in database

    Created: 2025-11-03
    Usage: def test_something(sample_user): ...
    """
    if User is None:
        pytest.skip("User model not available")

    user = User(
        clerk_id="test_user_123",
        email="test@example.com",
        credits=10,
        monthly_checks_used=0,
        created_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


# ==================== UTILITY FIXTURES ====================

@pytest.fixture
def freeze_time():
    """
    Fixture to freeze time for testing

    Created: 2025-11-03
    Usage:
        def test_something(freeze_time):
            with freeze_time("2024-11-03 12:00:00"):
                # time is frozen
    """
    from unittest.mock import patch
    from datetime import datetime

    class TimeFreezer:
        def __init__(self):
            self.frozen_time = None

        def __call__(self, time_str):
            self.frozen_time = datetime.fromisoformat(time_str)
            return patch('datetime.datetime', return_value=self.frozen_time)

    return TimeFreezer()


@pytest.fixture
def temp_file(tmp_path):
    """
    Create temporary file for testing

    Created: 2025-11-03
    Usage: def test_file_upload(temp_file): ...
    """
    def _create_temp_file(content: str, filename: str = "test.txt"):
        file_path = tmp_path / filename
        file_path.write_text(content)
        return str(file_path)

    return _create_temp_file


@pytest.fixture
def mock_celery_task():
    """
    Mock Celery task for testing pipeline orchestration

    Created: 2025-11-03
    Usage: def test_pipeline(mock_celery_task): ...
    """
    mock_task = Mock()
    mock_task.delay = Mock(return_value=Mock(id="task_123"))
    mock_task.AsyncResult = Mock(return_value=Mock(
        state="SUCCESS",
        result={"status": "completed"}
    ))

    return mock_task


@pytest.fixture(scope="session")
def event_loop():
    """
    Create event loop for async tests

    Created: 2025-11-03
    Required for pytest-asyncio
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ==================== PERFORMANCE FIXTURES ====================

@pytest.fixture
def performance_timer():
    """
    Timer for performance testing

    Created: 2025-11-03
    Usage:
        def test_perf(performance_timer):
            with performance_timer() as timer:
                # code to measure
            assert timer.elapsed < 1.0  # must be under 1 second
    """
    import time

    class Timer:
        def __init__(self):
            self.start = None
            self.end = None
            self.elapsed = None

        def __enter__(self):
            self.start = time.perf_counter()
            return self

        def __exit__(self, *args):
            self.end = time.perf_counter()
            self.elapsed = self.end - self.start

    return Timer


@pytest.fixture
def memory_tracker():
    """
    Track memory usage during tests

    Created: 2025-11-03
    Usage:
        def test_memory(memory_tracker):
            with memory_tracker() as tracker:
                # code to measure
            assert tracker.peak_mb < 100  # must use less than 100MB
    """
    import psutil
    import os

    class MemoryTracker:
        def __init__(self):
            self.process = psutil.Process(os.getpid())
            self.start_mb = 0
            self.peak_mb = 0
            self.end_mb = 0

        def __enter__(self):
            self.start_mb = self.process.memory_info().rss / 1024 / 1024
            return self

        def __exit__(self, *args):
            self.end_mb = self.process.memory_info().rss / 1024 / 1024
            self.peak_mb = max(self.start_mb, self.end_mb)

    return MemoryTracker


# ==================== PYTEST HOOKS ====================

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook to capture test results for logging

    Created: 2025-11-03
    """
    outcome = yield
    report = outcome.get_result()

    # Log test results
    if report.when == "call":
        if report.passed:
            item.test_result = "PASSED"
        elif report.failed:
            item.test_result = "FAILED"
        elif report.skipped:
            item.test_result = "SKIPPED"


# ==================== DOCUMENTATION ====================

"""
Fixture Usage Examples:

1. Database Testing:
    def test_create_check(db_session, sample_user):
        check = Check(user_id=sample_user.clerk_id, ...)
        db_session.add(check)
        db_session.commit()
        assert check.id is not None

2. API Mocking:
    def test_extraction(mock_openai_client):
        extractor = ClaimExtractor(client=mock_openai_client)
        claims = await extractor.extract("text")
        assert len(claims) > 0

3. Performance Testing:
    def test_speed(performance_timer):
        with performance_timer() as timer:
            result = expensive_function()
        assert timer.elapsed < 1.0

4. Sample Data:
    def test_retrieval(sample_claims, sample_evidence):
        retriever = EvidenceRetriever()
        results = retriever.retrieve(sample_claims[0])
        assert results is not None

5. Async Testing:
    @pytest.mark.asyncio
    async def test_async_function(mock_openai_client):
        result = await async_function()
        assert result is not None
"""

# ==================== VERSION HISTORY ====================
# v1.0.0 - 2025-11-03 - Initial fixture library
#          - Database fixtures (session, clean_db)
#          - Mock API fixtures (OpenAI, Search, Fact-Check, NLI, Redis)
#          - Sample data fixtures (content, claims, evidence)
#          - Utility fixtures (timer, memory tracker, temp files)
#          - Performance fixtures
#          - Pytest hooks and configuration
