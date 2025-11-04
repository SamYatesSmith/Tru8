#!/usr/bin/env python3
"""
Fix test_retrieve.py to match actual EvidenceRetriever implementation

Actual signature:
    retrieve_evidence_for_claims(claims: List[Dict], exclude_source_url: Optional[str]) -> Dict[str, List[Dict]]

Changes needed:
1. Convert Claim objects to dicts
2. Call retrieve_evidence_for_claims([claim_dict]) instead of retrieve(claim)
3. Extract evidence from returned dict: result[claim.text]
4. Change assertions from hasattr() to dict key checks

Created: 2025-11-03
"""

import re

def fix_retrieve_tests():
    filepath = 'tests/unit/pipeline/test_retrieve.py'

    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Fix 1: Replace retriever.retrieve(claim) with proper call
    # Pattern: await retriever.retrieve(claim)
    # Replace with: await retriever.retrieve_evidence_for_claims([{"text": claim.text, ...}])

    # This is complex, so let's do it in steps

    # Step 1: Replace method name
    content = content.replace(
        'evidence_list = await retriever.retrieve(claim)',
        '''claim_dict = {
            "text": claim.text,
            "subject_context": claim.subject_context,
            "key_entities": claim.key_entities,
            "is_time_sensitive": claim.is_time_sensitive,
            "claim_type": claim.claim_type
        }
        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = result.get(claim.text, [])'''
    )

    content = content.replace(
        'evidence_list = await retriever.retrieve(test_claim)',
        '''claim_dict = {
            "text": test_claim.text,
            "subject_context": test_claim.subject_context if hasattr(test_claim, 'subject_context') else None,
            "key_entities": test_claim.key_entities if hasattr(test_claim, 'key_entities') else [],
            "is_time_sensitive": test_claim.is_time_sensitive if hasattr(test_claim, 'is_time_sensitive') else False,
            "claim_type": test_claim.claim_type if hasattr(test_claim, 'claim_type') else "factual"
        }
        result = await retriever.retrieve_evidence_for_claims([claim_dict])
        evidence_list = result.get(test_claim.text, [])'''
    )

    # Step 2: Replace hasattr checks with dict key checks for evidence objects
    content = re.sub(
        r'assert hasattr\(evidence, \'([^\']+)\'\)',
        r'assert "\1" in evidence',
        content
    )

    # Step 3: Replace attribute access with dict access
    content = re.sub(
        r'evidence\.credibility_score',
        r'evidence["credibility_score"]',
        content
    )

    content = re.sub(
        r'evidence\.url',
        r'evidence["url"]',
        content
    )

    content = re.sub(
        r'evidence\.publisher',
        r'evidence["publisher"]',
        content
    )

    content = re.sub(
        r'evidence\.text',
        r'evidence["text"]',
        content
    )

    content = re.sub(
        r'evidence\.published_date',
        r'evidence.get("published_date")',
        content
    )

    content = re.sub(
        r'evidence\.relevance_score',
        r'evidence.get("relevance_score", 0)',
        content
    )

    content = re.sub(
        r'evidence\.is_factcheck',
        r'evidence.get("is_factcheck", False)',
        content
    )

    content = re.sub(
        r'evidence\.rating',
        r'evidence.get("rating")',
        content
    )

    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print("SUCCESS: Fixed test_retrieve.py")
    print("  - Updated method calls to retrieve_evidence_for_claims()")
    print("  - Converted Claim objects to dicts")
    print("  - Fixed evidence assertions to use dict keys")

if __name__ == '__main__':
    fix_retrieve_tests()
