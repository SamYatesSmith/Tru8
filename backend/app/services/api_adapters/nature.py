"""
Nature and Biodiversity API Adapters

Adapters for biodiversity and species data:
- GBIF (Global Biodiversity Information Facility)
"""

import logging
from typing import List, Dict, Any, Optional

from app.services.government_api_client import GovernmentAPIClient

logger = logging.getLogger(__name__)


# ========== GBIF ADAPTER (Global Biodiversity Information Facility) ==========


class GBIFAdapter(GovernmentAPIClient):
    """
    GBIF (Global Biodiversity Information Facility) API Adapter.

    Covers: Animals (species occurrence, taxonomy, biodiversity)
    Jurisdiction: Global
    Free tier: No API key required, rate limit ~10 requests/second
    API key: Not required

    Features:
    - Species occurrence records (observations, specimens)
    - Species taxonomy and classification
    - Biodiversity data from museums, research institutions worldwide
    """

    def __init__(self):
        super().__init__(
            api_name="GBIF",
            base_url="https://api.gbif.org/v1",
            api_key=None,  # No API key required
            cache_ttl=86400 * 7,  # 7 days (species data is stable)
            timeout=15,
            max_results=10,
            emits_structural_metadata=True,  # NF-07-v2: species records, taxonomic snippets
        )

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """GBIF covers Animals domain globally."""
        return domain == "Animals"

    # SC-06: GBIF's species search expects short common or scientific names
    # (e.g. "right whale", "Eubalaena glacialis"), not full claim sentences.
    # Passing the full claim returned 0 results on every home-turf query
    # in the 2026-04-23 scorecard. These boundary words terminate the
    # "species-name prefix" of a typical claim so we can feed a clean
    # species phrase into the API.
    _SPECIES_QUERY_STOPWORDS = frozenset({"the", "a", "an"})
    _SPECIES_QUERY_BOUNDARY_WORDS = frozenset(
        {
            # Copula / auxiliary verbs
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "has",
            "have",
            "had",
            "become",
            "became",
            "becomes",
            # Population/trend verbs
            "fell",
            "rose",
            "declined",
            "grew",
            "dropped",
            "increased",
            "decreased",
            "exceeded",
            "reached",
            # Population nouns
            "population",
            "populations",
            "numbers",
            "count",
            "counts",
            # Biological activity verbs
            "breed",
            "breeds",
            "breeding",
            "bred",
            "feed",
            "feeds",
            "feeding",
            "fed",
            "hunt",
            "hunts",
            "hunting",
            "hunted",
            "live",
            "lives",
            "living",
            "lived",
            "inhabit",
            "inhabits",
            "inhabiting",
            "inhabited",
            "migrate",
            "migrates",
            "migrating",
            "migrated",
            "nest",
            "nests",
            "nesting",
            "nested",
            "graze",
            "grazes",
            "grazing",
            "grazed",
        }
    )
    _SPECIES_QUERY_MAX_TOKENS = 5

    def _extract_species_query(self, query: str) -> str:
        """SC-06: reduce a claim sentence to a likely species name phrase.

        GBIF's /species/search returns 0 on long sentences (verified live
        2026-04-24). This trims leading articles, stops at the first
        copula/population/biological verb, and caps at 5 tokens. Preserves
        multi-word species names like "North Atlantic right whale" while
        dropping population/trend tails like "population fell below 350".
        Returns the original query unchanged if trimming would produce
        an empty string.
        """
        words = query.split()
        while words and words[0].lower() in self._SPECIES_QUERY_STOPWORDS:
            words.pop(0)
        trimmed: List[str] = []
        for w in words:
            if w.lower().rstrip(".,;:!?") in self._SPECIES_QUERY_BOUNDARY_WORDS:
                break
            trimmed.append(w)
            if len(trimmed) >= self._SPECIES_QUERY_MAX_TOKENS:
                break
        return " ".join(trimmed).strip() or query

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search GBIF for species and biodiversity data.

        Args:
            query: Search query (e.g., "African elephant population", "red panda habitat")
            domain: Animals
            jurisdiction: Any (global coverage)
            entities: Optional NER entities

        Returns:
            List of evidence dictionaries
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        query = self._sanitize_query(query)
        evidence = []

        try:
            # SC-06: try a species-name-focused query first, fall back to
            # the full claim if trimming produced no results. The trimmed
            # query is what GBIF's /species/search is actually shaped for.
            species_query = self._extract_species_query(query)
            species_evidence = self._search_species(species_query)
            if not species_evidence and species_query != query:
                species_evidence = self._search_species(query)
            evidence.extend(species_evidence)

            # Search for occurrence data if we have a species name
            if species_evidence:
                species_key = species_evidence[0].get("metadata", {}).get("species_key")
                if species_key:
                    occurrence_evidence = self._get_occurrence_data(species_key)
                    evidence.extend(occurrence_evidence)

            return evidence[: self.max_results]

        except Exception as e:
            logger.error(f"GBIF search failed for '{query}': {e}")
            return []

    def _search_species(self, query: str) -> List[Dict[str, Any]]:
        """Search for species by name."""
        evidence = []

        try:
            import httpx
            from urllib.parse import quote

            # Search species endpoint
            url = f"{self.base_url}/species/search?q={quote(query)}&limit=5"

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url)
                response.raise_for_status()
                data = response.json()

            if not data or "results" not in data:
                return []

            for species in data.get("results", [])[:3]:
                scientific_name = species.get("scientificName", "Unknown species")
                common_name = species.get("vernacularName", "")
                kingdom = species.get("kingdom", "")
                phylum = species.get("phylum", "")
                class_name = species.get("class", "")
                order = species.get("order", "")
                family = species.get("family", "")
                species_key = species.get("key")
                status = species.get("taxonomicStatus", "")

                # Build taxonomy string
                taxonomy_parts = [
                    p for p in [kingdom, phylum, class_name, order, family] if p
                ]
                taxonomy = (
                    " > ".join(taxonomy_parts) if taxonomy_parts else "Unknown taxonomy"
                )

                title = common_name if common_name else scientific_name
                if common_name and scientific_name:
                    title = f"{common_name} ({scientific_name})"

                snippet = f"Scientific classification: {taxonomy}. "
                if status:
                    snippet += f"Taxonomic status: {status}. "
                snippet += f"Data from GBIF - Global Biodiversity Information Facility."

                evidence.append(
                    self._create_evidence_dict(
                        title=f"Species: {title}",
                        snippet=snippet,
                        url=(
                            f"https://www.gbif.org/species/{species_key}"
                            if species_key
                            else "https://www.gbif.org"
                        ),
                        source_date=None,
                        metadata={
                            "api_source": "GBIF",
                            "data_type": "species_taxonomy",
                            "species_key": species_key,
                            "scientific_name": scientific_name,
                            "kingdom": kingdom,
                            "family": family,
                        },
                    )
                )

            return evidence

        except Exception as e:
            logger.warning(f"GBIF species search failed: {e}")
            return []

    def _get_occurrence_data(self, species_key: int) -> List[Dict[str, Any]]:
        """Get occurrence/observation data for a species."""
        evidence = []

        try:
            import httpx

            # Get occurrence count and country distribution
            url = f"{self.base_url}/occurrence/search?speciesKey={species_key}&limit=0&facet=country&facetLimit=10"

            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url)
                response.raise_for_status()
                data = response.json()

            count = data.get("count", 0)
            facets = data.get("facets", [])

            if count == 0:
                return []

            # Parse country distribution
            country_counts = []
            for facet in facets:
                if facet.get("field") == "COUNTRY":
                    for item in facet.get("counts", [])[:5]:
                        country_counts.append(
                            f"{item.get('name', 'Unknown')}: {item.get('count', 0):,}"
                        )

            snippet = f"Total occurrence records: {count:,}. "
            if country_counts:
                snippet += f"Top countries: {', '.join(country_counts)}."

            evidence.append(
                self._create_evidence_dict(
                    title=f"GBIF Occurrence Data ({count:,} records)",
                    snippet=snippet,
                    url=f"https://www.gbif.org/species/{species_key}",
                    source_date=None,
                    metadata={
                        "api_source": "GBIF",
                        "data_type": "occurrence_data",
                        "species_key": species_key,
                        "total_occurrences": count,
                    },
                )
            )

            return evidence

        except Exception as e:
            logger.warning(f"GBIF occurrence search failed: {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform GBIF API response to standardized evidence format."""
        # Handled by specific methods above
        return []
