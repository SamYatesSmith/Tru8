-- API Integration Metrics Dashboard
-- Week 5: Internal Rollout Monitoring
--
-- Run these queries to monitor Government API Integration performance
-- Recommended: Set up as scheduled queries in your DB monitoring tool

-- =============================================================================
-- 1. PIPELINE PERFORMANCE (Target: P95 < 10s)
-- =============================================================================

-- P50, P95, P99 latency for checks with API retrieval
SELECT
    percentile_cont(0.50) WITHIN GROUP (ORDER BY processing_time_ms) AS p50_latency_ms,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY processing_time_ms) AS p95_latency_ms,
    percentile_cont(0.99) WITHIN GROUP (ORDER BY processing_time_ms) AS p99_latency_ms,
    AVG(processing_time_ms) AS avg_latency_ms,
    MIN(processing_time_ms) AS min_latency_ms,
    MAX(processing_time_ms) AS max_latency_ms,
    COUNT(*) AS total_checks_with_api,
    CASE
        WHEN percentile_cont(0.95) WITHIN GROUP (ORDER BY processing_time_ms) < 10000 THEN '✅ PASS'
        ELSE '❌ FAIL'
    END AS p95_target_status
FROM "check"
WHERE
    status = 'completed'
    AND api_call_count > 0
    AND created_at > NOW() - INTERVAL '24 hours';

-- =============================================================================
-- 2. API COVERAGE (Target: 20-30%)
-- =============================================================================

-- Percentage of checks using API data
SELECT
    COUNT(CASE WHEN api_call_count > 0 THEN 1 END) AS checks_with_api,
    COUNT(CASE WHEN api_call_count = 0 THEN 1 END) AS checks_without_api,
    COUNT(*) AS total_checks,
    ROUND(
        COUNT(CASE WHEN api_call_count > 0 THEN 1 END)::numeric /
        NULLIF(COUNT(*), 0)::numeric * 100,
        2
    ) AS api_coverage_percentage,
    ROUND(
        AVG(CASE WHEN api_call_count > 0 THEN api_coverage_percentage END),
        2
    ) AS avg_api_evidence_percentage,
    CASE
        WHEN ROUND(
            COUNT(CASE WHEN api_call_count > 0 THEN 1 END)::numeric /
            NULLIF(COUNT(*), 0)::numeric * 100,
            2
        ) BETWEEN 20 AND 30 THEN '✅ ON TARGET'
        WHEN ROUND(
            COUNT(CASE WHEN api_call_count > 0 THEN 1 END)::numeric /
            NULLIF(COUNT(*), 0)::numeric * 100,
            2
        ) > 30 THEN '⚠️ ABOVE TARGET'
        ELSE '⚠️ BELOW TARGET'
    END AS coverage_status
FROM "check"
WHERE
    status = 'completed'
    AND created_at > NOW() - INTERVAL '24 hours';

-- =============================================================================
-- 3. API SOURCES USED (Most Popular)
-- =============================================================================

-- Most frequently used APIs
SELECT
    api->>'name' AS api_name,
    COUNT(*) AS times_used,
    SUM((api->>'results')::int) AS total_results_returned,
    ROUND(AVG((api->>'results')::int), 2) AS avg_results_per_call,
    ROUND(
        COUNT(*)::numeric /
        SUM(COUNT(*)) OVER () * 100,
        2
    ) AS usage_percentage
FROM "check",
     jsonb_array_elements(api_sources_used::jsonb) AS api
WHERE
    created_at > NOW() - INTERVAL '24 hours'
    AND api_sources_used IS NOT NULL
GROUP BY api->>'name'
ORDER BY times_used DESC;

-- =============================================================================
-- 4. ERROR RATES (Target: <1%)
-- =============================================================================

-- Error rate by status
SELECT
    status,
    COUNT(*) AS count,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER () * 100, 2) AS percentage,
    CASE
        WHEN status = 'failed' AND
             ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER () * 100, 2) < 1 THEN '✅ PASS'
        WHEN status = 'failed' THEN '❌ FAIL (>1% error rate)'
        ELSE '✅ OK'
    END AS status_check
FROM "check"
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY status
ORDER BY count DESC;

-- Error details for failed checks
SELECT
    error_message,
    COUNT(*) AS occurrences,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER () * 100, 2) AS percentage_of_errors,
    MAX(created_at) AS last_occurrence
FROM "check"
WHERE
    status = 'failed'
    AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY error_message
