#!/usr/bin/env python3
"""
Fix test_extract.py to use proper mocking strategy for ClaimExtractor

The issue: ClaimExtractor doesn't accept a client parameter, it uses httpx.AsyncClient internally
Solution: Patch httpx.AsyncClient at the module level in each test
"""

import re

def fix_test_extract():
    filepath = 'tests/unit/pipeline/test_extract.py'

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix 1: Replace the fixture completely
    old_fixture = '''    @pytest.fixture
    def mock_openai_client(self):
        """
        Create mock OpenAI client

        Created: 2025-11-03
        """
        client = AsyncMock()
        return client

    @pytest.fixture
    def claim_extractor(self, mock_openai_client):
        """
        Create ClaimExtractor with mock client

        Created: 2025-11-03
        """
        return ClaimExtractor(client=mock_openai_client)'''

    new_fixture = '''    @pytest.fixture
    def claim_extractor(self):
        """
        Create ClaimExtractor instance

        Created: 2025-11-03
        Note: ClaimExtractor() uses httpx.AsyncClient internally
        """
        return ClaimExtractor()'''

    content = content.replace(old_fixture, new_fixture)

    # Fix 2: Remove mock_openai_client parameter from all test method signatures
    content = re.sub(
        r'(async def test_[^(]+\(self, claim_extractor), mock_openai_client\)',
        r'\1)',
        content
    )

    # Fix 3: Replace all mock_openai_client.chat.completions.create patterns
    # with proper httpx patching context

    # Pattern 1: Simple mock with return value
    pattern1 = r"mock_openai_client\.chat\.completions\.create = AsyncMock\(\s*return_value=Mock\(\s*choices=\[Mock\(message=Mock\(content=([^)]+)\)\)\]\s*\)\s*\)"

    def replacement1(match):
        mock_content = match.group(1)
        return f'''mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {{
            "choices": [{{
                "message": {{
                    "content": {mock_content}
                }}
            }}]
        }}

        # Patch httpx.AsyncClient at module level
        with patch('app.pipeline.extract.httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client'''

    # This is complex - let me do simpler replacements
    # Just replace the mock setup and wrap Act sections with patches

    # Simpler approach: Replace mock_openai_client with inline httpx patching
    lines = content.split('\n')
    new_lines = []
    in_test_method = False
    indent_level = 0

    for i, line in enumerate(lines):
        # Detect test method start
        if 'async def test_' in line and '(self, claim_extractor)' in line:
            in_test_method = True
            new_lines.append(line)
            continue

        # Replace mock_openai_client.chat.completions.create
        if 'mock_openai_client.chat.completions.create' in line:
            # Get indentation
            indent = len(line) - len(line.lstrip())
            spaces = ' ' * indent

            if 'return_value=Mock(' in line and 'choices=' in line:
                # Extract the mock content
                match = re.search(r'content=([^)]+)\)', line)
                if match:
                    mock_content = match.group(1)
                    # Add the proper httpx mock setup
                    new_lines.append(f'{spaces}# Arrange - Mock httpx response')
                    new_lines.append(f'{spaces}mock_response = Mock()')
                    new_lines.append(f'{spaces}mock_response.status_code = 200')
                    new_lines.append(f'{spaces}mock_response.json.return_value = {{')
                    new_lines.append(f'{spaces}    "choices": [{{')
                    new_lines.append(f'{spaces}        "message": {{"content": {mock_content}}}')
                    new_lines.append(f'{spaces}    }}]')
                    new_lines.append(f'{spaces}}}')
                    continue
            elif 'side_effect=' in line:
                # Keep side_effect lines, we'll handle them differently
                new_lines.append(line.replace('mock_openai_client.', '# mock_openai_client.'))
                continue

        # Replace call_args access
        if 'mock_openai_client.chat.completions.create.call_args' in line:
            line = line.replace('mock_openai_client.chat.completions.create.call_args',
                               'mock_client.post.call_args')

        new_lines.append(line)

    content = '\n'.join(new_lines)

    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print("✓ Fixed test_extract.py")
    print("  - Updated fixtures")
    print("  - Removed mock_openai_client parameters")
    print("  - Replaced mock setup patterns")

if __name__ == '__main__':
    fix_test_extract()
