"""
Fix script for test_retrieve.py Batch 2 and remaining tests
Applies systematic fixes for common patterns
"""

import re

def fix_test_retrieve():
    with open('tests/unit/pipeline/test_retrieve.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix 1: Replace claim.text as dict key with position "0"
    content = re.sub(
        r'result\.get\(claim\.text, \[\]\)',
        'result.get("0", [])',
        content
    )

    # Fix 2: Replace object attribute access with dict access for evidence
    # e.url → e.get("url") or e["url"]
    content = re.sub(
        r'(\w+)\.url\.split',
        r'\1.get("url").split',
        content
    )
    content = re.sub(
        r'(\w+)\.credibility_score',
        r'\1.get("credibility_score", 0)',
        content
    )
    content = re.sub(
        r'(\w+)\.relevance_score',
        r'\1.get("relevance_score", 0)',
        content
    )

    # Fix 3: Replace method calls from retrieve() to retrieve_evidence_for_claims()
    content = re.sub(
        r'await retriever\.retrieve\(claim\)',
        'await retriever.retrieve_evidence_for_claims([claim_dict])',
        content
    )

    # Fix 4: Remove patch.object for non-existent search_api and factcheck_api
    # These tests should use the EvidenceExtractor mocking pattern instead

    # Fix 5: Fix credibility score comparisons (0-100 → 0-1)
    # This is more complex and will need manual review

    with open('tests/unit/pipeline/test_retrieve.py', 'w', encoding='utf-8') as f:
        f.write(content)

    print("Batch 2 fixes applied:")
    print("  - Fixed result.get(claim.text) to result.get('0')")
    print("  - Fixed attribute access to dict access (e.url to e.get('url'))")
    print("  - Fixed method calls (retrieve to retrieve_evidence_for_claims)")
    print("\nPlease review and run tests to validate")

if __name__ == "__main__":
    fix_test_retrieve()
