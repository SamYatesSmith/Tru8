"""
Script to systematically fix test_retrieve.py based on PHASE_1_TEST_FIX_PLAN template
Applies module-level patching pattern and fixes method names
"""

import re

def fix_test_retrieve():
    # Read the test file
    with open('tests/unit/pipeline/test_retrieve.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern 1: Remove fixture parameters from test signatures
    # Change: async def test_x(self, mock_search_api, mock_factcheck_api):
    # To:     async def test_x(self):
    content = re.sub(
        r'async def (test_\w+)\(self,\s*mock_search_api(?:,\s*mock_factcheck_api)?\)',
        r'async def \1(self)',
        content
    )

    # Pattern 2: Fix result access from claim.text to position "0"
    # Change: result.get(claim.text, [])
    # To:     result.get("0", [])
    content = re.sub(
        r'result\.get\(claim\.text,\s*\[\]\)',
        r'result.get("0", [])',
        content
    )

    # Pattern 3: Fix wrong method name .retrieve( to .retrieve_evidence_for_claims(
    content = re.sub(
        r'\.retrieve\(',
        r'.retrieve_evidence_for_claims(',
        content
    )

    # Write back
    with open('tests/unit/pipeline/test_retrieve.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("Fixed test_retrieve.py:")
    print("- Removed fixture parameters from test signatures")
    print("- Fixed result access to use position '0'")
    print("- Fixed method name to retrieve_evidence_for_claims")
    print("\nNote: Tests still need module-level mocking added manually")

if __name__ == "__main__":
    fix_test_retrieve()