ORDER BY occurrences DESC
LIMIT 10;

-- =============================================================================
-- 5. LATENCY COMPARISON (With API vs Without API)
-- =============================================================================

-- Compare performance with and without API retrieval
SELECT
    CASE WHEN api_call_count > 0 THEN 'With API' ELSE 'Without API' END AS mode,
    COUNT(*) AS checks,
    ROUND(AVG(processing_time_ms), 0) AS avg_latency_ms,
    percentile_cont(0.50) WITHIN GROUP (ORDER BY processing_time_ms) AS p50_ms,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY processing_time_ms) AS p95_ms,
    percentile_cont(0.99) WITHIN GROUP (ORDER BY processing_time_ms) AS p99_ms
FROM "check"
WHERE
    status = 'completed'
    AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY CASE WHEN api_call_count > 0 THEN 'With API' ELSE 'Without API' END
ORDER BY mode DESC;

-- =============================================================================
-- 6. HOURLY TRENDS
-- =============================================================================

-- API usage and performance by hour
SELECT
    DATE_TRUNC('hour', created_at) AS hour,
    COUNT(*) AS total_checks,
    COUNT(CASE WHEN api_call_count > 0 THEN 1 END) AS checks_with_api,
    ROUND(
        COUNT(CASE WHEN api_call_count > 0 THEN 1 END)::numeric /
        NULLIF(COUNT(*), 0)::numeric * 100,
        2
    ) AS api_coverage_pct,
    ROUND(AVG(processing_time_ms), 0) AS avg_latency_ms,
    ROUND(AVG(CASE WHEN api_call_count > 0 THEN api_call_count END), 1) AS avg_api_calls_per_check
FROM "check"
WHERE
    status = 'completed'
    AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', created_at)
ORDER BY hour DESC;

-- =============================================================================
-- 7. CLAIM DOMAIN DISTRIBUTION
-- =============================================================================

-- Which domains are getting API coverage
SELECT
    c.subject_context AS domain,
    COUNT(*) AS claims,
    COUNT(CASE WHEN ch.api_call_count > 0 THEN 1 END) AS claims_with_api,
    ROUND(
        COUNT(CASE WHEN ch.api_call_count > 0 THEN 1 END)::numeric /
        NULLIF(COUNT(*), 0)::numeric * 100,
        2
    ) AS api_coverage_pct,
    ROUND(AVG(ch.processing_time_ms), 0) AS avg_latency_ms
FROM "claim" c
JOIN "check" ch ON c.check_id = ch.id
WHERE
    ch.created_at > NOW() - INTERVAL '24 hours'
    AND ch.status = 'completed'
    AND c.subject_context IS NOT NULL
GROUP BY c.subject_context
ORDER BY claims DESC
LIMIT 10;

-- =============================================================================
-- 8. EVIDENCE SOURCE BREAKDOWN
-- =============================================================================

-- API evidence vs Web evidence
SELECT
    CASE
        WHEN e.external_source_provider IS NOT NULL THEN 'API Evidence'
        ELSE 'Web Evidence'
    END AS evidence_type,
    COUNT(*) AS count,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER () * 100, 2) AS percentage,
    ROUND(AVG(e.credibility_score), 3) AS avg_credibility,
    ROUND(AVG(e.relevance_score), 3) AS avg_relevance
FROM "evidence" e
JOIN "claim" c ON e.claim_id = c.id
JOIN "check" ch ON c.check_id = ch.id
WHERE
    ch.created_at > NOW() - INTERVAL '24 hours'
    AND ch.status = 'completed'
GROUP BY CASE
    WHEN e.external_source_provider IS NOT NULL THEN 'API Evidence'
    ELSE 'Web Evidence'
END;

-- Top API sources by evidence count
SELECT
    e.external_source_provider AS api_source,
    COUNT(*) AS evidence_count,
    ROUND(AVG(e.credibility_score), 3) AS avg_credibility,
    ROUND(AVG(e.relevance_score), 3) AS avg_relevance,
    COUNT(DISTINCT c.check_id) AS checks_used_in
FROM "evidence" e
JOIN "claim" c ON e.claim_id = c.id
JOIN "check" ch ON c.check_id = ch.id
WHERE
    ch.created_at > NOW() - INTERVAL '24 hours'
    AND ch.status = 'completed'
    AND e.external_source_provider IS NOT NULL
GROUP BY e.external_source_provider
ORDER BY evidence_count DESC;

