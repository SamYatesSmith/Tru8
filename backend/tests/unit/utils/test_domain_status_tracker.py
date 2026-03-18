"""Tests for DomainStatusTracker and DomainStatus enum."""

import json
import pytest
from pathlib import Path

from app.utils.domain_status_tracker import DomainStatus, DomainStatusTracker


# ---------------------------------------------------------------------------
# 1. TestDomainStatusEnum
# ---------------------------------------------------------------------------


class TestDomainStatusEnum:
    """Verify the DomainStatus enum shape."""

    def test_all_statuses_exist(self):
        """All 7 enum members are present."""
        expected = {
            "ACCESSIBLE",
            "BOT_BLOCKED",
            "PAYWALL",
            "JS_REQUIRED",
            "TIMEOUT",
            "RATE_LIMITED",
            "UNKNOWN",
        }
        assert set(DomainStatus.__members__.keys()) == expected

    def test_enum_values(self):
        """String values are lowercase."""
        for member in DomainStatus:
            assert member.value == member.value.lower()
            assert member.value == member.name.lower()


# ---------------------------------------------------------------------------
# 2. TestRecordAccessResult
# ---------------------------------------------------------------------------


class TestRecordAccessResult:
    """Verify recording behaviour — new domains, normalisation, dedup."""

    def test_records_new_domain(self, tmp_path: Path):
        """Recording a new domain returns True and stores the status."""
        tracker = DomainStatusTracker(storage_path=tmp_path / "ds.json")
        result = tracker.record_access_result("newsite.org", DomainStatus.ACCESSIBLE)
        assert result is True
        assert tracker.get_status("newsite.org") == DomainStatus.ACCESSIBLE

    def test_normalizes_domain(self, tmp_path: Path):
        """www prefix and mixed case are stripped/lowered."""
        tracker = DomainStatusTracker(storage_path=tmp_path / "ds.json")
        tracker.record_access_result("www.Example.Com", DomainStatus.TIMEOUT)
        assert tracker.get_status("example.com") == DomainStatus.TIMEOUT
        # Also retrievable via the un-normalised form
        assert tracker.get_status("www.Example.Com") == DomainStatus.TIMEOUT

    def test_increments_encounter_count(self, tmp_path: Path):
        """Recording the same domain twice increments encounter_count."""
        tracker = DomainStatusTracker(storage_path=tmp_path / "ds.json")
        tracker.record_access_result("repeat.io", DomainStatus.ACCESSIBLE)
        tracker.record_access_result("repeat.io", DomainStatus.ACCESSIBLE)
        record = tracker._domains["repeat.io"]
        assert record["encounter_count"] == 2

    def test_skips_duplicate_without_force(self, tmp_path: Path):
        """Second call without force_update returns False (no status change)."""
        tracker = DomainStatusTracker(storage_path=tmp_path / "ds.json")
        tracker.record_access_result("dup.io", DomainStatus.ACCESSIBLE)
        result = tracker.record_access_result("dup.io", DomainStatus.BOT_BLOCKED)
        assert result is False
        # Status unchanged
        assert tracker.get_status("dup.io") == DomainStatus.ACCESSIBLE

    def test_force_update_overwrites(self, tmp_path: Path):
        """force_update=True changes the stored status."""
        tracker = DomainStatusTracker(storage_path=tmp_path / "ds.json")
        tracker.record_access_result("change.io", DomainStatus.UNKNOWN)
        result = tracker.record_access_result(
            "change.io", DomainStatus.ACCESSIBLE, force_update=True
        )
        assert result is True
        assert tracker.get_status("change.io") == DomainStatus.ACCESSIBLE


# ---------------------------------------------------------------------------
# 3. TestStatusQueries
# ---------------------------------------------------------------------------


