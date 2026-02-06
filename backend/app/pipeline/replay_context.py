"""Request-scoped configuration for frozen evidence replay.

Uses contextvars for async/concurrency safety. Set by runner.py,
read by judge.py and relevance_scorer.py.
"""
import contextvars

# When set (not None), overrides LLM temperature for deterministic replay.
frozen_replay_temperature = contextvars.ContextVar(
    'frozen_replay_temperature', default=None
)
