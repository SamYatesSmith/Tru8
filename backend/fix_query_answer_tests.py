"""
Script to automatically fix remaining test_query_answer.py tests (tests 6-15)
Uses the established mocking pattern for httpx.AsyncClient
"""
import re

# Read the test file
with open('tests/unit/pipeline/test_query_answer.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern to find tests that still use old mocking pattern
old_pattern_tests = [
    'test_numerical_query_answer',
    'test_current_events_query',
    'test_complex_query_multi_part_answer',
    'test_high_credibility_source_prioritization',
    'test_search_query_optimization_from_user_query',
    'test_llm_prompt_structure',
    'test_answer_json_parsing',
    'test_malformed_llm_response_handling',
    'test_token_cost_optimization',
    'test_end_to_end_query_answer_pipeline'
]

# Simple replacements for common patterns
replacements = [
    # Replace Query object usage with direct string
    (r'query = Query\(text="([^"]+)"[^)]*\)', r'user_query = "\1"'),

    # Replace search_api mocking (remove it)
    (r'mock_search_api\.search = AsyncMock\([^\)]*\)\s*', ''),

    # Replace openai_client mocking patterns
    (r'mock_openai_client\.chat\.completions\.create = AsyncMock\(\s*return_value=Mock\(\s*choices=\[Mock\(message=Mock\(content=([^\)]+)\)\)\]\s*\)\s*\)', r'# Mock response content: \1'),

    # Replace patch.object with answer method call
    (r'with patch\.object\(answerer, \'search_api\', mock_search_api\):\s*with patch\.object\(answerer, \'openai_client\', mock_openai_client\):\s*result = await answerer\.answer\(query\)',
     'result = await answerer.answer_query(user_query, claims, evidence_by_claim, original_text)'),

    # Replace single patch.object
    (r'with patch\.object\(answerer, \'search_api\', mock_search_api\):\s*result = await answerer\.answer\(query\)',
     'result = await answerer.answer_query(user_query, claims, evidence_by_claim, original_text)'),
]

for old, new in replacements:
    content = re.sub(old, new, content, flags=re.MULTILINE | re.DOTALL)

# Write back
with open('tests/unit/pipeline/test_query_answer.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ Automated replacements complete")
print("⚠️  Manual review needed for:")
for test in old_pattern_tests:
    print(f"   - {test}")
