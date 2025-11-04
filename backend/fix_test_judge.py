"""
Script to systematically fix test_judge.py
Applies httpx.AsyncClient mocking pattern from test_extract.py
"""

import re

def fix_test_judge():
    with open('tests/unit/pipeline/test_judge.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix 1: Remove mock_openai_client fixture parameter
    content = re.sub(
        r'async def (test_\w+)\(self,\s*mock_openai_client\)',
        r'async def \1(self)',
        content
    )

    # Fix 2: Change generate_verdict to judge_claim
    content = re.sub(
        r'\.generate_verdict\(',
        r'.judge_claim(',
        content
    )

    # Fix 3: Fix undefined Judge class reference
    # Look for 'Judge(' and replace with 'ClaimJudge('
    content = re.sub(
        r'\bJudge\(',
        r'ClaimJudge(',
        content
    )

    with open('tests/unit/pipeline/test_judge.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("Phase 1 fixes applied to test_judge.py:")
    print("- Removed mock_openai_client fixture parameters")
    print("- Changed generate_verdict() to judge_claim()")
    print("- Fixed undefined Judge class to ClaimJudge")
    print("\nNote: Manual fixes still needed for:")
    print("- Adding httpx.AsyncClient mocking")
    print("- Fixing method parameters (claim dict, verification_signals dict, evidence list)")
    print("- Updating result access patterns")

if __name__ == "__main__":
    fix_test_judge()
