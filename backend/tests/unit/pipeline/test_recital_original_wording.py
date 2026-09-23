"""The recital gate matches the claim's OWN wording, not only the normalised one
(2026-09-23, Kennedy 977b36b7).

Decomposition rewrites the claim into `normalised_claim`. The restatement check
compared sources against that rewrite only, so the author's own newsletter —
restating the submitted sentence word for word — fell below the match threshold
once "pretty much the lowest on record" became "representing the lowest level on
record". It then supported all three elements, and on the 83% norm its weight was
what crossed the support floor. A claim's own source is evidence the claim was
made, never that it is true.
"""

from app.pipeline.claim_map_analyzer import ClaimMapAnalyzer
from app.pipeline.runner import attach_claim_text

SUBMITTED = (
    "As of 11 September 2026, EU-wide gas storage stocks are 67% full against a "
    "seasonal norm of 83%, pretty much the lowest on record for this time of year."
)
NORMALISED = (
    "As of 11 September 2026, EU-wide gas storage stocks are 67% full against a "
    "seasonal norm of 83%, representing the lowest level on record for this time "
    "of year."
)
EVIDENCE = [
    {
        "evidence_id": "ev-energyflux",
        "url": "https://www.energyflux.news/europes-gold-plated-energy-crisis/",
        "title": "Europe’s gold-plated energy crisis",
        "snippet": "EU-wide stocks are 67% full against a seasonal norm of 83%, pretty "
        "much the lowest on record for this time of year.",
        "tier": "commentary",
    },
    {
        "evidence_id": "ev-briefs",
        "url": "https://www.briefs.co/news/mild-weather-could-ease-europe-s-gas-crunch/",
        "title": "Mild Winter Forecasts May Ease Europe's Gas Crunch",
        "snippet": "As a result, Europe's storage sits at 67% compared with a typical "
        "seasonal level of 83%.",
        "tier": "reporting",
    },
]


def _parse(metadata):
    cm = {
        "claim_id": "0",
        "normalised_claim": NORMALISED,
        "elements": [
            {
                "element_id": "e1",
                "description": "The seasonal norm for EU-wide gas storage stocks as "
                "of 11 September 2026 is 83% full.",
                "evidence_refs": [],
                "state": None,
            }
        ],
        "metadata": metadata,
    }
    ClaimMapAnalyzer()._parse_mapping_response(
        {
            "elements": [
                {
                    "element_id": "e1",
                    "state": "supported",
                    "evidence_refs": [
                        {
                            "evidence_id": "ev-energyflux",
                            "relationship": "supports",
                            "reasoning": "This commentary directly confirms the "
                            "seasonal norm of 83%.",
                        },
                        {
                            "evidence_id": "ev-briefs",
                            "relationship": "supports",
                            "reasoning": "Identifies the typical seasonal level as 83%.",
                        },
                    ],
                }
            ]
        },
        cm,
        EVIDENCE,
    )
    elem = cm["elements"][0]
    return {
        r["evidence_id"]: getattr(r["relationship"], "value", r["relationship"])
        for r in elem["evidence_refs"]
    }, elem


def test_the_claims_own_source_is_context_when_its_wording_is_carried():
    rels, elem = _parse({"claim_text": SUBMITTED})
    assert rels["ev-energyflux"] == "context"
    assert rels["ev-briefs"] == "supports"  # an independent statement stays
    assert elem["basis"]["recital_scope"]["scoped"][0]["evidence_id"] == "ev-energyflux"


def test_it_was_missed_against_the_normalised_wording_alone():
    """Guards the guard: without the carried wording this is the production miss."""
    rels, _ = _parse({})
    assert rels["ev-energyflux"] == "supports"


def test_runner_carries_the_claim_text_onto_the_claim_map():
    claim_map = {"metadata": {"subjects": []}}
    assert attach_claim_text({"text": SUBMITTED}, claim_map) == SUBMITTED
    assert claim_map["metadata"] == {"subjects": [], "claim_text": SUBMITTED}


def test_the_pipeline_calls_the_writer_beside_the_other_attachers():
    """A reader whose key nobody writes is how retrieve.py failed for months.
    The helper above is only useful if the mapping scaffold loop calls it."""
    import inspect

    import app.pipeline.runner as runner

    src = inspect.getsource(runner)
    assert "attach_claim_subjects(claim, scaffold)\n            attach_claim_text(claim, scaffold)" in src
