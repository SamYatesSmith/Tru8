"""The WRITER side of the jurisdiction seam.

`test_jurisdiction_scope_wiring.py` proves the mapper reads
`claim_map["metadata"]["jurisdiction"]` and acts on it. That is worth nothing if
nobody writes the key — which is exactly how the element-retrieval defect survived
for months: `retrieve.py` read `claim["elements"]` while decompose wrote
`claim["claim_map"]["elements"]`, so a documented stage silently never ran.

So this file pins the writer the runner actually calls, and pins the shape both
sides agree on.
"""

from app.pipeline.runner import attach_claim_jurisdiction
from app.utils.jurisdiction_scope import claim_target_country


def test_the_jurisdiction_reaches_the_claim_map():
    claim = {"article_classification": {"jurisdiction": "UK"}}
    claim_map = {"metadata": {}}

    returned = attach_claim_jurisdiction(claim, claim_map)

    assert claim_map["metadata"]["jurisdiction"] == "UK"
    assert returned == "UK"


def test_it_survives_a_claim_map_with_no_metadata_dict():
    """Scaffolds are built in more than one place; do not assume the key exists."""
    claim_map = {}

    attach_claim_jurisdiction(
        {"article_classification": {"jurisdiction": "US"}}, claim_map
    )

    assert claim_map["metadata"]["jurisdiction"] == "US"


def test_an_existing_metadata_dict_is_not_clobbered():
    claim_map = {"metadata": {"element_count": 3}}

    attach_claim_jurisdiction(
        {"article_classification": {"jurisdiction": "UK"}}, claim_map
    )

    assert claim_map["metadata"]["element_count"] == 3
    assert claim_map["metadata"]["jurisdiction"] == "UK"


def test_a_claim_with_no_classification_writes_none_rather_than_crashing():
    """Focused-mode and legacy paths may lack it; the gate must go quiet, not fail."""
    claim_map = {"metadata": {}}

    returned = attach_claim_jurisdiction({}, claim_map)

    assert returned is None
    assert claim_map["metadata"]["jurisdiction"] is None
    # And the value written is one the reader treats as "do not fire".
    assert claim_target_country(claim_map["metadata"]["jurisdiction"]) is None


def test_the_two_sides_agree_on_the_value_vocabulary():
    """The writer emits article_classifier's values; the reader must accept them.

    VALID_JURISDICTIONS is UK/US/EU/Global. UK and US must arm the gate and the
    other two must not — if the classifier ever gains a value, this is where the
    mismatch should surface.
    """
    from app.utils.article_classifier import VALID_JURISDICTIONS

    armed = {j for j in VALID_JURISDICTIONS if claim_target_country(j)}

    assert armed == {"UK", "US"}
