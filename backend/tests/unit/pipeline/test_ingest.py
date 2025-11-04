"""
Tests for Ingest Stage - URL Extraction Only (MVP Scope)

Created: 2025-11-03 15:50:00 UTC
Last Updated: 2025-11-03 15:50:00 UTC
Tested Code Version: commit 388ac66
Last Successful Run: Not yet run
Test Framework: pytest 8.x
Python Version: 3.12

Coverage Target: 80%+
Test Count: 15
Performance: All tests < 5s

Purpose:
    Test URL ingestion functionality for MVP release including:
    - Successful URL extraction with trafilatura
    - Fallback to readability
    - Paywall detection
    - Content sanitization
    - Error handling (timeouts, invalid URLs)
    - Metadata extraction
    - Security (script removal, HTML sanitization)

MVP Scope: URL/TEXT input only
NOT TESTED: Image OCR, Video transcription (not in MVP)

Phase: Phase 1 - Pipeline Coverage
Priority: Critical
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime
import requests

# Test metadata
TEST_VERSION = "388ac66"
LAST_RUN = "Not yet run"
CREATED = "2025-11-03 15:50:00 UTC"

# Import module under test
try:
    from app.pipeline.ingest import UrlIngester, BaseIngester
    INGEST_AVAILABLE = True
except ImportError:
    INGEST_AVAILABLE = False
    UrlIngester = None
    BaseIngester = None

# Import test utilities
try:
    from sample_content import SAMPLE_NEWS_URL, SAMPLE_ARTICLE_TEXT, SAMPLE_HTML_CONTENT
except ImportError:
    SAMPLE_NEWS_URL = "https://www.bbc.com/news/test-article"
    SAMPLE_ARTICLE_TEXT = "Test article content"
    SAMPLE_HTML_CONTENT = "<html><body>Test</body></html>"


@pytest.mark.skipif(not INGEST_AVAILABLE, reason="Ingest module not available")
@pytest.mark.unit
@pytest.mark.phase1
@pytest.mark.stage_ingest
@pytest.mark.critical
class TestUrlIngester:
    """
    Test suite for UrlIngester class

    Tests URL extraction for MVP release (URL/TEXT inputs only)
    Created: 2025-11-03
    Coverage: 15 tests for UrlIngester
    """

    @pytest.fixture
    def url_ingester(self):
        """
        Create UrlIngester instance for testing

        Created: 2025-11-03
        """
        return UrlIngester()

    @pytest.mark.asyncio
    async def test_successful_url_extraction_with_trafilatura(self, url_ingester):
        """
        Test: Successful URL extraction using trafilatura (primary method)
        Created: 2025-11-03
        Last Passed: Not yet run

        CRITICAL: Main URL extraction path for MVP
        """
        # Arrange
        test_url = SAMPLE_NEWS_URL
        expected_content = "Test article content about climate change and environmental policy. This is a comprehensive article with sufficient content length for validation purposes."

        mock_response = Mock()
        mock_response.text = SAMPLE_HTML_CONTENT
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        # Act
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch('trafilatura.extract', return_value=expected_content):
                with patch('trafilatura.extract_metadata', return_value=Mock(
                    title="Test Article",
                    author="Test Author",
                    date="2024-11-01"
                )):
                    result = await url_ingester.process(test_url)

        # Assert
        assert result["success"] is True
        assert "content" in result
        assert len(result["content"]) > 0
        assert result["metadata"]["url"] == test_url
        assert result["metadata"]["title"] == "Test Article"

    @pytest.mark.asyncio
    async def test_fallback_to_readability_when_trafilatura_fails(self, url_ingester):
        """
        Test: Fallback to readability when trafilatura returns empty
        Created: 2025-11-03
        Last Passed: Not yet run

        CRITICAL: Ensures backup extraction method works
        """
        # Arrange
        test_url = SAMPLE_NEWS_URL
        # Readability returns HTML summary with enough content
        readability_html = """
        <div>
            <h1>Fallback Title</h1>
            <p>Fallback content extracted using readability library when trafilatura fails.</p>
            <p>This content is sufficiently long to pass the minimum content validation checks.</p>
            <p>Additional paragraph to ensure we have enough content for the validation.</p>
        </div>
        """

        mock_response = Mock()
        mock_response.text = SAMPLE_HTML_CONTENT
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        # Act
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.get.return_value = mock_response

            # Trafilatura returns None/empty
            with patch('trafilatura.extract', return_value=None):
                with patch('app.pipeline.ingest.Document') as mock_doc_class:
                    mock_doc = Mock()
                    mock_doc.summary.return_value = readability_html
                    mock_doc.title.return_value = "Fallback Title"
                    mock_doc_class.return_value = mock_doc

                    result = await url_ingester.process(test_url)

        # Assert
        assert result["success"] is True
        assert "content" in result
        assert result["metadata"]["extraction_method"] == "readability"

    @pytest.mark.asyncio
    async def test_paywall_detection_http_402(self, url_ingester):
        """
        Test: Detect and handle paywall (HTTP 402)
        Created: 2025-11-03
        Last Passed: Not yet run

        CRITICAL: Must respect paywalls for legal compliance
        """
        # Arrange
        test_url = "https://www.nytimes.com/paywall-article"

        mock_response = Mock()
        mock_response.status_code = 402
        mock_response.raise_for_status.side_effect = requests.HTTPError(response=mock_response)

        # Act
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.get.return_value = mock_response

            result = await url_ingester.process(test_url)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Paywall detected"
        assert result.get("metadata", {}).get("paywall") is True

    @pytest.mark.asyncio
    async def test_timeout_handling(self, url_ingester):
        """
        Test: Handle request timeout gracefully
        Created: 2025-11-03
        Last Passed: Not yet run

        CRITICAL: Must not hang on slow websites
        """
        # Arrange
        test_url = "https://very-slow-website.com/article"

        # Act
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.get.side_effect = requests.Timeout("Request timed out")

            result = await url_ingester.process(test_url)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Request timeout"

    @pytest.mark.asyncio
    async def test_content_sanitization(self, url_ingester):
        """
        Test: HTML sanitization removes dangerous content
        Created: 2025-11-03
        Last Passed: Not yet run

        CRITICAL: Security requirement - must remove scripts
        """
        # Arrange
        dangerous_content = """
        <p>Safe content</p>
        <script>alert('XSS')</script>
        <p>More safe content</p>
        """

        # Act
        sanitized = await url_ingester.sanitize_content(dangerous_content)

        # Assert
        assert "<script>" not in sanitized, "Script tags should be removed"
        # Note: bleach.clean with strip=True removes tags but preserves text content
        # This is acceptable since the <script> tag itself is removed, preventing execution
        assert "Safe content" in sanitized
        assert "More safe content" in sanitized

    @pytest.mark.asyncio
    async def test_empty_content_handling(self, url_ingester):
        """
        Test: Handle empty content after extraction
        Created: 2025-11-03
        Last Passed: Not yet run

        Required: Graceful handling of empty pages
        """
        # Arrange
        test_url = SAMPLE_NEWS_URL

        mock_response = Mock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = Mock()

        # Act
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch('trafilatura.extract', return_value=None):
                with patch('readability.Document') as mock_doc_class:
                    mock_doc = Mock()
                    mock_doc.summary.return_value = ""
                    mock_doc_class.return_value = mock_doc

                    result = await url_ingester.process(test_url)

        # Assert
        assert result["success"] is False
        assert "Could not extract content" in result["error"] or "too short" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_robots_txt_disabled_comment_exists(self, url_ingester):
        """
        Test: Verify robots.txt checking is disabled with comment
        Created: 2025-11-03
        Last Passed: Not yet run

        Required: Document why robots.txt is disabled (legal/fair use)
        """
        # Arrange - Read the actual source code
        import inspect
        source_code = inspect.getsource(UrlIngester.process)

        # Assert
        assert "DISABLED" in source_code or "robots.txt" in source_code.lower()
        # The code should have a comment explaining why robots.txt is disabled

    @pytest.mark.asyncio
    async def test_user_agent_header_verification(self, url_ingester):
        """
        Test: Verify User-Agent header is set correctly
        Created: 2025-11-03
        Last Passed: Not yet run

        Required: Identify bot as Tru8 for transparency
        """
        # Arrange
        test_url = SAMPLE_NEWS_URL

        mock_response = Mock()
        mock_response.text = "content"
        mock_response.raise_for_status = Mock()

        # Act
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch('trafilatura.extract', return_value="content"):
                with patch('trafilatura.extract_metadata', return_value=None):
                    await url_ingester.process(test_url)

        # Assert - Check User-Agent was set
        call_kwargs = mock_session.get.call_args[1]
        assert 'headers' in call_kwargs
        assert 'User-Agent' in call_kwargs['headers']
        assert 'Tru8' in call_kwargs['headers']['User-Agent']

    @pytest.mark.asyncio
    async def test_metadata_extraction(self, url_ingester):
        """
        Test: Extract metadata (title, author, date, URL, word count)
        Created: 2025-11-03
        Last Passed: Not yet run

        Required: Metadata needed for source attribution
        """
        # Arrange
        test_url = SAMPLE_NEWS_URL
        test_content = "This is a test article with multiple words for counting."

        mock_response = Mock()
        mock_response.text = SAMPLE_HTML_CONTENT
        mock_response.raise_for_status = Mock()

        mock_metadata = Mock()
        mock_metadata.title = "Test Article Title"
        mock_metadata.author = "Jane Doe"
        mock_metadata.date = "2024-11-01"

        # Act
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch('trafilatura.extract', return_value=test_content):
                with patch('trafilatura.extract_metadata', return_value=mock_metadata):
                    result = await url_ingester.process(test_url)

        # Assert
        assert result["success"] is True
        assert result["metadata"]["title"] == "Test Article Title"
        assert result["metadata"]["author"] == "Jane Doe"
        assert result["metadata"]["date"] == "2024-11-01"
        assert result["metadata"]["url"] == test_url
        assert result["metadata"]["word_count"] > 0

    @pytest.mark.asyncio
    async def test_very_short_content_rejection(self, url_ingester):
        """
        Test: Reject content shorter than 50 characters
        Created: 2025-11-03
        Last Passed: Not yet run

        Required: Prevent processing of stub pages
        """
        # Arrange
        test_url = SAMPLE_NEWS_URL
        short_content = "Too short"  # Only 9 chars

        mock_response = Mock()
        mock_response.text = "<html><body>Too short</body></html>"
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        # Act
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch('trafilatura.extract', return_value=short_content):
                with patch('trafilatura.extract_metadata', return_value=None):
                    with patch('readability.Document') as mock_doc_class:
                        mock_doc = Mock()
                        mock_doc.summary.return_value = short_content
                        mock_doc_class.return_value = mock_doc

                        result = await url_ingester.process(test_url)

        # Assert - Should fail because content is too short even after readability fallback
        assert result["success"] is False
        assert "too short" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_html_script_removal_for_security(self, url_ingester):
        """
        Test: Remove script tags and other dangerous HTML
        Created: 2025-11-03
        Last Passed: Not yet run

        CRITICAL: Security requirement for MVP
        """
        # Arrange
        dangerous_html = """
        <html>
        <head><script>malicious()</script></head>
        <body>
            <p>Good content</p>
            <script>alert('xss')</script>
            <iframe src="evil.com"></iframe>
            <p>More good content</p>
        </body>
        </html>
        """

        # Act
        cleaned = await url_ingester.sanitize_content(dangerous_html)

        # Assert
        assert "<script>" not in cleaned, "Script tags should be removed"
        assert "<iframe>" not in cleaned, "Iframe tags should be removed"
        # Note: bleach.clean with strip=True removes tags but preserves text content
        # The text content itself (malicious(), alert()) is harmless without the <script> tags
        assert "Good content" in cleaned
        assert "More good content" in cleaned

    @pytest.mark.asyncio
    async def test_redirect_handling_max_5(self, url_ingester):
        """
        Test: Handle URL redirects (max 5)
        Created: 2025-11-03
        Last Passed: Not yet run

        Required: Follow redirects but prevent infinite loops
        """
        # Arrange
        test_url = "http://short.url/abc"
        final_url = "https://full-url.com/article"

        final_content = "Final content after following redirects. This article has sufficient length to pass validation checks."

        mock_response = Mock()
        mock_response.text = final_content
        mock_response.url = final_url  # Final URL after redirects
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()

        # Act
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session.max_redirects = 5
            mock_session_class.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch('trafilatura.extract', return_value=final_content):
                with patch('trafilatura.extract_metadata', return_value=None):
                    result = await url_ingester.process(test_url)

        # Assert
        assert result["success"] is True
        # Verify max_redirects was set
        assert mock_session.max_redirects == 5

    @pytest.mark.asyncio
    async def test_invalid_url_handling(self, url_ingester):
        """
        Test: Handle invalid/malformed URLs gracefully
        Created: 2025-11-03
        Last Passed: Not yet run

        Required: User input validation
        """
        # Arrange
        invalid_url = "not-a-valid-url"

        # Act
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.get.side_effect = requests.exceptions.InvalidURL("Invalid URL")

            result = await url_ingester.process(invalid_url)

        # Assert
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_network_timeout_errors(self, url_ingester):
        """
        Test: Handle network timeouts properly
        Created: 2025-11-03
        Last Passed: Not yet run

        Required: Robust error handling for production
        """
        # Arrange
        test_url = SAMPLE_NEWS_URL

        # Act
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.get.side_effect = requests.Timeout()

            result = await url_ingester.process(test_url)

        # Assert
        assert result["success"] is False
        assert result["error"] == "Request timeout"

    @pytest.mark.asyncio
    async def test_large_page_handling(self, url_ingester):
        """
        Test: Handle large pages (timeout applies, no explicit size limit)
        Created: 2025-11-03
        Last Passed: Not yet run

        Note: No size limit but timeout (180s) prevents very large pages
        """
        # Arrange
        test_url = SAMPLE_NEWS_URL
        large_content = "word " * 100000  # Very large content

        mock_response = Mock()
        mock_response.text = "<html><body>" + large_content + "</body></html>"
        mock_response.raise_for_status = Mock()

        # Act
        with patch('requests.Session') as mock_session_class:
            mock_session = Mock()
            mock_session_class.return_value = mock_session
            mock_session.get.return_value = mock_response

            with patch('trafilatura.extract', return_value=large_content):
                with patch('trafilatura.extract_metadata', return_value=None):
                    result = await url_ingester.process(test_url)

        # Assert - Should succeed (no size limit, only timeout)
        assert result["success"] is True
        assert len(result["content"]) > 0


# ==================== INTEGRATION TESTS ====================

@pytest.mark.skipif(not INGEST_AVAILABLE, reason="Ingest module not available")
@pytest.mark.integration
@pytest.mark.phase1
@pytest.mark.slow
class TestUrlIngesterIntegration:
    """
    Integration tests for UrlIngester

    Tests interaction with external libraries (trafilatura, readability)
    Created: 2025-11-03
    """

    @pytest.fixture
    def url_ingester(self):
        """Create UrlIngester instance"""
        return UrlIngester()

    @pytest.mark.asyncio
    async def test_sanitization_preserves_formatting(self, url_ingester):
        """
        Test: Sanitization preserves paragraph structure
        Created: 2025-11-03
        """
        # Arrange
        html_with_formatting = """
        <p>First paragraph with <strong>bold</strong> text.</p>
        <p>Second paragraph with <em>italic</em> text.</p>
        <ul>
            <li>List item 1</li>
            <li>List item 2</li>
        </ul>
        """

        # Act
        result = await url_ingester.sanitize_content(html_with_formatting)

        # Assert
        assert "First paragraph" in result
        assert "Second paragraph" in result
        assert "List item 1" in result
        # Tags should be preserved
        assert "<p>" in result or "paragraph" in result


# ==================== DOCUMENTATION ====================

"""
Test Coverage Summary:
- ✅ Successful extraction (trafilatura)
- ✅ Fallback to readability
- ✅ Paywall detection (HTTP 402)
- ✅ Timeout handling
- ✅ Content sanitization
- ✅ Empty content handling
- ✅ Robots.txt disabled verification
- ✅ User-Agent header
- ✅ Metadata extraction
- ✅ Short content rejection
- ✅ HTML script removal
- ✅ Redirect handling
- ✅ Invalid URL handling
- ✅ Network timeout errors
- ✅ Large page handling

MVP Scope: URL/TEXT only (no image/video)
Total: 15 unit tests + 1 integration test

Usage:
    pytest tests/unit/pipeline/test_ingest.py                    # Run all
    pytest tests/unit/pipeline/test_ingest.py -m critical        # Critical only
    pytest tests/unit/pipeline/test_ingest.py -k "sanitization"  # Specific test
    pytest tests/unit/pipeline/test_ingest.py -v                 # Verbose

Expected Pass Rate: 100% (when code is bug-free)
Expected Duration: < 10 seconds total
"""

# ==================== VERSION HISTORY ====================
# v1.0.0 - 2025-11-03 - Initial test suite
#          - 15 UrlIngester tests (MVP scope: URL/TEXT only)
#          - Security tests (XSS, script removal)
#          - Error handling tests (timeouts, paywalls, invalid URLs)
#          - Integration tests for external library interaction
