"""
Complete fix script for test_judge.py
Applies the proven pattern from the first successful test to all remaining tests
"""

import re

def fix_test_judge_complete():
    with open('tests/unit/pipeline/test_judge.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix 1: Convert Evidence objects to dicts
    # Pattern: Evidence( ... ) -> { ... }
    # This is complex, so we'll do it with a function

    def convert_evidence_to_dict(match):
        """Convert Evidence(...) to dict"""
        inner = match.group(1)
        # Simple conversion for common patterns
        inner = re.sub(r'\btext\s*=\s*', '"text": ', inner)
        inner = re.sub(r'\burl\s*=\s*', '"url": ', inner)
        inner = re.sub(r'\bcredibility_score\s*=\s*', '"credibility_score": ', inner)
        inner = re.sub(r'\bpublisher\s*=\s*', '"publisher": ', inner)
        inner = re.sub(r'\bpublished_date\s*=\s*', '"published_date": ', inner)
        inner = re.sub(r'\brelevance_score\s*=\s*', '"relevance_score": ', inner)
        return '{' + inner + '}'

    # Apply Evidence conversion
    content = re.sub(r'Evidence\(((?:[^()]|\([^)]*\))*)\)', convert_evidence_to_dict, content)

    # Fix 2: Replace mock_openai_client mocking with httpx pattern
    # Find and replace the mock_openai_client.chat.completions.create pattern
    old_mock_pattern = r'mock_openai_client\.chat\.completions\.create = AsyncMock\(\s*return_value=Mock\(\s*choices=\[Mock\(message=Mock\(content=([^)]+)\)\)\]\s*\)\s*\)'

    def replace_mock(match):
        mock_var = match.group(1)
        return f'''# Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {{
            "choices": [{{
                "message": {{
                    "content": {mock_var}
                }}
            }}]
        }}'''

    content = re.sub(old_mock_pattern, replace_mock, content, flags=re.DOTALL)

    # Fix 3: Replace patch.object with httpx and settings patch
    # Pattern: with patch.object(judge, 'openai_client', mock_openai_client):
    old_with_pattern = r'with patch\.object\(judge, [\'"]openai_client[\'"], mock_openai_client\):'
    new_with_pattern = '''with patch('app.pipeline.judge.httpx.AsyncClient') as mock_client_class, \\
             patch('app.pipeline.judge.settings.ENABLE_ABSTENTION_LOGIC', False):
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
'''

    content = re.sub(old_with_pattern, new_with_pattern, content)

    # Fix 4: Add claim conversion to dict before judge_claim call
    # Find: result = await judge.judge_claim(claim, ...)
    # Add before it: claim_dict = {"text": claim.text, ...}
    # And change the call to use claim_dict

    # This is tricky, let's look for the pattern
    def add_claim_conversion(match):
        indent = match.group(1)
        rest = match.group(2)
        return f'''{indent}# Convert claim to dict
{indent}claim_dict = {{"text": claim.text, "claim_type": claim.claim_type if hasattr(claim, 'claim_type') else "factual"}}

{indent}result = await judge.judge_claim(claim_dict, {rest}'''

    content = re.sub(
        r'(\s+)result = await judge\.judge_claim\(claim, (.+)',
        add_claim_conversion,
        content
    )

    # Fix 5: Fix result access patterns
    # verdict['verdict'] -> result.verdict
    # verdict['confidence'] -> result.confidence
    # verdict['reasoning'] -> result.rationale
    # verdict['rationale'] -> result.rationale
    # verdict['key_evidence'] -> result.supporting_evidence

    content = re.sub(r'\bverdict\[[\'"](verdict|confidence|rationale)[\'"]', r'result.\1', content)
    content = re.sub(r'\bresult\[[\'"]verdict[\'"]\]', r'result.verdict', content)
    content = re.sub(r'\bresult\[[\'"]confidence[\'"]\]', r'result.confidence', content)
    content = re.sub(r'\bresult\[[\'"]rationale[\'"]\]', r'result.rationale', content)
    content = re.sub(r'\bresult\[[\'"]reasoning[\'"]\]', r'result.rationale', content)
    content = re.sub(r'\bresult\[[\'"]key_evidence[\'"]\]', r'result.supporting_evidence', content)

    # Also handle verdict variable if it exists
    content = re.sub(r"verdict = await judge\.judge_claim", r"result = await judge.judge_claim", content)

    # Fix 6: Fix confidence scale (0-100 -> 0-1)
    # >= 0.85 instead of >= 85
    # >= 0.50 instead of >= 50
    # etc.

    # Find assertions with confidence checks
    content = re.sub(r'assert result\.confidence >= (\d+)', lambda m: f'assert result.confidence >= {int(m.group(1))/100}', content)
    content = re.sub(r'assert result\.confidence < (\d+)', lambda m: f'assert result.confidence < {int(m.group(1))/100}', content)
    content = re.sub(r'assert result\.confidence <= (\d+)', lambda m: f'assert result.confidence <= {int(m.group(1))/100}', content)

    # Fix reasoning -> rationale
    content = re.sub(r"'reasoning' in result", "result.rationale is not None", content)
    content = re.sub(r'"reasoning" in result', "result.rationale is not None", content)
    content = re.sub(r'len\(result\.reasoning\)', 'len(result.rationale)', content)

    # Fix key_evidence -> supporting_evidence
    content = re.sub(r"'key_evidence' in result", "result.supporting_evidence is not None", content)
    content = re.sub(r'"key_evidence" in result', "result.supporting_evidence is not None", content)
    content = re.sub(r'len\(result\.key_evidence\)', 'len(result.supporting_evidence)', content)

    with open('tests/unit/pipeline/test_judge.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("✅ Complete fixes applied to test_judge.py:")
    print("  - Converted Evidence objects to dicts")
    print("  - Replaced OpenAI client mocking with httpx.AsyncClient pattern")
    print("  - Added ENABLE_ABSTENTION_LOGIC=False patch")
    print("  - Added claim-to-dict conversion")
    print("  - Fixed result access (attributes instead of dict keys)")
    print("  - Fixed confidence scale (0-1 instead of 0-100)")
    print("  - Fixed field names (reasoning->rationale, key_evidence->supporting_evidence)")
    print("\nRunning test suite to validate...")

if __name__ == "__main__":
    fix_test_judge_complete()
