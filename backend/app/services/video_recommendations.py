"""Video recommendations orchestrator (E14).

Fetches YouTube videos for each claim, applies channel-based
tier/type heuristic classification, dedupes by video ID, saves to DB.

This is a standalone feature — NOT part of the evidence pipeline.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session
from app.models.video_recommendation import VideoRecommendation
from app.services.api_adapters.youtube import search_youtube_videos

logger = logging.getLogger(__name__)

# Channel heuristic classification table.
# Maps known channel names (lowercase) to (tier, type).
# Unknown channels default to commentary / analysis.
CHANNEL_HEURISTICS: Dict[str, Tuple[str, str]] = {
    # T1 / Primary — government, data, official
    "white house": ("primary", "official_statement"),
    "the white house": ("primary", "official_statement"),
    "united nations": ("primary", "official_statement"),
    "european commission": ("primary", "official_statement"),
    "uk parliament": ("primary", "official_statement"),
    "c-span": ("primary", "official_statement"),
    "nasa": ("primary", "data"),
    "noaa": ("primary", "data"),
    "world health organization (who)": ("primary", "official_statement"),
    "world bank": ("primary", "data"),
    "imf": ("primary", "data"),
    "ted": ("primary", "academic"),
    "tedx talks": ("primary", "academic"),
    "nature video": ("primary", "academic"),
    "mit opencourseware": ("primary", "academic"),
    # T2 / Reporting — news organisations
    "reuters": ("reporting", "news_reporting"),
    "associated press": ("reporting", "news_reporting"),
    "ap": ("reporting", "news_reporting"),
    "bbc news": ("reporting", "news_reporting"),
    "bbc": ("reporting", "news_reporting"),
    "cnn": ("reporting", "news_reporting"),
    "cnbc": ("reporting", "news_reporting"),
    "abc news": ("reporting", "news_reporting"),
    "nbc news": ("reporting", "news_reporting"),
    "cbs news": ("reporting", "news_reporting"),
    "sky news": ("reporting", "news_reporting"),
    "al jazeera english": ("reporting", "news_reporting"),
    "france 24 english": ("reporting", "news_reporting"),
    "dw news": ("reporting", "news_reporting"),
    "bloomberg television": ("reporting", "news_reporting"),
    "bloomberg quicktake": ("reporting", "analysis"),
    "the guardian": ("reporting", "news_reporting"),
    "the new york times": ("reporting", "news_reporting"),
    "the washington post": ("reporting", "news_reporting"),
    "channel 4 news": ("reporting", "news_reporting"),
    "itv news": ("reporting", "news_reporting"),
    "fox news": ("reporting", "news_reporting"),
    "msnbc": ("reporting", "news_reporting"),
    "pbs newshour": ("reporting", "news_reporting"),
    "pbs nova": ("reporting", "analysis"),
    "vice news": ("reporting", "news_reporting"),
    "the economist": ("reporting", "analysis"),
    "financial times": ("reporting", "analysis"),
    "wall street journal": ("reporting", "news_reporting"),
    "nbc news now": ("reporting", "news_reporting"),
    "abc news in-depth": ("reporting", "analysis"),
    # T3 / Commentary — think-tanks, opinion, explainers
    "vox": ("commentary", "analysis"),
    "kurzgesagt – in a nutshell": ("commentary", "analysis"),
    "wendover productions": ("commentary", "analysis"),
    "reallifelore": ("commentary", "analysis"),
    "johnny harris": ("commentary", "opinion"),
    "last week tonight": ("commentary", "opinion"),
    "the daily show": ("commentary", "opinion"),
    "brookings institution": ("commentary", "analysis"),
    "chatham house": ("commentary", "analysis"),
    "council on foreign relations": ("commentary", "analysis"),
    "cato institute": ("commentary", "analysis"),
    "heritage foundation": ("commentary", "opinion"),
}


def classify_channel(channel_name: str) -> Tuple[str, str]:
    """Classify a YouTube channel by heuristic lookup.

    Returns (tier, type). Defaults to (commentary, analysis) for unknowns.
    """
    key = channel_name.strip().lower()

    # Exact match
    if key in CHANNEL_HEURISTICS:
        return CHANNEL_HEURISTICS[key]

    # Partial match — check if any known channel is a substring
    for known, classification in CHANNEL_HEURISTICS.items():
        if known in key or key in known:
            return classification

    return ("commentary", "analysis")


async def fetch_video_recommendations(
    check_id: str,
    claims: List[Dict[str, Any]],
    max_per_claim: int = 5,
) -> None:
    """Fetch and save video recommendations for all claims.

    Fire-and-forget task — errors are logged, never raised.
    Dedupes videos by video_id across claims.

    Args:
        check_id: The check these claims belong to.
        claims: List of claim dicts with at least 'id' and 'text'.
        max_per_claim: Max videos per claim (default 5).
    """
    try:
        seen_video_ids: set = set()
        all_recommendations: List[Dict[str, Any]] = []

        # Fetch every claim's videos CONCURRENTLY — collapses the fire-and-forget
        # window from (claims x ~1-2s) to ~1-2s flat, so an API restart is far
        # less likely to catch the task mid-flight. return_exceptions keeps one
        # claim's failure from sinking the rest.
        valid_claims = [c for c in claims if c.get("id") and c.get("text")]
        search_results = await asyncio.gather(
            *[
                search_youtube_videos(query=c["text"][:200], max_results=max_per_claim)
                for c in valid_claims
            ],
            return_exceptions=True,
        )

        # Process in claim order so cross-claim dedupe stays deterministic
        # (the first claim to surface a video keeps it).
        for claim, videos in zip(valid_claims, search_results):
            if isinstance(videos, Exception):
                logger.warning(
                    f"[VIDEO RECS] Search failed for claim {claim.get('id')}: {videos}"
                )
                continue
            claim_id = claim["id"]
            for video in videos:
                vid_id = video["video_id"]
                if vid_id in seen_video_ids:
                    continue
                seen_video_ids.add(vid_id)

                tier, etype = classify_channel(video["channel_name"])
                all_recommendations.append(
                    {
                        "check_id": check_id,
                        "claim_id": claim_id,
                        "video_id": vid_id,
                        "title": video["title"],
                        "description": (video.get("description") or "")[:2000],
                        "channel_name": video["channel_name"],
                        "channel_id": video.get("channel_id"),
                        "publish_date": video.get("publish_date"),
                        "video_url": video["video_url"],
                        "thumbnail_url": video.get("thumbnail_url"),
                        "duration": video.get("duration"),
                        "tier_label": tier,
                        "type_label": etype,
                    }
                )

        if not all_recommendations:
            logger.info(f"[VIDEO RECS] No videos found for check {check_id}")
            return

        # Save to database — skip any video already stored for this check so a
        # re-run (the recover endpoint after a lost fire-and-forget task, or a
        # second generation) can't double-insert the same video.
        async with async_session() as session:
            existing_ids = set(
                (
                    await session.execute(
                        select(VideoRecommendation.video_id).where(
                            VideoRecommendation.check_id == check_id
                        )
                    )
                )
                .scalars()
                .all()
            )
            to_add = [
                r for r in all_recommendations if r["video_id"] not in existing_ids
            ]
            for rec in to_add:
                session.add(VideoRecommendation(**rec))
            await session.commit()

        logger.info(
            f"[VIDEO RECS] Saved {len(to_add)} new videos "
            f"({len(all_recommendations) - len(to_add)} already stored) "
            f"for check {check_id} ({len(claims)} claims)"
        )

    except Exception as e:
        logger.error(f"[VIDEO RECS] Failed for check {check_id}: {e}")
