#!/usr/bin/env python3
"""
Tru8 Cost Analysis - Current Configuration
Estimates costs for 300 users with 25-40 claims/month average
"""

# GPT-4o-mini pricing (November 2024)
INPUT_COST_PER_1M = 0.150  # USD per 1M tokens
OUTPUT_COST_PER_1M = 0.600  # USD per 1M tokens

# Estimated tokens per check (based on codebase analysis)
# 1 check = ~5 claims average

# Extract stage (once per check)
EXTRACT_INPUT = 2500   # Article content
EXTRACT_OUTPUT = 1000  # Claims JSON with metadata

# Judge stage (5 claims × per claim tokens)
JUDGE_INPUT_PER_CLAIM = 1800   # Claim + evidence snippets (5 sources × 400 chars)
JUDGE_OUTPUT_PER_CLAIM = 600   # Verdict JSON
CLAIMS_PER_CHECK = 5

# Unknown source credibility assessment (4 sources per check average)
UNKNOWN_SOURCES = 4
UNKNOWN_INPUT_PER_SOURCE = 400
UNKNOWN_OUTPUT_PER_SOURCE = 200

# Query Answer stage (if used, ~20% of checks with Search Clarity enabled)
QUERY_INPUT = 600
QUERY_OUTPUT = 250
QUERY_USAGE_RATE = 0.2  # 20% of checks

# Calculate total tokens per check
total_input = (
    EXTRACT_INPUT +
    (JUDGE_INPUT_PER_CLAIM * CLAIMS_PER_CHECK) +
    (UNKNOWN_SOURCES * UNKNOWN_INPUT_PER_SOURCE) +
    (QUERY_INPUT * QUERY_USAGE_RATE)
)

total_output = (
    EXTRACT_OUTPUT +
    (JUDGE_OUTPUT_PER_CLAIM * CLAIMS_PER_CHECK) +
    (UNKNOWN_SOURCES * UNKNOWN_OUTPUT_PER_SOURCE) +
    (QUERY_OUTPUT * QUERY_USAGE_RATE)
)

# Calculate costs per check
input_cost_per_check = (total_input / 1_000_000) * INPUT_COST_PER_1M
output_cost_per_check = (total_output / 1_000_000) * OUTPUT_COST_PER_1M
total_cost_per_check = input_cost_per_check + output_cost_per_check

print("=" * 70)
print("TRU8 COST ANALYSIS - CURRENT CONFIGURATION")
print("=" * 70)
print()
print("MODEL: GPT-4o-mini-2024-07-18")
print(f"  Input:  ${INPUT_COST_PER_1M} per 1M tokens")
print(f"  Output: ${OUTPUT_COST_PER_1M} per 1M tokens")
print()
print("=" * 70)
print("PER CHECK BREAKDOWN")
print("=" * 70)
print()
print("Token Usage:")
print(f"  Input tokens:  {total_input:>8,.0f}")
print(f"  Output tokens: {total_output:>8,.0f}")
print(f"  Total tokens:  {total_input + total_output:>8,.0f}")
print()
print("Cost Breakdown:")
print(f"  Input cost:    ${input_cost_per_check:>7.5f}")
print(f"  Output cost:   ${output_cost_per_check:>7.5f}")
print(f"  TOTAL/check:   ${total_cost_per_check:>7.5f}")
print()
print("=" * 70)
print("300 USER SCENARIOS (varying usage)")
print("=" * 70)
print()

scenarios = [
    ("Low Usage", 25),
    ("Average Usage", 32),
    ("High Usage", 40),
]