class TestStatusQueries:
    """Verify status lookup helpers."""

    def test_get_status_returns_none_for_unknown(self, tmp_path: Path):
        """An unrecorded domain returns None."""
        tracker = DomainStatusTracker(storage_path=tmp_path / "ds.json")
        assert tracker.get_status("never-seen.dev") is None

    def test_is_known_blocked(self, tmp_path: Path):
        """BOT_BLOCKED -> True, ACCESSIBLE -> False."""
        tracker = DomainStatusTracker(storage_path=tmp_path / "ds.json")
        tracker.record_access_result("blocked.io", DomainStatus.BOT_BLOCKED)
        tracker.record_access_result("open.io", DomainStatus.ACCESSIBLE)
        assert tracker.is_known_blocked("blocked.io") is True
        assert tracker.is_known_blocked("open.io") is False

    def test_is_paywall(self, tmp_path: Path):
        """PAYWALL -> True, ACCESSIBLE -> False."""
        tracker = DomainStatusTracker(storage_path=tmp_path / "ds.json")
        tracker.record_access_result("pay.io", DomainStatus.PAYWALL)
        tracker.record_access_result("free.io", DomainStatus.ACCESSIBLE)
        assert tracker.is_paywall("pay.io") is True
        assert tracker.is_paywall("free.io") is False

    def test_get_domains_by_status(self, tmp_path: Path):
        """Returns only matching domains, sorted by encounter_count desc."""
        tracker = DomainStatusTracker(storage_path=tmp_path / "ds.json")
        # Record two accessible and one blocked
        tracker.record_access_result("a.com", DomainStatus.ACCESSIBLE)
        tracker.record_access_result("b.com", DomainStatus.ACCESSIBLE)
        tracker.record_access_result("c.com", DomainStatus.BOT_BLOCKED)

        # Bump b.com's encounter count so it sorts first
        tracker.record_access_result("b.com", DomainStatus.ACCESSIBLE)

        accessible = tracker.get_domains_by_status(DomainStatus.ACCESSIBLE)
        domains = [d["domain"] for d in accessible]
        assert "a.com" in domains
        assert "b.com" in domains
        assert "c.com" not in domains
        # b.com has 2 encounters, a.com has 1 -> b.com first
        assert domains.index("b.com") < domains.index("a.com")


# ---------------------------------------------------------------------------
# 4. TestSummaryAndExport
# ---------------------------------------------------------------------------


class TestSummaryAndExport:
    """Verify summary generation and pre-seeded domains."""

    def test_get_summary(self, tmp_path: Path):
        """Summary includes total_domains and by_status counts."""
        tracker = DomainStatusTracker(storage_path=tmp_path / "ds.json")
        tracker.record_access_result("s1.com", DomainStatus.ACCESSIBLE)
        tracker.record_access_result("s2.com", DomainStatus.ACCESSIBLE)
        tracker.record_access_result("s3.com", DomainStatus.TIMEOUT)

        summary = tracker.get_summary()
        assert "total_domains" in summary
        assert "by_status" in summary
        # At minimum: pre-seeded paywalls + bot_blocked + the 3 we just added
        assert summary["total_domains"] >= 3
        assert summary["by_status"].get("accessible", 0) >= 2
        assert summary["by_status"].get("timeout", 0) >= 1

    def test_seeded_domains(self, tmp_path: Path):
        """KNOWN_PAYWALLS and KNOWN_BOT_BLOCKED are pre-populated on init."""
        tracker = DomainStatusTracker(storage_path=tmp_path / "ds.json")

        for domain in DomainStatusTracker.KNOWN_PAYWALLS:
            assert (
                tracker.get_status(domain) == DomainStatus.PAYWALL
            ), f"{domain} should be seeded as PAYWALL"

        for domain in DomainStatusTracker.KNOWN_BOT_BLOCKED:
            assert (
                tracker.get_status(domain) == DomainStatus.BOT_BLOCKED
            ), f"{domain} should be seeded as BOT_BLOCKED"


# ---------------------------------------------------------------------------
# 5. TestPersistence
# ---------------------------------------------------------------------------


class TestPersistence:
    """Verify JSON file persistence."""

    def test_saves_and_loads(self, tmp_path: Path):
        """Data recorded by one tracker instance is available to a new one."""
        path = tmp_path / "persist.json"
        tracker1 = DomainStatusTracker(storage_path=path)
        tracker1.record_access_result("persist.io", DomainStatus.JS_REQUIRED)

        # New instance, same file
        tracker2 = DomainStatusTracker(storage_path=path)
        assert tracker2.get_status("persist.io") == DomainStatus.JS_REQUIRED

    def test_creates_file(self, tmp_path: Path):
        """The storage file is created after recording a domain."""
        path = tmp_path / "subdir" / "tracker.json"
        assert not path.exists()
        tracker = DomainStatusTracker(storage_path=path)
        tracker.record_access_result("file.io", DomainStatus.ACCESSIBLE)
        assert path.exists()

        # Verify the file is valid JSON with expected structure
        data = json.loads(path.read_text())
        assert "domains" in data
        assert "file.io" in data["domains"]
