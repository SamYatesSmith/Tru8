"""Replay bench — frozen-corpus regression check for pipeline changes.

Entry point: backend/scripts/replay_bench.py (CLI wrapper).
This package holds the implementation modules, kept small and obvious.

Module layout:
- fixtures   restore domain_status.json + reset tracker singleton
- capture    in-memory log handler that parses structured pipeline signals
- runner     invokes pipeline as library, returns observation
- comparator hard invariants / tolerant counters / set Jaccard
- golden_io  read/write golden.json files
- reporter   human-readable diff report
"""
