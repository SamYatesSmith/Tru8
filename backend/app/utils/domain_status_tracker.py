"""
Domain Status Tracker

Collects and categorizes domains based on their access status during scraping.
This is a ONE-TIME collection system - domains are recorded once and persisted.

Categories:
- ACCESSIBLE: Content successfully extracted
- BOT_BLOCKED: Returns 403/429, likely bot detection
- PAYWALL: Content exists but requires subscription
- JS_REQUIRED: Page loads but content is JS-rendered (empty extraction)
- TIMEOUT: Consistently times out
- UNKNOWN: Other errors

Usage:
    tracker = get_domain_tracker()
    tracker.record_access_result("example.com", DomainStatus.BOT_BLOCKED, {"status_code": 403})

    # Get domains by category for budgeting
    paywalled = tracker.get_domains_by_status(DomainStatus.PAYWALL)
"""

import json
import logging
from enum import Enum
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from threading import Lock

logger = logging.getLogger(__name__)


class DomainStatus(Enum):
    """Domain access status categories"""
    ACCESSIBLE = "accessible"           # Successfully scraped
    BOT_BLOCKED = "bot_blocked"         # 403/429 - bot detection
    PAYWALL = "paywall"                 # Subscription required
    JS_REQUIRED = "js_required"         # Content is JS-rendered
    TIMEOUT = "timeout"                 # Consistently times out
    RATE_LIMITED = "rate_limited"       # Temporary rate limiting
    UNKNOWN = "unknown"                 # Other errors


