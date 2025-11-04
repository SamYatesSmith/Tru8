#!/usr/bin/env python3
"""
Complete test_extract.py by adding httpx.AsyncClient mocking to all tests

This script applies the proven mocking pattern from test_extract_minimal.py
to all 24 tests in test_extract.py.

Working pattern:
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{
            "message": {"content": MOCK_CLAIM_EXTRACTION}
        }]
    }

    with patch('app.pipeline.extract.httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        result = await claim_extractor.extract_claims(content)

Created: 2025-11-03
"""

import re

def fix_test_extract():
    filepath = 'tests/unit/pipeline/test_extract.py'

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern 1: Replace "# TODO: Add httpx.AsyncClient mocking here" followed by "# Act"
    # with the proper mocking setup

    # For tests that use MOCK_CLAIM_EXTRACTION (standard response)
    pattern1 = r'(\s+)# TODO: Add httpx\.AsyncClient mocking here\s+# Act\s+result = await claim_extractor\.extract_claims\(([^)]+)\)'

    def replacement1(match):
        indent = match.group(1)
        content_arg = match.group(2)
        return f'''{indent}# Mock httpx response
{indent}mock_response = Mock()
{indent}mock_response.status_code = 200
{indent}mock_response.json.return_value = {{
{indent}    "choices": [{{
{indent}        "message": {{
{indent}            "content": MOCK_CLAIM_EXTRACTION
{indent}        }}
{indent}    }}]
{indent}}}

{indent}# Act
{indent}with patch('app.pipeline.extract.httpx.AsyncClient') as mock_client_class:
{indent}    mock_client = AsyncMock()
{indent}    mock_client.__aenter__.return_value = mock_client
{indent}    mock_client.__aexit__.return_value = None
{indent}    mock_client.post = AsyncMock(return_value=mock_response)
{indent}    mock_client_class.return_value = mock_client
{indent}
{indent}    result = await claim_extractor.extract_claims({content_arg})'''

    content = re.sub(pattern1, replacement1, content)

    # Pattern 2: For tests that define custom mock_response before TODO
    # These have: mock_response = json.dumps({...}) BEFORE the TODO
    pattern2 = r'(\s+)(mock_response = json\.dumps\([^)]+\)\s+\))\s+# TODO: Add httpx\.AsyncClient mocking here\s+# Act\s+result = await claim_extractor\.extract_claims\(([^)]+)\)'

    def replacement2(match):
        indent = match.group(1)
        mock_json_def = match.group(2)
        content_arg = match.group(3)
        return f'''{indent}{mock_json_def}

{indent}# Mock httpx response
{indent}mock_http_response = Mock()
{indent}mock_http_response.status_code = 200
{indent}mock_http_response.json.return_value = {{
{indent}    "choices": [{{
{indent}        "message": {{
{indent}            "content": mock_response
{indent}        }}
{indent}    }}]
{indent}}}

{indent}# Act
{indent}with patch('app.pipeline.extract.httpx.AsyncClient') as mock_client_class:
{indent}    mock_client = AsyncMock()
{indent}    mock_client.__aenter__.return_value = mock_client
{indent}    mock_client.__aexit__.return_value = None
{indent}    mock_client.post = AsyncMock(return_value=mock_http_response)
{indent}    mock_client_class.return_value = mock_client
{indent}
{indent}    result = await claim_extractor.extract_claims({content_arg})'''

    content = re.sub(pattern2, replacement2, content, flags=re.DOTALL)

    # Fix import to include mocks.llm_responses
    if 'from mocks.llm_responses import' not in content:
        content = content.replace(
            "try:\n    from llm_responses import",
            "try:\n    from mocks.llm_responses import"
        )

    if 'from sample_content import' not in content:
        content = content.replace(
            "from sample_content import",
            "from mocks.sample_content import"
        )

    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print("SUCCESS: Completed test_extract.py httpx mocking")
    print("  - Applied httpx.AsyncClient mocking pattern to all tests")
    print("  - Fixed import paths for mocks")

if __name__ == '__main__':
    fix_test_extract()
