"""YouTube Data API v3 adapter (E14).

Standalone video retrieval — NOT pipeline evidence.
Fetches up to 5 relevant YouTube videos per claim.
Graceful degradation if API key missing or quota exceeded.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"


async def search_youtube_videos(
    query: str,
    max_results: int = 5,
    published_after: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search YouTube for videos matching a query.

    Args:
        query: Search query derived from claim text.
        max_results: Maximum videos to return (capped at 5).
        published_after: ISO 8601 date filter (e.g. "2025-01-01T00:00:00Z").

    Returns:
        List of video dicts with: video_id, title, description, channel_name,
        channel_id, publish_date, video_url, thumbnail_url.
        Empty list if API key missing, quota exceeded, or error.
    """
    api_key = settings.YOUTUBE_API_KEY
    if not api_key:
        logger.debug("[YOUTUBE] No API key configured — skipping video search")
        return []

    max_results = min(max_results, 5)

    params: Dict[str, Any] = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "maxResults": max_results,
        "order": "relevance",
        "safeSearch": "none",
        "key": api_key,
    }
    if published_after:
        params["publishedAfter"] = published_after

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(YOUTUBE_SEARCH_URL, params=params)

            if resp.status_code == 403:
                logger.warning("[YOUTUBE] Quota exceeded or forbidden — skipping")
                return []
            resp.raise_for_status()

            data = resp.json()
            items = data.get("items", [])

            videos = []
            video_ids = []
            for item in items:
                snippet = item.get("snippet", {})
                vid_id = item.get("id", {}).get("videoId")
                if not vid_id:
                    continue

                video_ids.append(vid_id)
                videos.append(
                    {
                        "video_id": vid_id,
                        "title": snippet.get("title", ""),
                        "description": snippet.get("description", ""),
                        "channel_name": snippet.get("channelTitle", ""),
                        "channel_id": snippet.get("channelId"),
                        "publish_date": _parse_youtube_date(snippet.get("publishedAt")),
                        "video_url": f"https://www.youtube.com/watch?v={vid_id}",
                        "thumbnail_url": _best_thumbnail(snippet.get("thumbnails", {})),
                    }
                )

            # Fetch durations from videos endpoint
            if video_ids:
                durations = await _fetch_durations(client, video_ids, api_key)
                for v in videos:
                    v["duration"] = durations.get(v["video_id"])

            logger.info(f"[YOUTUBE] Found {len(videos)} videos for query: {query[:60]}")
            return videos

    except httpx.TimeoutException:
        logger.warning("[YOUTUBE] Request timed out")
        return []
    except httpx.HTTPStatusError as e:
        logger.warning(f"[YOUTUBE] HTTP error {e.response.status_code}")
        return []
    except Exception as e:
        logger.warning(f"[YOUTUBE] Unexpected error: {e}")
        return []


async def _fetch_durations(
    client: httpx.AsyncClient, video_ids: List[str], api_key: str
) -> Dict[str, Optional[str]]:
    """Fetch video durations from the videos endpoint."""
    try:
        resp = await client.get(
            YOUTUBE_VIDEOS_URL,
            params={
                "part": "contentDetails",
                "id": ",".join(video_ids),
                "key": api_key,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            item["id"]: item.get("contentDetails", {}).get("duration")
            for item in data.get("items", [])
        }
    except Exception as e:
        logger.debug(f"[YOUTUBE] Failed to fetch durations: {e}")
        return {}


def _parse_youtube_date(date_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO 8601 date from YouTube API."""
    if not date_str:
        return None
    try:
        # YouTube returns "2026-02-14T18:30:00Z"
        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _best_thumbnail(thumbnails: Dict[str, Any]) -> Optional[str]:
    """Pick the best available thumbnail URL."""
    for key in ("high", "medium", "default"):
        thumb = thumbnails.get(key)
        if thumb and thumb.get("url"):
            return thumb["url"]
    return None
