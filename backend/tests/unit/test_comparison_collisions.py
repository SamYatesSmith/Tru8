"""COMPARE: collisions are a pure function of the LIVE claim map.

These tests are the guard on the design rule that matters most here
(design §7.4 / §10.2): the model writes prose, the CODE computes structure —
and structure is computed on READ, never stored, so a re-search that re-maps
evidence can never leave a comparison contradicting the claim map beside it.
If someone persists collisions "for performance", the staleness test at the
bottom is the one that should stop them.
"""

from app.services.comparison import compute_collisions, sorted_pair


def _claim_map(elements):
    return {"elements": elements}


def _element(eid, refs):
    return {
        "element_id": eid,
        "evidence_refs": [{"evidence_id": ev, "relationship": rel} for ev, rel in refs],
    }


class TestComputeCollisions:
    def test_opposed_pair(self):
        cm = _claim_map(
            [_element("e1", [("ev-a", "supports"), ("ev-b", "challenges")])]
        )
        rows = compute_collisions(cm, "ev-a", "ev-b")
        assert rows == [
            {
                "elementId": "e1",
                "a": "supports",
                "b": "challenges",
                "verdict": "opposed",
            }
        ]

    def test_opposed_is_symmetric(self):
        cm = _claim_map(
            [_element("e1", [("ev-a", "challenges"), ("ev-b", "supports")])]
        )
        rows = compute_collisions(cm, "ev-a", "ev-b")
        assert rows[0]["verdict"] == "opposed"

    def test_aligned_identical(self):
        cm = _claim_map([_element("e1", [("ev-a", "supports"), ("ev-b", "supports")])])
        assert compute_collisions(cm, "ev-a", "ev-b")[0]["verdict"] == "aligned"

    def test_context_vs_directional_is_aligned_not_opposed(self):
        # Context vs supports is NOT a collision — 'opposed' is reserved for
        # exactly {supports, challenges}. The printed relationships carry
        # the nuance.
        cm = _claim_map([_element("e1", [("ev-a", "context"), ("ev-b", "supports")])])
        rows = compute_collisions(cm, "ev-a", "ev-b")
        assert rows[0]["verdict"] == "aligned"
        assert rows[0]["a"] == "context"
        assert rows[0]["b"] == "supports"

    def test_only_one_side(self):
        cm = _claim_map(
            [
                _element("e1", [("ev-a", "supports")]),
                _element("e2", [("ev-b", "challenges")]),
            ]
        )
        rows = compute_collisions(cm, "ev-a", "ev-b")
        by_el = {r["elementId"]: r for r in rows}
        assert by_el["e1"]["verdict"] == "only_a"
        assert by_el["e1"]["b"] is None
        assert by_el["e2"]["verdict"] == "only_b"

    def test_element_neither_addresses_yields_no_row(self):
        cm = _claim_map(
            [
                _element("e1", [("ev-a", "supports"), ("ev-b", "supports")]),
                _element("e2", [("ev-other", "supports")]),
            ]
        )
        rows = compute_collisions(cm, "ev-a", "ev-b")
        assert [r["elementId"] for r in rows] == ["e1"]

    def test_opposed_sorts_first(self):
        cm = _claim_map(
            [
                _element("e1", [("ev-a", "supports"), ("ev-b", "supports")]),
                _element("e2", [("ev-a", "supports"), ("ev-b", "challenges")]),
                _element("e3", [("ev-a", "context")]),
            ]
        )
        rows = compute_collisions(cm, "ev-a", "ev-b")
        assert [r["verdict"] for r in rows] == ["opposed", "aligned", "only_a"]

    def test_camel_case_keys_accepted(self):
        # The API serialiser camelCases claim_map in some contexts.
        cm = {
            "elements": [
                {
                    "elementId": "e1",
                    "evidenceRefs": [
                        {"evidenceId": "ev-a", "relationship": "supports"},
                        {"evidenceId": "ev-b", "relationship": "challenges"},
                    ],
                }
            ]
        }
        assert compute_collisions(cm, "ev-a", "ev-b")[0]["verdict"] == "opposed"

    def test_no_claim_map(self):
        assert compute_collisions(None, "ev-a", "ev-b") == []
        assert compute_collisions({}, "ev-a", "ev-b") == []

    def test_staleness_guard_recomputation_reflects_new_map(self):
        """THE reason collisions are never stored: after a re-search re-maps
        the evidence, recomputing against the NEW map gives the new truth
        with no migration and no stale row."""
        old = _claim_map(
            [_element("e1", [("ev-a", "supports"), ("ev-b", "challenges")])]
        )
        new = _claim_map([_element("e1", [("ev-a", "supports"), ("ev-b", "context")])])
        assert compute_collisions(old, "ev-a", "ev-b")[0]["verdict"] == "opposed"
        assert compute_collisions(new, "ev-a", "ev-b")[0]["verdict"] == "aligned"


class TestSortedPair:
    def test_order_independence(self):
        assert sorted_pair("ev-b", "ev-a") == ("ev-a", "ev-b")
        assert sorted_pair("ev-a", "ev-b") == ("ev-a", "ev-b")
