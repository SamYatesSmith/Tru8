"""B3: post-mapping receipt annotation tests.

Pre-B3 every surviving evidence item was marked receipt_status='shown'
in runner.py:2082-2084 — including items the mapper didn't select for
any element. The Librarian's "What we didn't include" disclosure
couldn't surface them because they looked identical to truly shown
items. _apply_post_mapping_receipts splits them: mapped items →
'shown'; unmapped survivors → 'unmapped' + exclusion_reason
'not_selected_by_mapper'.
"""

from app.pipeline.runner import _apply_post_mapping_receipts


class TestApplyPostMappingReceipts:
    def test_three_of_five_evidence_items_mapped(self):
        """Canonical case: 5 classified items, mapper selected 3 across
        2 elements. The other 2 must be tagged 'unmapped' with a
        exclusion_reason so the Librarian can surface them."""
        claim_map = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {"evidence_id": "ev-001", "relationship": "supports"},
                        {"evidence_id": "ev-002", "relationship": "challenges"},
                    ],
                },
                {
                    "element_id": "e2",
                    "evidence_refs": [
                        {"evidence_id": "ev-004", "relationship": "supports"},
                    ],
                },
            ],
        }
        evidence = [
            {"evidence_id": "ev-001", "title": "A"},
            {"evidence_id": "ev-002", "title": "B"},
            {"evidence_id": "ev-003", "title": "C"},
            {"evidence_id": "ev-004", "title": "D"},
            {"evidence_id": "ev-005", "title": "E"},
        ]

        counts = _apply_post_mapping_receipts(claim_map, evidence)

        assert counts == {"shown": 3, "unmapped": 2, "excluded": 0}
        assert evidence[0]["receipt_status"] == "shown"
        assert evidence[1]["receipt_status"] == "shown"
        assert evidence[2]["receipt_status"] == "unmapped"
        assert evidence[2]["exclusion_reason"] == "not_selected_by_mapper"
        assert evidence[3]["receipt_status"] == "shown"
        assert evidence[4]["receipt_status"] == "unmapped"
        assert evidence[4]["exclusion_reason"] == "not_selected_by_mapper"

    def test_pre_excluded_items_are_left_alone(self):
        """Items already tagged 'excluded' by an earlier stage (satire,
        irrelevant, quality-floor demotion to excluded) must keep their
        decision and reason. B3 only re-tags items that survived to the
        post-mapping stage."""
        claim_map = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {"evidence_id": "ev-001", "relationship": "supports"},
                    ],
                },
            ],
        }
        evidence = [
            {"evidence_id": "ev-001"},
            {
                "evidence_id": "ev-002",
                "receipt_status": "excluded",
                "exclusion_reason": "satire",
            },
            {
                "evidence_id": "ev-003",
                "receipt_status": "excluded",
                "exclusion_reason": "irrelevant",
            },
        ]

        counts = _apply_post_mapping_receipts(claim_map, evidence)

        assert counts == {"shown": 1, "unmapped": 0, "excluded": 2}
        # Pre-excluded items keep their original reason
        assert evidence[1]["exclusion_reason"] == "satire"
        assert evidence[2]["exclusion_reason"] == "irrelevant"

    def test_no_claim_map_marks_everything_shown(self):
        """No claim_map (pipeline branch where mapping was skipped or
        failed): preserve current behaviour and tag everything 'shown'.
        Worst case is "show too much", never "silently drop"."""
        evidence = [
            {"evidence_id": "ev-001"},
            {"evidence_id": "ev-002"},
        ]

        counts = _apply_post_mapping_receipts(None, evidence)

        assert counts == {"shown": 2, "unmapped": 0, "excluded": 0}
        assert all(ev["receipt_status"] == "shown" for ev in evidence)

    def test_empty_elements_marks_everything_unmapped(self):
        """Empty elements list (mapper produced no element refs at all):
        every classified item is genuinely unmapped, not silently
        shown — this is the exact bug B3 closes."""
        claim_map = {"elements": []}
        evidence = [
            {"evidence_id": "ev-001"},
            {"evidence_id": "ev-002"},
        ]

        counts = _apply_post_mapping_receipts(claim_map, evidence)

        assert counts == {"shown": 0, "unmapped": 2, "excluded": 0}
        assert all(ev["receipt_status"] == "unmapped" for ev in evidence)
        assert all(
            ev["exclusion_reason"] == "not_selected_by_mapper" for ev in evidence
        )

    def test_evidence_id_fallback_to_id_field(self):
        """Defensive: some upstream code paths use 'id' instead of
        'evidence_id'. Helper checks both — items with 'id' matching a
        mapped ref should be tagged 'shown', not 'unmapped'."""
        claim_map = {
            "elements": [
                {
                    "element_id": "e1",
                    "evidence_refs": [
                        {"evidence_id": "alt-id-1"},
                    ],
                },
            ],
        }
        evidence = [
            {"id": "alt-id-1", "title": "uses id, not evidence_id"},
        ]

        counts = _apply_post_mapping_receipts(claim_map, evidence)

        assert counts == {"shown": 1, "unmapped": 0, "excluded": 0}
        assert evidence[0]["receipt_status"] == "shown"

    def test_evidence_without_id_marks_shown(self):
        """Defensive: items lacking both 'evidence_id' and 'id' fields
        can't be matched against the claim_map. Mark 'shown' rather
        than 'unmapped' so the worst-case bug is over-disclosure
        rather than silent drop."""
        evidence = [{"title": "no id at all"}]

        counts = _apply_post_mapping_receipts({"elements": []}, evidence)

        assert counts == {"shown": 1, "unmapped": 0, "excluded": 0}
        assert evidence[0]["receipt_status"] == "shown"

    def test_malformed_claim_map_handled_defensively(self):
        """Defensive: malformed claim_map (elements that aren't dicts,
        evidence_refs that aren't dicts) must not crash. Elements
        skipped, items default to 'unmapped' since none can be matched."""
        claim_map = {
            "elements": [
                "not a dict",
                {"element_id": "e1", "evidence_refs": ["also not a dict"]},
                {"element_id": "e2", "evidence_refs": [{"evidence_id": "ev-001"}]},
            ],
        }
        evidence = [
            {"evidence_id": "ev-001"},
            {"evidence_id": "ev-002"},
        ]

        counts = _apply_post_mapping_receipts(claim_map, evidence)

        assert counts == {"shown": 1, "unmapped": 1, "excluded": 0}
        assert evidence[0]["receipt_status"] == "shown"
        assert evidence[1]["receipt_status"] == "unmapped"
