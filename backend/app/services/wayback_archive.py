"""Auto-archiving service (F10).

Archives every evidence URL via the Wayback Machine Save API.
Runs as a fire-and-forget background task after pipeline completion.

Rate-limited to ~15 requests/minute (4-second spacing).
Retries once on transient failures. Never raises — logs and continues.
"""

import asyncio
import logging
from typing import Optional

import httpx
from sqlalchemy import select, update

from app.core.database import async_session
from app.models import Claim, Evidence

logger = logging.getLogger(__name__)

WAYBACK_SAVE_URL = "https://web.archive.org/save/"
# Wayback's Save API routinely takes 60-120s to capture a page; a short
# timeout silently zeroes the archive yield (observed live 2026-06-12).
REQUEST_TIMEOUT = 120.0
INTER_REQUEST_DELAY = 4.0  # seconds between requests (~15/min)
RETRY_DELAYS = {
    429: 60.0,  # Rate limited — wait longer
    503: 30.0,  # Service unavailable
}
DEFAULT_RETRY_DELAY = 30.0


def _extract_archive_url(response: httpx.Response) -> Optional[str]:
    """Extract the archived snapshot URL from Wayback response headers."""
    # The Save API returns the archive path in Content-Location or Location
    for header in ("Content-Location", "Location"):
        value = response.headers.get(header)
        if value:
            # Content-Location is often a relative path like /web/20260223.../url
            if value.startswith("/"):
                return f"https://web.archive.org{value}"
            if value.startswith("https://web.archive.org/"):
                return value

    # Fallback: construct from the response URL if it redirected to the snapshot
    final_url = str(response.url)
    if "web.archive.org/web/" in final_url:
        return final_url

    return None


async def _archive_single_url(
    client: httpx.AsyncClient,
    url: str,
) -> Optional[str]:
    """Attempt to archive a single URL. Returns archive URL or None."""
    for attempt in range(2):  # max 2 attempts (initial + 1 retry)
        try:
            response = await client.get(
                f"{WAYBACK_SAVE_URL}{url}",
                timeout=REQUEST_TIMEOUT,
                follow_redirects=True,
            )

            if response.status_code == 200:
                archive_url = _extract_archive_url(response)
                if archive_url:
                    return archive_url
                logger.warning(
                    f"[ARCHIVE] No archive URL in response headers for {url}"
                )
                return None

            # Retriable status codes
            if response.status_code in (429, 503) and attempt == 0:
                delay = RETRY_DELAYS.get(response.status_code, DEFAULT_RETRY_DELAY)
                logger.info(
                    f"[ARCHIVE] HTTP {response.status_code} for {url}, "
                    f"retrying in {delay}s"
                )
                await asyncio.sleep(delay)
                continue

            logger.warning(f"[ARCHIVE] HTTP {response.status_code} for {url}, skipping")
            return None

        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            if attempt == 0:
                logger.info(
                    f"[ARCHIVE] {type(exc).__name__} for {url}, "
                    f"retrying in {DEFAULT_RETRY_DELAY}s"
                )
                await asyncio.sleep(DEFAULT_RETRY_DELAY)
                continue
            logger.warning(
                f"[ARCHIVE] {type(exc).__name__} for {url} on retry, skipping"
            )
            return None

        except Exception as exc:
            logger.warning(f"[ARCHIVE] Unexpected error for {url}: {exc}")
            return None

    return None


async def archive_evidence_urls(check_id: str) -> None:
    """Background task: archive all evidence URLs for a check via Wayback Machine.

    Processes sequentially with rate limiting. Idempotent — only touches
    evidence where archived_url IS NULL.
    """
    logger.info(f"[ARCHIVE] Starting archiving for check {check_id}")

    try:
        async with async_session() as session:
            # Get claim IDs for this check
            claims_result = await session.execute(
                select(Claim.id).where(Claim.check_id == check_id)
            )
            claim_ids = [row[0] for row in claims_result.all()]

            if not claim_ids:
                logger.info(f"[ARCHIVE] No claims found for check {check_id}")
                return

            # Get evidence needing archiving
            evidence_result = await session.execute(
                select(Evidence.id, Evidence.url)
                .where(Evidence.claim_id.in_(claim_ids))
                .where(Evidence.archived_url.is_(None))
                .where(Evidence.url.isnot(None))
            )
            evidence_rows = evidence_result.all()

        if not evidence_rows:
            logger.info(f"[ARCHIVE] No evidence needs archiving for check {check_id}")
            return

        logger.info(
            f"[ARCHIVE] Archiving {len(evidence_rows)} URLs for check {check_id}"
        )

        archived_count = 0
        async with httpx.AsyncClient(
            headers={
                "User-Agent": "Tru8 Evidence Archiver (+https://www.trueight.com)"
            },
        ) as client:
            for i, (evidence_id, url) in enumerate(evidence_rows):
                archive_url = await _archive_single_url(client, url)

                if archive_url:
                    async with async_session() as session:
                        await session.execute(
                            update(Evidence)
                            .where(Evidence.id == evidence_id)
                            .values(archived_url=archive_url)
                        )
                        await session.commit()
                    archived_count += 1

                # Rate limit — don't sleep after the last item
                if i < len(evidence_rows) - 1:
                    await asyncio.sleep(INTER_REQUEST_DELAY)

        logger.info(
            f"[ARCHIVE] Completed for check {check_id}: "
            f"{archived_count}/{len(evidence_rows)} URLs archived"
        )

    except Exception as exc:
        logger.error(f"[ARCHIVE] Failed for check {check_id}: {exc}")
