"""Snapshot/restore data/domain_status.json so the bench has a deterministic
starting state and never corrupts the user's accumulated runtime state."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional


BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DOMAIN_STATUS_LIVE = BACKEND_DIR / "data" / "domain_status.json"
DOMAIN_STATUS_FIXTURE = (
    BACKEND_DIR / "tests" / "replay_corpus" / "_fixtures" / "domain_status.json"
)


class DomainStatusFixture:
    """Context manager: backs up live file, swaps fixture in for the bench
    session, restores live file on exit."""

    def __init__(self) -> None:
        self._backup_path: Optional[Path] = None

    def __enter__(self) -> "DomainStatusFixture":
        if DOMAIN_STATUS_LIVE.exists():
            self._backup_path = DOMAIN_STATUS_LIVE.with_suffix(".json.bench_backup")
            shutil.copy2(DOMAIN_STATUS_LIVE, self._backup_path)
        self._install_fixture()
        return self

    def __exit__(self, *_exc) -> None:
        if self._backup_path and self._backup_path.exists():
            shutil.copy2(self._backup_path, DOMAIN_STATUS_LIVE)
            self._backup_path.unlink()
        elif self._backup_path is None and DOMAIN_STATUS_LIVE.exists():
            DOMAIN_STATUS_LIVE.unlink()

    def reset_between_claims(self) -> None:
        """Re-install fixture and reset the tracker singleton so the next
        pipeline call sees a clean slate."""
        self._install_fixture()
        self._reset_singleton()

    def _install_fixture(self) -> None:
        DOMAIN_STATUS_LIVE.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(DOMAIN_STATUS_FIXTURE, DOMAIN_STATUS_LIVE)

    @staticmethod
    def _reset_singleton() -> None:
        try:
            from app.utils import domain_status_tracker

            domain_status_tracker._tracker = None
        except Exception:
            pass
