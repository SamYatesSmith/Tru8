"""Unit tests for adapter_query_helpers — extract_topic_phrase, extract_entity_name."""

from app.utils.adapter_query_helpers import (
    extract_entity_name,
    extract_topic_phrase,
)


CLAIM = "The Climate Change Act 2008 set the UK's target of net zero emissions by 2050"


# ---------- extract_topic_phrase ----------


class TestExtractTopicPhrase:
    def test_returns_law_entity_when_present(self):
        entities = [
            {"text": "Climate Change Act 2008", "label": "LAW"},
            {"text": "UK", "label": "GPE"},
            {"text": "2050", "label": "DATE"},
        ]
        assert extract_topic_phrase(CLAIM, entities) == "Climate Change Act 2008"

    def test_law_outranks_org(self):
        entities = [
            {"text": "BP", "label": "ORG"},
            {"text": "Energy Act 2013", "label": "LAW"},
        ]
        assert extract_topic_phrase("anything", entities) == "Energy Act 2013"

    def test_event_outranks_org(self):
        entities = [
            {"text": "BBC", "label": "ORG"},
            {"text": "World Cup 2022", "label": "EVENT"},
        ]
        assert extract_topic_phrase("anything", entities) == "World Cup 2022"

    def test_longest_text_wins_within_same_label(self):
        entities = [
            {"text": "FCA", "label": "ORG"},
            {"text": "Financial Conduct Authority", "label": "ORG"},
        ]
        assert (
            extract_topic_phrase("anything", entities) == "Financial Conduct Authority"
        )

    def test_falls_back_to_claim_when_no_priority_label(self):
        entities = [
            {"text": "London", "label": "GPE"},
            {"text": "Boris Johnson", "label": "PERSON"},
            {"text": "2024", "label": "DATE"},
        ]
        assert extract_topic_phrase(CLAIM, entities) == CLAIM

    def test_falls_back_to_claim_when_entities_empty(self):
        assert extract_topic_phrase(CLAIM, []) == CLAIM

    def test_falls_back_to_claim_when_entities_none(self):
        assert extract_topic_phrase(CLAIM, None) == CLAIM

    def test_ignores_blank_text(self):
        entities = [
            {"text": "  ", "label": "LAW"},
            {"text": "Energy Act 2013", "label": "LAW"},
        ]
        assert extract_topic_phrase("anything", entities) == "Energy Act 2013"

    def test_ignores_entities_without_label(self):
        entities = [
            {"text": "Some Phrase"},  # no label
            {"text": "Climate Change Act 2008", "label": "LAW"},
        ]
        assert extract_topic_phrase("anything", entities) == "Climate Change Act 2008"

    def test_strips_whitespace_from_returned_text(self):
        entities = [{"text": "  Climate Change Act 2008  ", "label": "LAW"}]
        assert extract_topic_phrase("anything", entities) == "Climate Change Act 2008"


# ---------- extract_entity_name ----------


class TestExtractEntityName:
    def test_returns_org_when_present(self):
        entities = [
            {"text": "BP", "label": "ORG"},
            {"text": "London", "label": "GPE"},
        ]
        assert extract_entity_name("anything", entities, label="ORG") == "BP"

    def test_returns_none_when_label_missing(self):
        entities = [
            {"text": "London", "label": "GPE"},
            {"text": "Boris Johnson", "label": "PERSON"},
        ]
        assert extract_entity_name("anything", entities, label="ORG") is None

    def test_returns_longest_org_when_multiple(self):
        entities = [
            {"text": "BP", "label": "ORG"},
            {"text": "British Petroleum PLC", "label": "ORG"},
        ]
        assert (
            extract_entity_name("anything", entities, label="ORG")
            == "British Petroleum PLC"
        )

    def test_returns_none_when_entities_empty(self):
        assert extract_entity_name(CLAIM, [], label="ORG") is None

    def test_returns_none_when_entities_none(self):
        assert extract_entity_name(CLAIM, None, label="ORG") is None

    def test_label_parameter_filters_correctly(self):
        entities = [
            {"text": "BP", "label": "ORG"},
            {"text": "Lionel Messi", "label": "PERSON"},
        ]
        assert (
            extract_entity_name("anything", entities, label="PERSON") == "Lionel Messi"
        )
        assert extract_entity_name("anything", entities, label="ORG") == "BP"

    def test_skips_blank_text(self):
        entities = [
            {"text": "  ", "label": "ORG"},
            {"text": "BP", "label": "ORG"},
        ]
        assert extract_entity_name("anything", entities, label="ORG") == "BP"
