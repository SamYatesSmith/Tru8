"""Invented precision (2026-09-09): an element must not be stricter than the claim."""

import pytest

from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
from app.utils.invented_precision import strip_invented_precision

CLAIM = "Taking 5g of creatine daily prevents dementia in healthy adults."


@pytest.mark.parametrize(
    "desc,expected,removed",
    [
        (
            "The intervention involves taking a daily dose of exactly 5g of creatine.",
            "The intervention involves taking a daily dose of 5g of creatine.",
            ["exactly"],
        ),
        (
            "The target population consists strictly of healthy adults who do not have dementia.",
            "The target population consists of healthy adults who do not have dementia.",
            ["strictly"],
        ),
        (
            "Exactly 5g of creatine is taken daily.",
            "5g of creatine is taken daily.",
            ["exactly"],
        ),
        ("The dose is 5g of creatine daily.", "The dose is 5g of creatine daily.", []),
    ],
)
def test_adverbs_the_claim_does_not_carry_are_removed(desc, expected, removed):
    assert strip_invented_precision(desc, CLAIM) == (expected, removed)


def test_an_adverb_the_claim_itself_uses_is_kept():
    claim = "The trial enrolled only adults with established cardiovascular disease."
    desc = "The trial enrolled only adults with established cardiovascular disease, not the general population."
    assert strip_invented_precision(desc, claim) == (desc, [])
    # "purely" absent from the claim still goes
    assert strip_invented_precision("The effect is purely mechanical.", claim)[1] == [
        "purely"
    ]


def test_figures_are_never_touched():
    desc = "Sweden did not impose a general lockdown during the 2020-2022 period."
    assert strip_invented_precision(
        desc, "Sweden's no-lockdown policy in 2020-22 …"
    ) == (desc, [])


def test_parser_strips_and_records_when_given_the_claim():
    a = ClaimMapAnalyzer()
    a._last_model_used = "test"  # set by _call_llm on the real path
    raw = {
        "normalised_claim": CLAIM,
        "claim_type": "empirical",
        "elements": [
            {
                "description": "The intervention involves taking a daily dose of exactly 5g of creatine."
            },
            {
                "description": "Daily creatine prevents the onset of dementia in healthy adults."
            },
        ],
    }
    cm = a._parse_decomposition_response(raw, "c", claim_text=CLAIM)
    assert (
        cm["elements"][0]["description"]
        == "The intervention involves taking a daily dose of 5g of creatine."
    )
    assert cm["metadata"]["precision_stripped"] == [
        {
            "element_id": "e1",
            "removed": ["exactly"],
            "was": "The intervention involves taking a daily dose of exactly 5g of creatine.",
        }
    ]
    # Without the claim text (legacy callers) nothing changes and no key appears.
    cm2 = a._parse_decomposition_response(raw, "c")
    assert "exactly" in cm2["elements"][0]["description"]
    assert "precision_stripped" not in cm2["metadata"]
