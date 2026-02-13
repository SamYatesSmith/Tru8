"""Request-scoped configuration for frozen evidence replay.

Uses contextvars for async/concurrency safety. Set by runner.py,
read by claim_map_analyzer.py and relevance_scorer.py.
"""

import contextvars

# When set (not None), overrides LLM temperature for deterministic replay.
frozen_replay_temperature = contextvars.ContextVar(
    "frozen_replay_temperature", default=None
)

# When True, V2 frozen evidence replay is active — skip LLM scoring/reassignment
# to keep evidence in its original claim buckets for full determinism.
frozen_evidence_replay = contextvars.ContextVar("frozen_evidence_replay", default=False)