class DomainStatusTracker:
    """
    Persistent tracker for domain access status.

    Records domain status ONCE - subsequent encounters of the same domain
    do not update the record (unless explicitly requested).

    Persists to JSON file for analysis and budgeting.
    """

    # Known paywall domains (pre-seeded)
    KNOWN_PAYWALLS = {
        "thetimes.co.uk": "The Times",
        "telegraph.co.uk": "The Telegraph",
        "ft.com": "Financial Times",
        "wsj.com": "Wall Street Journal",
        "nytimes.com": "New York Times",
        "washingtonpost.com": "Washington Post",
        "economist.com": "The Economist",
        "bloomberg.com": "Bloomberg",
        "theathletic.com": "The Athletic",
    }

    # Known bot-blocking domains (pre-seeded)
    KNOWN_BOT_BLOCKED = {
        "yahoo.com": "Aggressive bot detection",
        "linkedin.com": "Requires authentication",
        "facebook.com": "Requires authentication",
        "instagram.com": "Requires authentication",
    }

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize tracker with optional custom storage path.

        Args:
            storage_path: Path to JSON storage file. Defaults to data/domain_status.json
        """
        if storage_path is None:
            # Default to backend/data/domain_status.json
            storage_path = Path(__file__).parent.parent.parent / "data" / "domain_status.json"

        self.storage_path = storage_path
        self._lock = Lock()
        self._domains: Dict[str, Dict[str, Any]] = {}
        self._load()
        self._seed_known_domains()

    def _load(self) -> None:
        """Load existing domain data from storage"""
        try:
            if self.storage_path.exists():
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    self._domains = data.get("domains", {})
                    logger.info(f"[DOMAIN_TRACKER] Loaded {len(self._domains)} domain records")
            else:
                self._domains = {}
                logger.info("[DOMAIN_TRACKER] No existing data, starting fresh")
        except Exception as e:
            logger.error(f"[DOMAIN_TRACKER] Failed to load: {e}")
            self._domains = {}

    def _save(self) -> None:
        """Persist domain data to storage"""
        try:
            # Ensure directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "last_updated": datetime.utcnow().isoformat(),
                "total_domains": len(self._domains),
                "domains": self._domains,
                "summary": self._generate_summary()
            }

            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"[DOMAIN_TRACKER] Failed to save: {e}")

    def _seed_known_domains(self) -> None:
        """Pre-seed known paywall and blocked domains"""
        seeded = 0

        for domain, name in self.KNOWN_PAYWALLS.items():
            if domain not in self._domains:
                self._domains[domain] = {
                    "status": DomainStatus.PAYWALL.value,
                    "first_seen": datetime.utcnow().isoformat(),
                    "source": "pre_seeded",
                    "notes": name,
                    "encounter_count": 0
                }
                seeded += 1

        for domain, reason in self.KNOWN_BOT_BLOCKED.items():
            if domain not in self._domains:
                self._domains[domain] = {
                    "status": DomainStatus.BOT_BLOCKED.value,
                    "first_seen": datetime.utcnow().isoformat(),
                    "source": "pre_seeded",
                    "notes": reason,
                    "encounter_count": 0
                }
                seeded += 1

        if seeded > 0:
            logger.info(f"[DOMAIN_TRACKER] Seeded {seeded} known domains")
            self._save()

    def record_access_result(
        self,
        domain: str,
        status: DomainStatus,
        metadata: Optional[Dict[str, Any]] = None,
        force_update: bool = False
    ) -> bool:
        """
        Record domain access result.

        By default, only records NEW domains. Existing domains are not updated
        unless force_update=True.

        Args:
            domain: Domain name (e.g., "example.com")
            status: Access status
            metadata: Optional additional info (status_code, error message, etc.)
            force_update: If True, updates existing records

        Returns:
            True if record was created/updated, False if skipped (already exists)
        """
        # Normalize domain
        domain = domain.lower().strip()
        if domain.startswith("www."):
            domain = domain[4:]

        with self._lock:
            # Skip if already recorded (unless forcing update)
            if domain in self._domains:
                # Just increment encounter count
                self._domains[domain]["encounter_count"] = \
                    self._domains[domain].get("encounter_count", 0) + 1
                self._domains[domain]["last_seen"] = datetime.utcnow().isoformat()

                if not force_update:
                    return False

            # Record new domain or update existing
            self._domains[domain] = {
                "status": status.value,
                "first_seen": self._domains.get(domain, {}).get(
                    "first_seen", datetime.utcnow().isoformat()
                ),
                "last_seen": datetime.utcnow().isoformat(),
                "source": "runtime_detection",
                "metadata": metadata or {},
                "encounter_count": self._domains.get(domain, {}).get("encounter_count", 0) + 1
            }

            self._save()

            logger.info(f"[DOMAIN_TRACKER] Recorded: {domain} -> {status.value}")
            return True

    def get_status(self, domain: str) -> Optional[DomainStatus]:
        """Get recorded status for a domain"""
        domain = domain.lower().strip()
        if domain.startswith("www."):
            domain = domain[4:]

        record = self._domains.get(domain)
        if record:
            return DomainStatus(record["status"])
        return None

    def is_known_blocked(self, domain: str) -> bool:
        """Quick check if domain is known to be blocked"""
        status = self.get_status(domain)
        return status in (DomainStatus.BOT_BLOCKED, DomainStatus.RATE_LIMITED)

    def is_paywall(self, domain: str) -> bool:
        """Quick check if domain is behind paywall"""
        return self.get_status(domain) == DomainStatus.PAYWALL

    def get_domains_by_status(self, status: DomainStatus) -> List[Dict[str, Any]]:
        """
        Get all domains with a specific status.

        Useful for:
        - Budgeting paywall subscriptions
        - Reviewing blocked domains
        - Planning Playwright integration for JS-required sites
        """
        results = []
        for domain, record in self._domains.items():
            if record["status"] == status.value:
                results.append({
                    "domain": domain,
                    **record
                })
        return sorted(results, key=lambda x: x.get("encounter_count", 0), reverse=True)

    def _generate_summary(self) -> Dict[str, int]:
        """Generate status summary for storage"""
        summary = {}
        for record in self._domains.values():
            status = record["status"]
            summary[status] = summary.get(status, 0) + 1
        return summary

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all tracked domains"""
        summary = self._generate_summary()
        return {
            "total_domains": len(self._domains),
            "by_status": summary,
            "paywall_domains": len(self.get_domains_by_status(DomainStatus.PAYWALL)),
            "blocked_domains": len(self.get_domains_by_status(DomainStatus.BOT_BLOCKED)),
            "js_required_domains": len(self.get_domains_by_status(DomainStatus.JS_REQUIRED)),
        }

    def export_for_budgeting(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Export categorized domains for budgeting decisions.

        Returns:
            {
                "paywall_priority": [...],  # High encounter count paywalls
                "consider_playwright": [...],  # JS-required sites worth investing in
                "blocked_investigate": [...]  # Blocked sites to investigate
            }
        """
        paywalls = self.get_domains_by_status(DomainStatus.PAYWALL)
        js_required = self.get_domains_by_status(DomainStatus.JS_REQUIRED)
        blocked = self.get_domains_by_status(DomainStatus.BOT_BLOCKED)

        return {
            "paywall_priority": [
                p for p in paywalls if p.get("encounter_count", 0) >= 3
            ],
            "consider_playwright": [
                j for j in js_required if j.get("encounter_count", 0) >= 5
            ],
            "blocked_investigate": [
                b for b in blocked if b.get("encounter_count", 0) >= 3
            ]
        }


# Singleton instance
_tracker: Optional[DomainStatusTracker] = None

def get_domain_tracker() -> DomainStatusTracker:
    """Get singleton tracker instance"""
    global _tracker
    if _tracker is None:
        _tracker = DomainStatusTracker()
    return _tracker
