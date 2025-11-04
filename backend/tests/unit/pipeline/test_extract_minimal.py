"""
Minimal test to verify ClaimExtractor mocking pattern works
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock

from app.pipeline.extract import ClaimExtractor

# Mock response
MOCK_CLAIM_EXTRACTION = json.dumps({
    "claims": [{
        "text": "Test claim about climate change",
        "confidence": 0.95,
        "subject_context": "Climate",
        "key_entities": ["climate change"]
    }],
    "source_summary": "Test summary",
    "extraction_confidence": 0.9
})


@pytest.mark.unit
@pytest.mark.asyncio
class TestClaimExtractorMinimal:

    @pytest.fixture
    def claim_extractor(self):
        """Create ClaimExtractor instance"""
        return ClaimExtractor()

    async def test_extract_claims_basic(self, claim_extractor):
        """Test basic claim extraction with httpx mocking"""
        # Arrange
        test_content = "This is test content about climate change and global warming."

        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": MOCK_CLAIM_EXTRACTION
                }
            }]
        }

        # Act
        with patch('app.pipeline.extract.httpx.AsyncClient') as mock_client_class:
            # Create mock client that works as async context manager
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await claim_extractor.extract_claims(test_content)

        # Assert
        assert result["success"] is True
        assert "claims" in result
        assert len(result["claims"]) > 0
        assert result["claims"][0]["text"] == "Test claim about climate change"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
