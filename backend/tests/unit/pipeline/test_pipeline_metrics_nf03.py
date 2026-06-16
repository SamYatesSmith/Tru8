"""NF-03 regression: api_adapter_calls counts adapters that returned >=1 result.

The aggregated per-adapter detail lives in final_result["api_stats"]["apis_queried"]
(a list of {name, results}). The old counter iterated api_stats.items() — the
top-level keys (apis_queried is a list, total_api_calls/total_api_results are
ints) — none of which are {results_returned: N} dicts, so it always read 0.
Pinned against the deterministic cassette bench, where TRU-B4A3 yields GOV.UK 15 /
Hansard 4 / Marketaux 3 (3 adapters with results) and TRU-82CF yields GovInfo 0.
"""

from app.pipeline.runner import DEFAULT_CONFIG, extract_pipeline_metrics


def _result(apis_queried):
    return {"claims": [], "api_stats": {"apis_queried": apis_queried}}


def test_counts_adapters_with_results():
    result = _result(
        [
            {"name": "GOV.UK Content API", "results": 15},
            {"name": "UK Parliament Hansard", "results": 4},
            {"name": "Marketaux", "results": 3},
            {"name": "ONS Economic Statistics", "results": 0},  # queried, no results
            {"name": "Companies House", "results": 0},
        ]
    )
    assert extract_pipeline_metrics(result, DEFAULT_CONFIG).api_adapter_calls == 3


def test_zero_when_all_adapters_empty():
    result = _result([{"name": "GovInfo.gov", "results": 0}])
    assert extract_pipeline_metrics(result, DEFAULT_CONFIG).api_adapter_calls == 0


def test_zero_when_no_adapters_queried():
    result = _result([])
    assert extract_pipeline_metrics(result, DEFAULT_CONFIG).api_adapter_calls == 0


def test_handles_missing_api_stats():
    result = {"claims": []}  # no api_stats key at all
    assert extract_pipeline_metrics(result, DEFAULT_CONFIG).api_adapter_calls == 0
