"""Unit tests for adapter_query_helpers — extract_topic_phrase,
extract_entity_name, extract_location_and_date, extract_concept_keyword."""

from app.utils.adapter_query_helpers import (
    extract_concept_keyword,
    extract_entity_name,
    extract_location_and_date,
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


# ---------- extract_location_and_date ----------


class TestExtractLocationAndDate:
    def test_returns_both_when_present(self):
        entities = [
            {"text": "London", "label": "LOCATION"},
            {"text": "July 2022", "label": "DATE"},
        ]
        assert extract_location_and_date(entities) == ("London", "July 2022")

    def test_returns_none_for_missing_location(self):
        entities = [{"text": "2022", "label": "DATE"}]
        assert extract_location_and_date(entities) == (None, "2022")

    def test_returns_none_for_missing_date(self):
        entities = [{"text": "Greenland", "label": "LOCATION"}]
        assert extract_location_and_date(entities) == ("Greenland", None)

    def test_returns_none_none_when_neither_present(self):
        entities = [
            {"text": "BP plc", "label": "ORG"},
            {"text": "Energy Act 2008", "label": "LAW"},
        ]
        assert extract_location_and_date(entities) == (None, None)

    def test_longest_wins_within_label(self):
        entities = [
            {"text": "London", "label": "LOCATION"},
            {"text": "Greater London", "label": "LOCATION"},
            {"text": "2022", "label": "DATE"},
            {"text": "July 2022", "label": "DATE"},
        ]
        assert extract_location_and_date(entities) == ("Greater London", "July 2022")

    def test_handles_empty_entities(self):
        assert extract_location_and_date([]) == (None, None)

    def test_handles_none_entities(self):
        assert extract_location_and_date(None) == (None, None)

    def test_skips_non_dict_entries(self):
        entities = [
            "stray string",  # not a dict
            None,
            {"text": "Berlin", "label": "LOCATION"},
        ]
        assert extract_location_and_date(entities) == ("Berlin", None)

    def test_skips_blank_text(self):
        entities = [
            {"text": "   ", "label": "LOCATION"},
            {"text": "Paris", "label": "LOCATION"},
        ]
        assert extract_location_and_date(entities) == ("Paris", None)

    def test_ignores_irrelevant_labels(self):
        # GPE is the legacy label (heuristic labeller). Post-NF-15 the LLM
        # only emits LOCATION; GPE-labelled entities should not be picked up.
        entities = [
            {"text": "USA", "label": "GPE"},
            {"text": "Tokyo", "label": "LOCATION"},
        ]
        assert extract_location_and_date(entities) == ("Tokyo", None)


# ---------- extract_concept_keyword ----------


_FRED_LIKE_MAPPING = {
    "unemployment rate": "UNRATE",
    "inflation": "CPIAUCSL",
    "GDP growth": "A191RL1Q225SBEA",  # specific
    "GDP": "GDP",  # broader; deliberately listed AFTER "GDP growth"
}


class TestExtractConceptKeyword:
    def test_matches_typed_other_entity(self):
        entities = [{"text": "unemployment rate", "label": "OTHER"}]
        result = extract_concept_keyword(
            "Unemployment in the US is rising", _FRED_LIKE_MAPPING, entities
        )
        assert result == "UNRATE"

    def test_matches_in_claim_text_fallback(self):
        # No matching OTHER entity, but the claim mentions the concept.
        entities = [{"text": "Federal Reserve", "label": "ORG"}]
        result = extract_concept_keyword(
            "US inflation hit 3% in 2024", _FRED_LIKE_MAPPING, entities
        )
        assert result == "CPIAUCSL"

    def test_returns_none_when_no_match(self):
        result = extract_concept_keyword(
            "BP profits hit record levels", _FRED_LIKE_MAPPING, []
        )
        assert result is None

    def test_typed_entity_wins_over_claim_text(self):
        # Claim text mentions "inflation" but the OTHER entity says "GDP".
        # Pass 1 (entity) should win — the LLM is the more specific signal.
        entities = [{"text": "GDP growth", "label": "OTHER"}]
        result = extract_concept_keyword(
            "Inflation matters for monetary policy", _FRED_LIKE_MAPPING, entities
        )
        assert result == "A191RL1Q225SBEA"

    def test_more_specific_keyword_wins_via_dict_order(self):
        # Mapping order: "GDP growth" before "GDP". Claim mentions the
        # specific phrase. The longer/more-specific code should be returned.
        result = extract_concept_keyword(
            "UK GDP growth slowed in Q2", _FRED_LIKE_MAPPING, []
        )
        assert result == "A191RL1Q225SBEA"

    def test_short_keyword_matches_when_specific_absent(self):
        result = extract_concept_keyword(
            "GDP figures released today", _FRED_LIKE_MAPPING, []
        )
        assert result == "GDP"

    def test_case_insensitive_match(self):
        entities = [{"text": "INFLATION", "label": "OTHER"}]
        result = extract_concept_keyword("Anything", _FRED_LIKE_MAPPING, entities)
        assert result == "CPIAUCSL"

    def test_handles_none_entities(self):
        result = extract_concept_keyword(
            "GDP figures released", _FRED_LIKE_MAPPING, None
        )
        assert result == "GDP"

    def test_handles_empty_mapping(self):
        result = extract_concept_keyword("Anything", {}, None)
        assert result is None

    def test_skips_non_other_entities(self):
        # ORG-labelled entity should not match concept keywords even if
        # the entity text happens to contain a mapping key.
        entities = [{"text": "Inflation Reduction Bureau", "label": "ORG"}]
        result = extract_concept_keyword(
            "The Bureau filed a report", _FRED_LIKE_MAPPING, entities
        )
        assert result is None  # claim text doesn't match either

    def test_skips_blank_entity_text(self):
        entities = [
            {"text": "   ", "label": "OTHER"},
            {"text": "inflation", "label": "OTHER"},
        ]
        result = extract_concept_keyword("Anything", _FRED_LIKE_MAPPING, entities)
        assert result == "CPIAUCSL"
