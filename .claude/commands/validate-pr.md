Validate the current state of a Track A PR by running the grep checks from the audit documents.

Run ALL of these checks and report pass/fail for each:

```bash
# 1. No dead flags from PR-01
grep -r "ENABLE_SAFETY_CHECKING\|ENABLE_CITATION_ARCHIVAL\|ENABLE_VERDICT_MONITORING\|ENABLE_CROSS_ENCODER_RERANK\|ENABLE_QUERY_EXPANSION\|ENABLE_PRIMARY_SOURCE_DETECTION\|FEATURE_ROLLOUT_PERCENTAGE\|INTERNAL_USER_IDS" backend/app/ --include="*.py" || echo "PASS: No dead PR-01 flags"

# 2. No dead functions from PR-01
grep -r "generate_overall_assessment\|update_check_status_sync\|save_check_results_sync\|aggregate_api_stats" backend/app/ --include="*.py" || echo "PASS: No dead PR-01 functions"

# 3. No embedding path from PR-02
grep -r "_rank_evidence_with_embeddings\|ENABLE_SEMANTIC_RELEVANCE_FILTER\|SNIPPET_SEMANTIC_THRESHOLD" backend/app/ --include="*.py" || echo "PASS: No PR-02 embedding remnants"

# 4. No deleted filter stages from PR-03
grep -r "unknown_source_probation\|adaptive_fallback\|source_diversity_filter\|source_validation_filter\|ENABLE_PER_CLAIM_DOMAIN_CAPPING" backend/app/ --include="*.py" || echo "PASS: No PR-03 deleted filters"

# 5. No diagnostic prints from PR-05
grep -rn "print(" backend/app/pipeline/runner.py backend/app/pipeline/retrieve.py backend/app/workers/pipeline.py || echo "PASS: No print() in pipeline code"

# 6. No V1 frozen replay from PR-05
grep -r "frozen_urls" backend/app/pipeline/runner.py || echo "PASS: No V1 frozen replay"

# 7. No dead factcheck parsing from PR-05
grep -r "ENABLE_FACTCHECK_PARSING" backend/app/ --include="*.py" || echo "PASS: No factcheck parsing flag"
```

Report which checks pass and which fail. For failures, list the file:line locations.
