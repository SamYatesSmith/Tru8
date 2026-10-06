"""A− #7 / #8 (2026-10-06): the mapping and completion prompts carry today's
date, in the sentence the replay bench normalises; both decomposition prompts
keep a shared total whole."""

import inspect
import re

import pytest

from app.pipeline import claim_map_analyzer as cma
from scripts.replay_bench import cassette


@pytest.mark.unit
def test_date_context_is_normalised_by_the_bench():
    text = cma._date_context()
    assert re.search(r"Today's date is \d{4}-\d{2}-\d{2} \(Year: \d{4}\)\.", text)
    assert any(p.search(text) for p, _ in cassette._DATE_BOILERPLATE_PATTERNS)


@pytest.mark.unit
def test_every_mapping_and_completion_prompt_carries_the_date():
    src = inspect.getsource(cma)
    assert src.count("_date_context()") == 5  # the def + four call sites
    for marker in (
        'f"{MAPPING_PROMPT}"',
        "BATCH_MAPPING_PROMPT +",
        'f"{COMPLETION_PROMPT}',
    ):
        for m in re.finditer(re.escape(marker), src):
            window = src[max(0, m.start() - 120) : m.end()]
            assert "_date_context()" in window, marker


@pytest.mark.unit
def test_both_decomposition_prompts_keep_a_shared_total_whole():
    for prompt in (cma.DECOMPOSITION_PROMPT, cma.BATCH_DECOMPOSITION_PROMPT):
        assert "KEEP A SHARED TOTAL WHOLE" in prompt