for scenario_name, avg_claims_per_user in scenarios:
    print(f"{scenario_name}: {avg_claims_per_user} claims/user/month")
    print("-" * 70)

    total_claims = 300 * avg_claims_per_user
    total_checks = total_claims / CLAIMS_PER_CHECK

    # LLM costs
    monthly_llm_cost = total_checks * total_cost_per_check

    # Brave Search costs
    brave_queries = total_checks * 1.5  # Average 1.5 queries per check
    if brave_queries <= 2500:
        brave_cost = 0
        brave_tier = "FREE tier"
    else:
        brave_cost = 5
        brave_tier = "Paid tier ($5/month)"

    # Total costs
    total_monthly_cost = monthly_llm_cost + brave_cost
    cost_per_user = total_monthly_cost / 300

    print(f"  Total claims:      {total_claims:>8,}")
    print(f"  Total checks:      {total_checks:>8,.0f}")
    print()
    print(f"  LLM costs:         ${monthly_llm_cost:>7.2f}/month")
    print(f"  Brave Search:      ${brave_cost:>7.2f}/month ({brave_tier})")
    print(f"  ---------------------------")
    print(f"  TOTAL MONTHLY:     ${total_monthly_cost:>7.2f}/month")
    print(f"  Cost per user:     ${cost_per_user:>7.3f}/month")
    print()

print("=" * 70)
print("OTHER API COSTS")
print("=" * 70)
print()
print("Government APIs (Phase 5) - ALL FREE:")
print("  - GovInfo.gov (US legal statutes)")
print("  - ONS (UK finance/demographics)")
print("  - PubMed (health/science)")
print("  - WHO (global health)")
print("  - CrossRef (academic research)")
print("  - GOV.UK (UK government)")
print("  - Hansard (UK parliament)")
print("  - Wikidata (general knowledge)")
print("  - Companies House (UK companies)")
print("  - FRED (US economic data)")
print("  - Met Office (UK weather)")
print()
print("Local Models - NO API COSTS:")
print("  - NLI verification: DeBERTa-v3-large (runs locally)")
print("  - Embeddings: all-MiniLM-L6-v2 (runs locally)")
print()
print("=" * 70)
print("REVENUE ANALYSIS (£1,500/month target)")
print("=" * 70)
print()

# Assume Pro plan at £5/month
pro_plan_price_gbp = 5.00
target_revenue_gbp = 1500
users_needed = target_revenue_gbp / pro_plan_price_gbp

for scenario_name, avg_claims_per_user in scenarios:
    total_claims = 300 * avg_claims_per_user
    total_checks = total_claims / CLAIMS_PER_CHECK
    monthly_llm_cost = total_checks * total_cost_per_check
    brave_queries = total_checks * 1.5
    brave_cost = 0 if brave_queries <= 2500 else 5
    total_monthly_cost_usd = monthly_llm_cost + brave_cost

    # Convert to GBP (rough estimate 1 USD = 0.80 GBP)
    total_monthly_cost_gbp = total_monthly_cost_usd * 0.80

    # Revenue calculation
    monthly_revenue_gbp = 300 * pro_plan_price_gbp
    profit_gbp = monthly_revenue_gbp - total_monthly_cost_gbp
    profit_margin = (profit_gbp / monthly_revenue_gbp) * 100

    print(f"{scenario_name} ({avg_claims_per_user} claims/user/month):")
    print(f"  Monthly revenue (300 users @ £{pro_plan_price_gbp}): £{monthly_revenue_gbp:>7.2f}")
    print(f"  Monthly costs:                       £{total_monthly_cost_gbp:>7.2f}")
    print(f"  PROFIT:                              £{profit_gbp:>7.2f}")
    print(f"  Profit margin:                       {profit_margin:>6.1f}%")
    print()

print("=" * 70)
print("KEY INSIGHTS")
print("=" * 70)
print()
print(f"1. Cost per check is VERY LOW: ${total_cost_per_check:.5f}")
print(f"2. GPT-4o-mini is extremely cost-effective for this use case")
print(f"3. Government APIs add ZERO marginal cost (all free)")
print(f"4. Profit margins are excellent (>96% even at high usage)")
print(f"5. 300 users would generate £1,500/month with minimal costs")
print()
print("RECOMMENDATION:")
print("  Current configuration is financially sustainable.")
print("  Focus on user acquisition - costs are negligible.")
print()
