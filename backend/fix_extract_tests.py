import re

# Read the original file
with open('tests/unit/pipeline/test_extract.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Update fixtures
content = content.replace(
    '''    @pytest.fixture
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
        return ClaimExtractor(client=mock_openai_client)''',
    '''    @pytest.fixture
    def claim_extractor(self):
        """
        Create ClaimExtractor instance
        
        Created: 2025-11-03
        """
        return ClaimExtractor()'''
)

# Fix 2: Remove mock_openai_client from test signatures
content = re.sub(
    r'async def test_([^(]+)\(self, claim_extractor, mock_openai_client\)',
    r'async def test_\1(self, claim_extractor)',
    content
)

# Fix 3: Replace extract() with extract_claims()
content = content.replace('.extract(', '.extract_claims(')

# Fix 4: Replace result checks to use dict format
content = re.sub(
    r'result = await claim_extractor\.extract_claims\(([^)]+)\)\s*\n\s*#\s*Assert\s*\n\s*assert isinstance\(result, list\)',
    r'result = await claim_extractor.extract_claims(\1)\n        # Assert\n        assert result["success"] is True\n        assert isinstance(result["claims"], list)',
    content
)

# Fix 5: Replace direct result access with result["claims"]
content = re.sub(r'assert len\(result\) > 0', 'assert len(result["claims"]) > 0', content)
content = re.sub(r'assert len\(result\) <= 12', 'assert len(result["claims"]) <= 12', content)
content = re.sub(r'assert len\(result\) == 0', 'assert len(result.get("claims", [])) == 0', content)
content = re.sub(r'for claim in result:', 'for claim in result.get("claims", []):', content)
content = re.sub(r'first_claim = result\[0\]', 'first_claim = result["claims"][0]', content)
content = re.sub(r'assert all\(hasattr\(claim, \'([^\']+)\'\) for claim in result\)',
                r'assert all("\1" in claim for claim in result["claims"])', content)

# Fix 6: Replace hasattr checks with dict key checks  
content = re.sub(r'hasattr\(([^,]+), \'([^\']+)\'\)', r'"\2" in \1', content)
content = re.sub(r'hasattr\(([^,]+),\'([^\']+)\'\)', r'"\2" in \1', content)

# Fix 7: Comment out httpx mock setup lines (we'll handle differently)
lines = content.split('\n')
new_lines = []
skip_next = 0

for i, line in enumerate(lines):
    if skip_next > 0:
        skip_next -= 1
        continue
        
    # Remove old mock_openai_client setup
    if 'mock_openai_client.chat.completions.create' in line:
        # Skip this and related lines, we need different mocking
        # Just comment it out for now
        new_lines.append('        # TODO: Add httpx.AsyncClient mocking here')
        # Skip until we hit blank line or next section
        j = i + 1
        while j < len(lines) and lines[j].strip() and not lines[j].strip().startswith('#'):
            if 'await claim_extractor' in lines[j]:
                break
            j += 1
        skip_next = j - i - 1
        continue
    
    new_lines.append(line)

content = '\n'.join(new_lines)

# Write back
with open('tests/unit/pipeline/test_extract.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESS: Fixed test_extract.py basic structure")
print("  Note: Tests will need httpx mocking added to each test")
print("  Pattern: See test_extract_minimal.py for working example")

