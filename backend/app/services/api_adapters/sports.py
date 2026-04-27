"""
Sports API Adapters for Tru8 Fact-Checking Pipeline.

This module contains adapters for sports-related data sources:
- TransfermarktAdapter: Historical player/club data (transfers, stats, achievements)
- FootballDataAdapter: Real-time football statistics (standings, results, scorers)

These adapters extend GovernmentAPIClient to provide standardized evidence
retrieval for the Sports domain.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.services.government_api_client import GovernmentAPIClient

logger = logging.getLogger(__name__)


class TransfermarktAdapter(GovernmentAPIClient):
    """
    Transfermarkt API Adapter for Historical Sports Data.

    Coverage:
    - Player transfers, career stats, achievements, market values
    - Club profiles and rosters
    - Historical data (complements Football-Data.org's real-time data)

    Domain: Sports
    Jurisdiction: Global
    API: Community-hosted transfermarkt-api (no key required)
    """

    def __init__(self):
        super().__init__(
            api_name="Transfermarkt",
            base_url="https://transfermarkt-api.fly.dev",
            api_key=None,  # No API key required
            cache_ttl=3600,  # 1 hour (historical data stable)
            timeout=15,
            max_results=5,
            emits_structural_metadata=True,  # NF-07-v2: transfer stats, structural
        )
        # NO HARDCODED LISTS - use NER entities passed from pipeline

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Transfermarkt covers Sports domain globally."""
        return domain == "Sports"

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search Transfermarkt for historical football data.

        Uses dynamic entity extraction from NER - NO HARDCODED LISTS!

        Supports:
        - Player transfers (e.g., "Neymar transfer to PSG")
        - Career stats (e.g., "Messi career goals")
        - Achievements (e.g., "Ronaldo Ballon d'Or")
        - Market values (e.g., "Haaland market value")
        - Club info (e.g., "Manchester United squad value")

        Args:
            query: Search query (claim text)
            domain: Sports
            jurisdiction: Any
            entities: NER entities [{"text": "Karim Adeyemi", "label": "PERSON"}, ...]

        Returns:
            List of evidence dictionaries with historical data
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        query_lower = query.lower()
        evidence = []

        try:
            # Detect query type and fetch appropriate data

            # TYPE 1: Transfer history
            if any(
                term in query_lower
                for term in [
                    "transfer",
                    "signed for",
                    "joined",
                    "left",
                    "fee",
                    "moved to",
                    "sold",
                ]
            ):
                player_evidence = self._search_player_with_transfers(
                    query_lower, entities
                )
                if player_evidence:
                    evidence.extend(player_evidence)

            # TYPE 2: Achievements / Trophies
            elif any(
                term in query_lower
                for term in [
                    "won",
                    "winner",
                    "champion",
                    "trophy",
                    "title",
                    "ballon d'or",
                    "golden boot",
                    "best player",
                ]
            ):
                player_evidence = self._search_player_with_achievements(
                    query_lower, entities
                )
                if player_evidence:
                    evidence.extend(player_evidence)

            # TYPE 3: Career stats
            elif any(
                term in query_lower
                for term in [
                    "career",
                    "total goals",
                    "all-time",
                    "scored for",
                    "appearances",
                    "caps",
                    "scored",
                    "goals",
                ]
            ):
                player_evidence = self._search_player_with_stats(query_lower, entities)
                if player_evidence:
                    evidence.extend(player_evidence)

            # TYPE 4: Market value
            elif any(
                term in query_lower
                for term in ["worth", "value", "valued at", "market value", "price"]
            ):
                player_evidence = self._search_player_with_value(query_lower, entities)
                if player_evidence:
                    evidence.extend(player_evidence)

            # TYPE 5: Club info (fallback)
            else:
                club_evidence = self._search_club(query_lower, entities)
                if club_evidence:
                    evidence.extend(club_evidence)

            logger.info(f"Transfermarkt returned {len(evidence)} evidence items")
            return evidence[: self.max_results]

        except Exception as e:
            logger.error(
                f"Transfermarkt search failed for '{query}': {e}", exc_info=True
            )
            return []

    def _extract_person_names(
        self, entities: Optional[List[Dict[str, str]]]
    ) -> List[str]:
        """
        Extract PERSON entity names from NER results.

        Uses dynamic NER entities. Also accepts ENTITY labels as fallback
        if they look like person names (2+ capitalized words).

        Args:
            entities: List of NER entities [{"text": "Karim Adeyemi", "label": "PERSON"}, ...]

        Returns:
            List of person names to search for
        """
        persons = []
        entity_fallbacks = []

        if entities:
            for ent in entities:
                if not isinstance(ent, dict):
                    continue

                text = ent.get("text", "")
                label = ent.get("label", "")

                if label == "PERSON":
                    persons.append(text)
                elif label == "ENTITY":
                    # Fallback: Check if it looks like a person name
                    # (2+ words, all capitalized, no org-like suffixes)
                    words = text.split()
                    org_indicators = (
                        "FC",
                        "United",
                        "City",
                        "Club",
                        "League",
                        "Inc",
                        "Ltd",
                    )
                    if (
                        len(words) >= 2
                        and all(w[0].isupper() for w in words if w)
                        and not any(ind in text for ind in org_indicators)
                    ):
                        entity_fallbacks.append(text)

        # Use PERSON entities first, fall back to ENTITY if none found
        return persons if persons else entity_fallbacks

    def _extract_org_names(self, entities: Optional[List[Dict[str, str]]]) -> List[str]:
        """
        Extract ORG entity names (clubs/teams) from NER results.

        Uses dynamic NER entities. Also accepts ENTITY labels as fallback
        if they look like organization names (contain org-like suffixes).

        Args:
            entities: List of NER entities [{"text": "Arsenal", "label": "ORG"}, ...]

        Returns:
            List of organization/club names to search for
        """
        orgs = []
        entity_fallbacks = []

        # Common sports/org indicators
        org_indicators = (
            "FC",
            "United",
            "City",
            "Rovers",
            "Athletic",
            "Club",
            "Dortmund",
            "Arsenal",
            "Chelsea",
            "Munich",
            "Madrid",
            "Barcelona",
            "Milan",
            "Inter",
            "Juventus",
            "PSG",
            "Bayern",
            "Liverpool",
            "League",
            "Association",
            "Federation",
            "UEFA",
            "FIFA",
        )

        if entities:
            for ent in entities:
                if not isinstance(ent, dict):
                    continue

                text = ent.get("text", "")
                label = ent.get("label", "")

                if label == "ORG":
                    orgs.append(text)
                elif label == "ENTITY":
                    # Fallback: Check if it looks like an organization
                    if any(ind in text for ind in org_indicators):
                        entity_fallbacks.append(text)

        # Use ORG entities first, fall back to ENTITY if none found
        return orgs if orgs else entity_fallbacks

    def _search_player_with_transfers(
        self, query_lower: str, entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Search for player and return transfer history using NER entities."""
        person_names = self._extract_person_names(entities)
        if not person_names:
            logger.debug("Transfermarkt: No PERSON entities found for transfer search")
            return []

        all_evidence = []

        for player_name in person_names:
            try:
                # Search for player using API's own fuzzy matching
                search_response = self._make_request(f"/players/search/{player_name}")
                if not search_response or "results" not in search_response:
                    continue

                results = search_response.get("results", [])
                if not results:
                    continue

                # Get first matching player
                player = results[0]
                player_id = player.get("id")
                player_name_full = player.get("name", player_name)

                # Get transfer history
                transfers_response = self._make_request(
                    f"/players/{player_id}/transfers"
                )
                if not transfers_response or "transfers" not in transfers_response:
                    continue

                transfers = transfers_response.get("transfers", [])

                # Build transfer history evidence
                transfer_text = f"Transfer History for {player_name_full}:\n"
                for t in transfers[:10]:
                    date = t.get("date", "Unknown")
                    from_club = t.get("from", {}).get("clubName", "Unknown")
                    to_club = t.get("to", {}).get("clubName", "Unknown")
                    fee = t.get("fee", "Undisclosed")

                    transfer_text += f"- {date}: {from_club} → {to_club} ({fee})\n"

                all_evidence.append(
                    self._create_evidence_dict(
                        title=f"{player_name_full} - Transfer History",
                        snippet=transfer_text.strip(),
                        url=f"https://www.transfermarkt.com/player/{player_id}",
                        source_date=datetime.now(timezone.utc),
                        metadata={
                            "api_source": "Transfermarkt",
                            "player_id": player_id,
                            "data_type": "transfers",
                            "transfer_count": len(transfers),
                        },
                    )
                )

            except Exception as e:
                logger.error(
                    f"Transfermarkt player transfer search failed for {player_name}: {e}"
                )
                continue

        return all_evidence

    def _search_player_with_achievements(
        self, query_lower: str, entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Search for player and return achievements/trophies using NER entities."""
        person_names = self._extract_person_names(entities)
        if not person_names:
            logger.debug(
                "Transfermarkt: No PERSON entities found for achievements search"
            )
            return []

        all_evidence = []

        for player_name in person_names:
            try:
                # Search for player
                search_response = self._make_request(f"/players/search/{player_name}")
                if not search_response or "results" not in search_response:
                    continue

                results = search_response.get("results", [])
                if not results:
                    continue

                player = results[0]
                player_id = player.get("id")
                player_name_full = player.get("name", player_name)

                # Get achievements
                achievements_response = self._make_request(
                    f"/players/{player_id}/achievements"
                )
                if (
                    not achievements_response
                    or "achievements" not in achievements_response
                ):
                    continue

                achievements = achievements_response.get("achievements", [])

                # Build achievements evidence
                achievements_text = f"Achievements for {player_name_full}:\n"
                for a in achievements[:15]:
                    title = a.get("title", "Unknown")
                    count = a.get("count", 1)

                    if count > 1:
                        achievements_text += f"- {title} ({count}x)\n"
                    else:
                        achievements_text += f"- {title}\n"

                all_evidence.append(
                    self._create_evidence_dict(
                        title=f"{player_name_full} - Career Achievements",
                        snippet=achievements_text.strip(),
                        url=f"https://www.transfermarkt.com/player/{player_id}",
                        source_date=datetime.now(timezone.utc),
                        metadata={
                            "api_source": "Transfermarkt",
                            "player_id": player_id,
                            "data_type": "achievements",
                            "achievement_count": len(achievements),
                        },
                    )
                )

            except Exception as e:
                logger.error(
                    f"Transfermarkt player achievements search failed for {player_name}: {e}"
                )
                continue

        return all_evidence

    def _search_player_with_stats(
        self, query_lower: str, entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Search for player and return career statistics using NER entities."""
        person_names = self._extract_person_names(entities)
        if not person_names:
            logger.debug("Transfermarkt: No PERSON entities found for stats search")
            return []

        all_evidence = []

        for player_name in person_names:
            try:
                # Search for player
                search_response = self._make_request(f"/players/search/{player_name}")
                if not search_response or "results" not in search_response:
                    continue

                results = search_response.get("results", [])
                if not results:
                    continue

                player = results[0]
                player_id = player.get("id")
                player_name_full = player.get("name", player_name)

                # Get stats
                stats_response = self._make_request(f"/players/{player_id}/stats")
                if not stats_response or "stats" not in stats_response:
                    continue

                stats = stats_response.get("stats", [])

                # Build career stats evidence
                stats_text = f"Career Statistics for {player_name_full}:\n"
                total_goals = 0
                total_assists = 0
                total_apps = 0

                for s in stats:
                    competition = s.get("competitionName", "Unknown")
                    goals = s.get("goals", 0) or 0
                    assists = s.get("assists", 0) or 0
                    appearances = s.get("appearances", 0) or 0

                    total_goals += goals
                    total_assists += assists
                    total_apps += appearances

                    if appearances > 0:
                        stats_text += f"- {competition}: {appearances} apps, {goals} goals, {assists} assists\n"

                stats_text += f"\nCareer Totals: {total_apps} appearances, {total_goals} goals, {total_assists} assists"

                all_evidence.append(
                    self._create_evidence_dict(
                        title=f"{player_name_full} - Career Statistics",
                        snippet=stats_text.strip(),
                        url=f"https://www.transfermarkt.com/player/{player_id}",
                        source_date=datetime.now(timezone.utc),
                        metadata={
                            "api_source": "Transfermarkt",
                            "player_id": player_id,
                            "data_type": "career_stats",
                            "total_goals": total_goals,
                            "total_assists": total_assists,
                            "total_appearances": total_apps,
                        },
                    )
                )

            except Exception as e:
                logger.error(
                    f"Transfermarkt player stats search failed for {player_name}: {e}"
                )
                continue

        return all_evidence

    def _search_player_with_value(
        self, query_lower: str, entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Search for player and return market value history using NER entities."""
        person_names = self._extract_person_names(entities)
        if not person_names:
            logger.debug("Transfermarkt: No PERSON entities found for value search")
            return []

        all_evidence = []

        for player_name in person_names:
            try:
                # Search for player
                search_response = self._make_request(f"/players/search/{player_name}")
                if not search_response or "results" not in search_response:
                    continue

                results = search_response.get("results", [])
                if not results:
                    continue

                player = results[0]
                player_id = player.get("id")
                player_name_full = player.get("name", player_name)
                current_value = player.get("marketValue", "Unknown")

                # Get market value history
                value_response = self._make_request(
                    f"/players/{player_id}/market_value"
                )

                value_text = f"Market Value for {player_name_full}:\n"
                value_text += f"Current Value: {current_value}\n"

                if value_response and "marketValueHistory" in value_response:
                    history = value_response.get("marketValueHistory", [])
                    if history:
                        value_text += "\nValue History:\n"
                        for h in history[:5]:  # Last 5 entries
                            date = h.get("date", "Unknown")
                            value = h.get("value", "Unknown")
                            club = h.get("clubName", "Unknown")
                            value_text += f"- {date}: {value} ({club})\n"

                all_evidence.append(
                    self._create_evidence_dict(
                        title=f"{player_name_full} - Market Value",
                        snippet=value_text.strip(),
                        url=f"https://www.transfermarkt.com/player/{player_id}",
                        source_date=datetime.now(timezone.utc),
                        metadata={
                            "api_source": "Transfermarkt",
                            "player_id": player_id,
                            "data_type": "market_value",
                            "current_value": current_value,
                        },
                    )
                )

            except Exception as e:
                logger.error(
                    f"Transfermarkt player value search failed for {player_name}: {e}"
                )
                continue

        return all_evidence

    def _search_club(
        self, query_lower: str, entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Search for club and return profile using NER entities - NO HARDCODED LISTS!"""
        org_names = self._extract_org_names(entities)
        if not org_names:
            logger.debug("Transfermarkt: No ORG entities found for club search")
            return []

        all_evidence = []

        for club_name in org_names:
            try:
                # Search for club using API's own fuzzy matching
                search_response = self._make_request(f"/clubs/search/{club_name}")
                if not search_response or "results" not in search_response:
                    continue

                results = search_response.get("results", [])
                if not results:
                    continue

                club = results[0]
                club_id = club.get("id")
                club_name_full = club.get("name", club_name)
                market_value = club.get("marketValue", "Unknown")
                squad_size = club.get("squadSize", "Unknown")

                club_text = f"{club_name_full}\n"
                club_text += f"Squad Size: {squad_size} players\n"
                club_text += f"Total Market Value: {market_value}\n"

                all_evidence.append(
                    self._create_evidence_dict(
                        title=f"{club_name_full} - Club Profile",
                        snippet=club_text.strip(),
                        url=f"https://www.transfermarkt.com/club/{club_id}",
                        source_date=datetime.now(timezone.utc),
                        metadata={
                            "api_source": "Transfermarkt",
                            "club_id": club_id,
                            "data_type": "club_profile",
                            "market_value": market_value,
                        },
                    )
                )

            except Exception as e:
                logger.error(f"Transfermarkt club search failed for {club_name}: {e}")
                continue

        return all_evidence

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform Transfermarkt API response to standardized evidence format."""
        # Handled by specific methods above
        return []


class FootballDataAdapter(GovernmentAPIClient):
    """
    Football-Data.org API Adapter for Sports Statistics.

    Coverage:
    - Premier League, La Liga, Serie A, Bundesliga, Ligue 1
    - Current standings, match results, team info
    - Player statistics (limited on free tier)

    Domain: Sports
    Jurisdiction: Global (European football)
    API: Football-Data.org (requires API key, free tier: 10 calls/min)
    """

    def __init__(self):
        # Use settings instead of os.getenv - .env loaded by pydantic-settings
        api_key = settings.FOOTBALL_DATA_API_KEY

        super().__init__(
            api_name="Football-Data.org",
            base_url="https://api.football-data.org/v4",
            api_key=api_key,
            cache_ttl=300,  # 5 minutes - sports data changes frequently
            timeout=10,
            max_results=10,
            emits_structural_metadata=True,  # NF-07-v2: match stats, structural
        )

        # Football-Data.org uses X-Auth-Token header
        if self.api_key:
            del self.headers["Authorization"]
            self.headers["X-Auth-Token"] = self.api_key

        # Competition codes for major leagues (free tier)
        # NOTE: These are official API identifiers, NOT entity matching (OK to keep)
        self.competitions = {
            # Top 5 European leagues
            "PL": "Premier League",
            "PD": "La Liga",
            "BL1": "Bundesliga",
            "SA": "Serie A",
            "FL1": "Ligue 1",
            # European competitions
            "CL": "Champions League",
            "EC": "European Championship",
            # Additional competitions
            "WC": "FIFA World Cup",
            "ELC": "EFL Championship",
            "DED": "Eredivisie",
            "PPL": "Primeira Liga",
            "BSA": "Campeonato Brasileiro Série A",
        }
        # NO HARDCODED team_aliases - use NER entities passed from pipeline

    def is_relevant_for_domain(self, domain: str, jurisdiction: str) -> bool:
        """Football-Data covers Sports domain globally."""
        return domain == "Sports"

    def search(
        self,
        query: str,
        domain: str,
        jurisdiction: str,
        entities: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search Football-Data.org for sports statistics.

        Uses dynamic entity extraction from NER - NO HARDCODED LISTS!

        Supports:
        - League standings (e.g., "Premier League standings")
        - Team info (e.g., "Arsenal squad")
        - Match results (e.g., "Arsenal vs Chelsea")

        Args:
            query: Search query (claim text)
            domain: Sports
            jurisdiction: Any
            entities: NER entities [{"text": "Arsenal", "label": "ORG"}, ...]

        Returns:
            List of evidence dictionaries with sports data
        """
        if not self.is_relevant_for_domain(domain, jurisdiction):
            return []

        if not self.api_key:
            logger.warning("Football-Data.org API key not configured, skipping")
            return []

        query_lower = query.lower()
        evidence = []

        try:
            # Detect query type and fetch appropriate data

            # TYPE 1: League standings (most common for fact-checking)
            if any(
                term in query_lower
                for term in [
                    "top",
                    "standing",
                    "table",
                    "points",
                    "lead",
                    "ahead",
                    "behind",
                    "position",
                ]
            ):
                evidence.extend(self._get_standings(query_lower, entities))

            # TYPE 2: Team info / squad / transfers
            # Extended with transfer-intent keywords to detect when claim is about player movements
            # Note: Football-Data.org has limited transfer data, but team info may help
            transfer_keywords = [
                "squad",
                "player",
                "signed",
                "transferred",
                "manager",
                "coach",
                # Transfer-intent keywords (helps detect transfer claims)
                "transfer",
                "offload",
                "offloading",
                "exit",
                "departure",
                "departing",
                "deal",
                "move",
                "moving",
                "loan",
                "loaned",
                "loaning",
                "linked",
                "link",
                "target",
                "targeting",
                "interest",
                "interested",
                "bid",
                "offer",
                "fee",
                "sell",
                "selling",
                "buy",
                "buying",
            ]
            if any(term in query_lower for term in transfer_keywords):
                evidence.extend(self._get_team_info(query_lower, entities))

            # TYPE 3: Match results
            if any(
                term in query_lower
                for term in [
                    "beat",
                    "won",
                    "lost",
                    "draw",
                    "match",
                    "game",
                    "vs",
                    "versus",
                ]
            ):
                evidence.extend(self._get_match_results(query_lower))

            # TYPE 4: Top scorers / goal statistics
            if any(
                term in query_lower
                for term in [
                    "scorer",
                    "goals scored",
                    "golden boot",
                    "top goal",
                    "leading scorer",
                    "most goals",
                ]
            ):
                evidence.extend(self._get_top_scorers(query_lower))

            # DO NOT fall back to standings when no keywords match
            # Better to return nothing than irrelevant data (e.g., standings for transfer claims)
            # The semantic relevance filter will handle cases where we return limited data
            if not evidence:
                logger.info(
                    f"Football-Data.org: No keyword match for query '{query[:80]}...', "
                    f"returning empty (claim may be about transfers which this API doesn't cover)"
                )

            logger.info(f"Football-Data.org returned {len(evidence)} evidence items")
            return evidence[: self.max_results]

        except Exception as e:
            logger.error(
                f"Football-Data.org search failed for '{query}': {e}", exc_info=True
            )
            return []

    def _extract_org_names(self, entities: Optional[List[Dict[str, str]]]) -> List[str]:
        """
        Extract ORG entity names (clubs/teams) from NER results.

        Uses dynamic NER entities. Also accepts ENTITY labels as fallback
        if they look like organization names (contain club/team indicators).

        Args:
            entities: List of NER entities [{"text": "Arsenal", "label": "ORG"}, ...]

        Returns:
            List of organization/club names to search for
        """
        orgs = []
        entity_fallbacks = []

        # Common sports/org indicators
        org_indicators = (
            "FC",
            "United",
            "City",
            "Rovers",
            "Athletic",
            "Club",
            "Dortmund",
            "Arsenal",
            "Chelsea",
            "Munich",
            "Madrid",
            "Barcelona",
            "Milan",
            "Inter",
            "Juventus",
            "PSG",
            "Bayern",
            "Liverpool",
            "League",
            "Association",
            "Federation",
            "UEFA",
            "FIFA",
        )

        if entities:
            for ent in entities:
                if not isinstance(ent, dict):
                    continue

                text = ent.get("text", "")
                label = ent.get("label", "")

                if label == "ORG":
                    orgs.append(text)
                elif label == "ENTITY":
                    # Fallback: Check if it looks like an organization
                    if any(ind in text for ind in org_indicators):
                        entity_fallbacks.append(text)

        # Use ORG entities first, fall back to ENTITY if none found
        return orgs if orgs else entity_fallbacks

    def _get_standings(
        self, query_lower: str, entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Get league standings for fact-checking using NER entities."""
        evidence = []

        # Detect which league from query
        competition_code = "PL"  # Default to Premier League
        for code, name in self.competitions.items():
            if name.lower() in query_lower:
                competition_code = code
                break

        # Extract org names from entities for team matching
        org_names = self._extract_org_names(entities)
        org_names_lower = [name.lower() for name in org_names]

        try:
            response = self._make_request(f"/competitions/{competition_code}/standings")

            if not response or "standings" not in response:
                return []

            standings_data = response.get("standings", [])
            competition_name = response.get("competition", {}).get("name", "League")
            season = response.get("season", {})
            current_matchday = season.get("currentMatchday", "Unknown")

            # Find TOTAL standings (not home/away split)
            total_standings = None
            for standing_type in standings_data:
                if standing_type.get("type") == "TOTAL":
                    total_standings = standing_type.get("table", [])
                    break

            if not total_standings:
                return []

            # Build evidence from top positions
            top_teams = total_standings[:6]  # Top 6 teams

            # Create main standings evidence
            standings_text = (
                f"Current {competition_name} standings (Matchday {current_matchday}):\n"
            )
            for team in top_teams:
                pos = team.get("position")
                name = team.get("team", {}).get("name", "Unknown")
                points = team.get("points")
                played = team.get("playedGames")
                won = team.get("won")
                drawn = team.get("draw")
                lost = team.get("lost")
                gd = team.get("goalDifference", 0)
                gd_str = f"+{gd}" if gd > 0 else str(gd)

                standings_text += f"{pos}. {name} - {points} pts (P:{played} W:{won} D:{drawn} L:{lost} GD:{gd_str})\n"

            # Calculate point gaps
            if len(top_teams) >= 2:
                leader = top_teams[0]
                second = top_teams[1]
                gap = leader.get("points", 0) - second.get("points", 0)
                standings_text += f"\n{leader.get('team', {}).get('name', 'Leader')} leads by {gap} points over {second.get('team', {}).get('name', 'Second')}."

            evidence.append(
                self._create_evidence_dict(
                    title=f"{competition_name} Standings - Matchday {current_matchday}",
                    snippet=standings_text.strip(),
                    url=f"https://www.football-data.org/competition/{competition_code}",
                    source_date=datetime.now(timezone.utc),
                    metadata={
                        "api_source": "Football-Data.org",
                        "competition": competition_code,
                        "matchday": current_matchday,
                        "data_type": "standings",
                    },
                )
            )

            # Add individual team evidence for teams mentioned via NER entities
            for team in total_standings[:20]:  # Check more teams
                team_name = team.get("team", {}).get("name", "")
                team_name_lower = team_name.lower()

                # Check if this team matches any ORG entity from NER
                team_mentioned = False
                for org_name in org_names_lower:
                    # Fuzzy match - check if entity name is contained in team name or vice versa
                    if org_name in team_name_lower or team_name_lower in org_name:
                        team_mentioned = True
                        break
                    # Also check partial match (e.g., "Arsenal" matches "Arsenal FC")
                    for word in org_name.split():
                        if len(word) > 3 and word in team_name_lower:
                            team_mentioned = True
                            break

                if team_mentioned:
                    pos = team.get("position")
                    points = team.get("points")
                    played = team.get("playedGames")

                    evidence.append(
                        self._create_evidence_dict(
                            title=f"{team_name} - {competition_name} Position",
                            snippet=f"{team_name} is currently {pos}{'st' if pos == 1 else 'nd' if pos == 2 else 'rd' if pos == 3 else 'th'} in the {competition_name} with {points} points from {played} matches.",
                            url=f"https://www.football-data.org/team/{team.get('team', {}).get('id')}",
                            source_date=datetime.now(timezone.utc),
                            metadata={
                                "api_source": "Football-Data.org",
                                "team_id": team.get("team", {}).get("id"),
                                "position": pos,
                                "points": points,
                                "data_type": "team_standing",
                            },
                        )
                    )

            return evidence

        except Exception as e:
            logger.error(f"Football-Data standings fetch failed: {e}")
            return []

    def _get_team_info(
        self, query_lower: str, entities: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, Any]]:
        """Get team/squad information using NER entities - NO HARDCODED LISTS!"""
        evidence = []

        # Extract org names from NER entities
        org_names = self._extract_org_names(entities)
        if not org_names:
            logger.debug("Football-Data: No ORG entities found for team info search")
            return []

        try:
            # Get all teams from API
            teams_response = self._make_request("/teams", params={"limit": 500})

            if not teams_response or "teams" not in teams_response:
                return []

            all_teams = teams_response.get("teams", [])

            # Find matching teams for each org entity
            for org_name in org_names:
                org_lower = org_name.lower()

                # Find best matching team
                team_id = None
                team_name_match = None

                for team in all_teams:
                    team_name = team.get("name", "")
                    team_lower = team_name.lower()

                    # Fuzzy match - check if entity matches team name
                    if org_lower in team_lower or team_lower in org_lower:
                        team_id = team.get("id")
                        team_name_match = team_name
                        break
                    # Partial match for common variations
                    for word in org_lower.split():
                        if len(word) > 3 and word in team_lower:
                            team_id = team.get("id")
                            team_name_match = team_name
                            break
                    if team_id:
                        break

                if not team_id:
                    continue

                # Get team details
                team_response = self._make_request(f"/teams/{team_id}")

                if not team_response:
                    continue

                team_info = team_response
                squad = team_info.get("squad", [])
                coach = team_info.get("coach", {})

                # Build squad evidence
                squad_text = f"{team_info.get('name')} Squad:\n"
                squad_text += f"Manager: {coach.get('name', 'Unknown')}\n\n"

                # Group by position
                positions = {
                    "Goalkeeper": [],
                    "Defence": [],
                    "Midfield": [],
                    "Offence": [],
                }
                for player in squad:
                    pos = player.get("position", "Unknown")
                    if pos in positions:
                        positions[pos].append(player.get("name"))

                for pos, players in positions.items():
                    if players:
                        squad_text += f"{pos}: {', '.join(players[:5])}\n"

                evidence.append(
                    self._create_evidence_dict(
                        title=f"{team_info.get('name')} Squad Information",
                        snippet=squad_text.strip(),
                        url=team_info.get(
                            "website", f"https://www.football-data.org/team/{team_id}"
                        ),
                        source_date=datetime.now(timezone.utc),
                        metadata={
                            "api_source": "Football-Data.org",
                            "team_id": team_id,
                            "squad_size": len(squad),
                            "data_type": "squad",
                        },
                    )
                )

            return evidence

        except Exception as e:
            logger.error(f"Football-Data team info fetch failed: {e}")
            return []

    def _get_match_results(self, query_lower: str) -> List[Dict[str, Any]]:
        """Get recent match results for detected competition."""
        evidence = []

        # Detect which competition from query (same logic as standings)
        competition_code = "PL"  # Default to Premier League
        for code, name in self.competitions.items():
            if name.lower() in query_lower:
                competition_code = code
                break

        try:
            response = self._make_request(
                f"/competitions/{competition_code}/matches",
                params={"status": "FINISHED", "limit": 10},
            )

            if not response or "matches" not in response:
                return []

            matches = response.get("matches", [])
            competition_name = self.competitions.get(competition_code, "League")

            for match in matches[:5]:
                home = match.get("homeTeam", {}).get("name", "Home")
                away = match.get("awayTeam", {}).get("name", "Away")
                score = match.get("score", {}).get("fullTime", {})
                home_goals = score.get("home", 0)
                away_goals = score.get("away", 0)
                match_date = match.get("utcDate", "")

                result_text = f"{home} {home_goals} - {away_goals} {away}"

                evidence.append(
                    self._create_evidence_dict(
                        title=f"{competition_name} Result: {home} vs {away}",
                        snippet=result_text,
                        url=f"https://www.football-data.org/match/{match.get('id')}",
                        source_date=(
                            datetime.fromisoformat(match_date.replace("Z", "+00:00"))
                            if match_date
                            else None
                        ),
                        metadata={
                            "api_source": "Football-Data.org",
                            "competition": competition_code,
                            "match_id": match.get("id"),
                            "data_type": "match_result",
                        },
                    )
                )

            return evidence

        except Exception as e:
            logger.error(f"Football-Data match results fetch failed: {e}")
            return []

    def _get_top_scorers(self, query_lower: str) -> List[Dict[str, Any]]:
        """Get top scorers for a competition."""
        evidence = []

        # Detect which competition from query
        competition_code = "PL"  # Default to Premier League
        for code, name in self.competitions.items():
            if name.lower() in query_lower:
                competition_code = code
                break

        try:
            response = self._make_request(
                f"/competitions/{competition_code}/scorers", params={"limit": 10}
            )

            if not response or "scorers" not in response:
                logger.warning(f"Top scorers not available for {competition_code}")
                return []

            scorers = response.get("scorers", [])
            competition_name = response.get("competition", {}).get(
                "name", self.competitions.get(competition_code, "League")
            )
            season = response.get("season", {})

            # Build top scorers summary
            scorers_text = f"Top Scorers - {competition_name} ({season.get('startDate', '')[:4]}/{season.get('endDate', '')[:4]} season):\n"

            for i, scorer in enumerate(scorers[:10], 1):
                player = scorer.get("player", {})
                team = scorer.get("team", {})
                goals = scorer.get("goals", 0)
                assists = scorer.get("assists", 0)
                played = scorer.get("playedMatches", 0)

                player_name = player.get("name", "Unknown")
                team_name = team.get("name", "Unknown")

                scorers_text += f"{i}. {player_name} ({team_name}) - {goals} goals"
                if assists:
                    scorers_text += f", {assists} assists"
                scorers_text += f" in {played} matches\n"

            evidence.append(
                self._create_evidence_dict(
                    title=f"{competition_name} Top Scorers",
                    snippet=scorers_text.strip(),
                    url=f"https://www.football-data.org/competition/{competition_code}",
                    source_date=datetime.now(timezone.utc),
                    metadata={
                        "api_source": "Football-Data.org",
                        "competition": competition_code,
                        "data_type": "top_scorers",
                        "season": f"{season.get('startDate', '')[:4]}/{season.get('endDate', '')[:4]}",
                    },
                )
            )

            # Also add individual scorer evidence for players mentioned in query
            for scorer in scorers[:10]:
                player = scorer.get("player", {})
                player_name = player.get("name", "").lower()

                # Check if this player is mentioned in the query
                if any(
                    word in player_name for word in query_lower.split() if len(word) > 3
                ):
                    team = scorer.get("team", {})
                    goals = scorer.get("goals", 0)
                    assists = scorer.get("assists", 0)
                    played = scorer.get("playedMatches", 0)

                    evidence.append(
                        self._create_evidence_dict(
                            title=f"{player.get('name')} - {competition_name} Stats",
                            snippet=f"{player.get('name')} ({team.get('name')}) has scored {goals} goals and provided {assists or 0} assists in {played} matches this season.",
                            url=f"https://www.football-data.org/player/{player.get('id')}",
                            source_date=datetime.now(timezone.utc),
                            metadata={
                                "api_source": "Football-Data.org",
                                "player_id": player.get("id"),
                                "goals": goals,
                                "assists": assists,
                                "data_type": "player_stats",
                            },
                        )
                    )

            return evidence

        except Exception as e:
            logger.error(f"Football-Data top scorers fetch failed: {e}")
            return []

    def _transform_response(self, raw_response: Any) -> List[Dict[str, Any]]:
        """Transform Football-Data.org API response to standardized evidence format."""
        # This is handled by specific methods above
        return []
