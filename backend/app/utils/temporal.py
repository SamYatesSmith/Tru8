import re
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class TemporalAnalyzer:
    """Detect and analyze temporal context in claims"""

    def __init__(self):
        # Get current year dynamically
        current_year = datetime.now().year
        next_year = current_year + 1
        last_year = current_year - 1

        # Temporal marker patterns (dynamic based on current year)
        self.time_markers = {
            "present": rf"\b(today|now|currently|at present|this year|{current_year})\b",
            "recent_past": rf"\b(yesterday|last week|last month|recently|{last_year})\b",
            "specific_year": r"\b(in 20\d{2}|during 20\d{2})\b",
            "specific_date": r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:st|nd|rd|th)?,?\s*20\d{2}\b",
            "historical": r"\b(in the past|historically|previously)\b",
            "future": rf"\b(will|going to|next year|in the future|{next_year})\b",
        }

        # Store current year for reference
        self.current_year = current_year

    def analyze_claim(self, claim_text: str) -> Dict[str, Any]:
        """Determine if claim is time-sensitive and extract temporal context"""
        claim_lower = claim_text.lower()

        # Detect temporal markers
        detected_markers = {}
        for category, pattern in self.time_markers.items():
            matches = re.findall(pattern, claim_lower, re.IGNORECASE)
            if matches:
                detected_markers[category] = matches

        # Also extract any years mentioned (standalone, not just in patterns)
        years_found = re.findall(r"\b20\d{2}\b", claim_text)
        if years_found:
            detected_markers["years_mentioned"] = list(set(years_found))
            # If current year mentioned, mark as present
            if str(self.current_year) in years_found:
                if "present" not in detected_markers:
                    detected_markers["present"] = [str(self.current_year)]
            # If any year > current year mentioned, mark as future
            future_years = [y for y in years_found if int(y) > self.current_year]
            if future_years and "future" not in detected_markers:
                detected_markers["future"] = future_years

        is_time_sensitive = bool(detected_markers)

        # Determine temporal window for evidence (priority order)
        # 1. Specific dates (e.g., "January 6, 2026") = very recent
        # 2. Present markers (today, 2026) = last 30 days
        # 3. Recent past (yesterday, last week) = last 90 days
        # 4. Specific year = that year
        if "specific_date" in detected_markers:
            temporal_window = "last_7_days"
            max_evidence_age_days = 7
        elif "future" in detected_markers:
            temporal_window = "future"
            max_evidence_age_days = 365  # Accept recent evidence about future events
        elif "present" in detected_markers:
            temporal_window = "last_30_days"
            max_evidence_age_days = 30
        elif "recent_past" in detected_markers:
            temporal_window = "last_90_days"
            max_evidence_age_days = 90
        elif (
            "specific_year" in detected_markers or "years_mentioned" in detected_markers
        ):
            year = self._extract_year(claim_text)
            temporal_window = f"year_{year}"
            max_evidence_age_days = 365  # Accept evidence from that year
        else:
            temporal_window = "timeless"
            max_evidence_age_days = None

        return {
            "is_time_sensitive": is_time_sensitive,
            "temporal_markers": detected_markers,
            "temporal_window": temporal_window,
            "max_evidence_age_days": max_evidence_age_days,
            "claim_type": self._classify_temporal_type(detected_markers),
            "years_mentioned": years_found if years_found else [],
        }

    def _extract_year(self, text: str) -> Optional[str]:
        """Extract specific year from claim"""
        match = re.search(r"20\d{2}", text)
        return match.group(0) if match else None

    def _classify_temporal_type(self, markers: Dict) -> str:
        """Classify claim by temporal type"""
        if "specific_date" in markers:
            return "breaking_news"  # Very specific date = likely breaking news
        elif "future" in markers:
            return "prediction"
        elif "present" in markers:
            return "current_state"
        elif "specific_year" in markers or "years_mentioned" in markers:
            return "historical_fact"
        else:
            return "timeless_fact"

    def filter_evidence_by_time(
        self, evidence: List[Dict], temporal_analysis: Dict
    ) -> List[Dict]:
        """Filter evidence based on temporal requirements"""
        if not temporal_analysis["is_time_sensitive"]:
            return evidence

        max_age_days = temporal_analysis["max_evidence_age_days"]
        if max_age_days is None:
            return evidence

        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        filtered = []

        for ev in evidence:
            pub_date = ev.get("published_date")
            if pub_date:
                try:
                    # Parse various date formats
                    ev_date = self._parse_date(pub_date)
                    if ev_date and ev_date >= cutoff_date:
                        filtered.append(ev)
                    else:
                        logger.debug(
                            f"Evidence too old: {pub_date} (cutoff: {cutoff_date})"
                        )
                except:
                    # If can't parse, include it (benefit of doubt)
                    filtered.append(ev)
            else:
                # No date = assume recent enough
                filtered.append(ev)

        logger.info(
            f"Temporal filtering: {len(evidence)} -> {len(filtered)} "
            f"(max age: {max_age_days} days)"
        )

        return filtered

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse various date formats"""
        # Handle datetime objects
        if isinstance(date_str, datetime):
            return date_str

        # Try ISO format
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except:
            pass

        # Try common formats
        formats = ["%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%B %d, %Y"]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except:
                continue

        # Extract year and assume Jan 1
        match = re.search(r"20\d{2}", date_str)
        if match:
            year = int(match.group(0))
            return datetime(year, 1, 1)

        return None