-- =============================================================================
-- 9. SLOW QUERIES (Investigations)
-- =============================================================================

-- Checks that took longer than 10s
SELECT
    id,
    created_at,
    processing_time_ms,
    api_call_count,
    ROUND(processing_time_ms / 1000.0, 1) AS processing_time_sec,
    api_coverage_percentage,
    input_type,
    LEFT(input_content::text, 100) AS input_preview
FROM "check"
WHERE
    status = 'completed'
    AND processing_time_ms > 10000
    AND created_at > NOW() - INTERVAL '24 hours'
ORDER BY processing_time_ms DESC
LIMIT 20;

-- =============================================================================
-- 10. CACHE EFFECTIVENESS (Indirect Measure)
-- =============================================================================

-- API calls per check (lower with good caching)
SELECT
    api_call_count AS api_calls,
    COUNT(*) AS checks,
    ROUND(COUNT(*)::numeric / SUM(COUNT(*)) OVER () * 100, 2) AS percentage
FROM "check"
WHERE
    api_call_count > 0
    AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY api_call_count
ORDER BY api_call_count;

-- Average API calls per check (should be low with caching)
SELECT
    ROUND(AVG(api_call_count), 2) AS avg_api_calls_per_check,
    MAX(api_call_count) AS max_api_calls,
    CASE
        WHEN AVG(api_call_count) <= 3 THEN '✅ Good (caching likely working)'
        WHEN AVG(api_call_count) <= 5 THEN '⚠️ Moderate'
        ELSE '❌ High (check cache)'
    END AS cache_health_indicator
FROM "check"
WHERE
    api_call_count > 0
    AND created_at > NOW() - INTERVAL '24 hours';

-- =============================================================================
-- 11. SUMMARY DASHBOARD (All-in-One)
-- =============================================================================

-- Single query for overall health check
SELECT
    -- Counts
    COUNT(*) AS total_checks_24h,
    COUNT(CASE WHEN api_call_count > 0 THEN 1 END) AS checks_with_api,

    -- Coverage
    ROUND(
        COUNT(CASE WHEN api_call_count > 0 THEN 1 END)::numeric /
        NULLIF(COUNT(*), 0)::numeric * 100,
        2
    ) AS api_coverage_pct,

    -- Performance
    ROUND(AVG(processing_time_ms), 0) AS avg_latency_ms,
    ROUND(percentile_cont(0.95) WITHIN GROUP (ORDER BY processing_time_ms), 0) AS p95_latency_ms,

    -- Error Rate
    ROUND(
        COUNT(CASE WHEN status = 'failed' THEN 1 END)::numeric /
        NULLIF(COUNT(*), 0)::numeric * 100,
        2
    ) AS error_rate_pct,

    -- Status Checks
    CASE
        WHEN ROUND(percentile_cont(0.95) WITHIN GROUP (ORDER BY processing_time_ms), 0) < 10000
        THEN '✅' ELSE '❌'
    END AS p95_target,

    CASE
        WHEN ROUND(
            COUNT(CASE WHEN api_call_count > 0 THEN 1 END)::numeric /
            NULLIF(COUNT(*), 0)::numeric * 100, 2
        ) BETWEEN 20 AND 30 THEN '✅'
        ELSE '⚠️'
    END AS coverage_target,

    CASE
        WHEN ROUND(
            COUNT(CASE WHEN status = 'failed' THEN 1 END)::numeric /
            NULLIF(COUNT(*), 0)::numeric * 100, 2
        ) < 1 THEN '✅'
        ELSE '❌'
    END AS error_rate_target

FROM "check"
WHERE
    status IN ('completed', 'failed')
    AND created_at > NOW() - INTERVAL '24 hours';

-- =============================================================================
-- NOTES
-- =============================================================================
--
-- Run these queries in your preferred SQL client or monitoring tool
--
-- Recommended Monitoring Setup:
-- - Query 11 (Summary Dashboard): Every 5 minutes, alert on failures
-- - Query 1 (Performance): Every 15 minutes
-- - Query 2 (Coverage): Every hour
-- - Query 4 (Errors): Every 5 minutes, alert on >1%
--
-- For Grafana/Similar:
-- - Create panels for each query
-- - Set refresh intervals as recommended
-- - Configure alerts based on target thresholds
--
-- Cache Metrics:
-- - Use REST API endpoints for cache hit rates
-- - curl http://localhost:8000/api/v1/health/cache-metrics
-- - These queries measure indirect effects of caching
