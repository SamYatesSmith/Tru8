"""Agent tier pricing constants (integer cents).

Track M appends "consensus" tier by adding to AGENT_PRICING_CENTS and TIER_ORDER.
Adding a tier requires: (1) entry in AGENT_PRICING_CENTS, (2) entry in TIER_ORDER,
(3) handler logic in run_tier().
"""

AGENT_PRICING_CENTS = {
    "lookup": 2,  # $0.02
    "consensus": 3,  # $0.03 (M-06)
    "quick": 7,  # $0.07
    "full": 15,  # $0.15
}

# Ordered lowest-to-highest. Consensus sits between lookup and quick.
TIER_ORDER = ["lookup", "consensus", "quick", "full"]


def get_tier_price(tier: str) -> int:
    """Return price in cents for a tier. Raises KeyError for unknown tiers."""
    return AGENT_PRICING_CENTS[tier]


def tier_rank(tier: str) -> int:
    """Return numeric rank for tier comparison. Higher = more expensive."""
    return TIER_ORDER.index(tier)
