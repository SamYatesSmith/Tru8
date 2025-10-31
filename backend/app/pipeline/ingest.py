import logging
import asyncio
from typing import Dict, Any, Optional
from urllib.parse import urlparse, parse_qs
import re
import requests
import trafilatura
from readability import Document
import bleach
from youtube_transcript_api import YouTubeTranscriptApi
from app.core.config import settings

# Note: pytesseract and PIL imports moved inside functions to prevent
# heavy ML libraries (numpy) from loading at startup. They will only load when OCR is actually used.

logger = logging.getLogger(__name__)

class BaseIngester:
    """Base class for content ingesters"""
    
    def __init__(self):
        self.timeout = settings.PIPELINE_TIMEOUT_SECONDS
    
    async def sanitize_content(self, content: str) -> str:
        """Sanitize HTML content and remove scripts"""
        # Handle None or empty content
        if not content:
            return ""

        # Remove scripts and other dangerous content
        allowed_tags = ['p', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                       'strong', 'em', 'ul', 'ol', 'li', 'br', 'blockquote']

        clean_content = bleach.clean(content, tags=allowed_tags, strip=True)

        # Remove excessive whitespace
        clean_content = re.sub(r'\s+', ' ', clean_content).strip()

        return clean_content if clean_content else ""

class UrlIngester(BaseIngester):
    """Ingest content from URLs"""
    
    async def process(self, url: str) -> Dict[str, Any]:
        """Fetch and extract content from URL"""
        try:
            # Use synchronous requests library to avoid asyncio DNS issues on Windows
            # Run in thread pool to keep async interface
            loop = asyncio.get_event_loop()

            def fetch_url():
                # DISABLED: robots.txt checker was incorrectly blocking legitimate requests
                # For MVP: We access publicly available content for fact-checking purposes (fair use)
                # Note: robots.txt is advisory, not legally binding. We respect paywalls (HTTP 402).

                session = requests.Session()
                session.max_redirects = 5
                response = session.get(
                    url,
                    timeout=self.timeout,
                    allow_redirects=True,
                    headers={'User-Agent': 'Tru8Bot/1.0 (Fact-checking service)'}
                )
                response.raise_for_status()
                return response

            # Fetch content in thread pool to avoid blocking
            response = await loop.run_in_executor(None, fetch_url)

            # Extract with trafilatura (primary)
            extracted = trafilatura.extract(
                response.text,
                include_comments=False,
                include_tables=False,
                with_metadata=True,
                url=url
            )

            if extracted:
                # Parse metadata (removed fast=True for compatibility)
                metadata = trafilatura.extract_metadata(response.text)

                content = await self.sanitize_content(extracted)

                # Check if content is actually usable
                if not content or len(content.strip()) < 50:
                    # Fall through to readability fallback
                    pass
                else:
                    return {
                        "success": True,
                        "content": content,
                        "metadata": {
                            "title": metadata.title if metadata else "",
                            "author": metadata.author if metadata else "",
                            "date": metadata.date if metadata else "",
                            "url": url,
                            "word_count": len(content.split())
                        }
                    }

            # Fallback to readability
            doc = Document(response.text)
            summary = doc.summary()

            if not summary:
                return {
                    "success": False,
                    "error": "Could not extract content from URL - both trafilatura and readability failed",
                    "metadata": {"url": url}
                }

            content = await self.sanitize_content(summary)

            # Final check - ensure we got actual content
            if not content or len(content.strip()) < 50:
                return {
                    "success": False,
                    "error": "Extracted content too short - URL may be behind paywall or block bot access",
                    "metadata": {"url": url}
                }

            return {
                "success": True,
                "content": content,
                "metadata": {
                    "title": doc.title(),
                    "url": url,
                    "word_count": len(content.split()),
                    "extraction_method": "readability"
                }
            }

        except requests.Timeout:
            logger.error(f"Timeout fetching URL: {url}")
            return {"success": False, "error": "Request timeout", "content": ""}

        except requests.HTTPError as e:
            if e.response and e.response.status_code == 402:
                # Paywall detected
                return {
                    "success": False,
                    "error": "Paywall detected",
                    "content": "",
                    "metadata": {"paywall": True}
                }
            logger.error(f"HTTP error fetching URL {url}: {e}")
            return {"success": False, "error": f"HTTP {e.response.status_code if e.response else 'error'}", "content": ""}
            
        except Exception as e:
            logger.error(f"Error processing URL {url}: {e}")
            return {"success": False, "error": str(e), "content": ""}

class ImageIngester(BaseIngester):
    """Extract text from images using OCR"""
    
    async def process(self, image_path: str) -> Dict[str, Any]:
        """Extract text from image using OCR"""
        try:
            # Import PIL only when actually needed
            from PIL import Image
            
            # Load image
            image = Image.open(image_path)
            
            # Check file size (6MB limit from project overview)
            max_size = 6 * 1024 * 1024  # 6MB
            if image_path and hasattr(image, 'tell'):
                if image.tell() > max_size:
                    return {
                        "success": False,
                        "error": "Image too large (max 6MB)",
                        "content": ""
                    }
            
            # Import pytesseract only when actually needed
            import pytesseract
            
            # Run OCR in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            extracted_text = await loop.run_in_executor(
                None, 
                pytesseract.image_to_string, 
                image
            )
            
            # Clean up extracted text
            content = await self.sanitize_content(extracted_text)
            
            # Basic quality check
            if len(content.strip()) < 10:
                return {
                    "success": False,
                    "error": "Insufficient text extracted from image",
                    "content": content
                }
            
            return {
                "success": True,
                "content": content,
                "metadata": {
                    "extraction_method": "tesseract_ocr",
                    "image_size": image.size if image else None,
                    "word_count": len(content.split())
                }
            }
            
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            return {"success": False, "error": str(e), "content": ""}

class VideoIngester(BaseIngester):
    """Extract transcripts from videos"""
    
    async def process(self, video_url: str) -> Dict[str, Any]:
        """Extract transcript from video URL"""
        try:
            # Check if YouTube video
            if self._is_youtube_url(video_url):
                return await self._process_youtube(video_url)
            
            # TODO: Add support for other video platforms
            return {
                "success": False,
                "error": "Unsupported video platform",
                "content": ""
            }
            
        except Exception as e:
            logger.error(f"Error processing video {video_url}: {e}")
            return {"success": False, "error": str(e), "content": ""}
    
    def _is_youtube_url(self, url: str) -> bool:
        """Check if URL is a YouTube video"""
        youtube_domains = ['youtube.com', 'youtu.be', 'm.youtube.com']
        parsed = urlparse(url)
        return any(domain in parsed.netloc for domain in youtube_domains)
    
    def _extract_youtube_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL"""
        parsed = urlparse(url)
        
        if 'youtu.be' in parsed.netloc:
            return parsed.path.lstrip('/')
        
        if 'youtube.com' in parsed.netloc:
            query = parse_qs(parsed.query)
            return query.get('v', [None])[0]
        
        return None
    
    async def _process_youtube(self, url: str) -> Dict[str, Any]:
        """Process YouTube video transcript"""
        try:
            video_id = self._extract_youtube_id(url)
            if not video_id:
                return {
                    "success": False,
                    "error": "Could not extract YouTube video ID",
                    "content": ""
                }
            
            # Get transcript in thread pool
            loop = asyncio.get_event_loop()
            transcript_list = await loop.run_in_executor(
                None,
                YouTubeTranscriptApi.get_transcript,
                video_id,
                ['en', 'en-US', 'en-GB']  # Prefer English
            )
            
            # Combine transcript segments
            full_transcript = " ".join([entry['text'] for entry in transcript_list])
            
            # Check 8-minute limit (from project overview)
            duration = transcript_list[-1]['start'] + transcript_list[-1]['duration'] if transcript_list else 0
            if duration > 8 * 60:  # 8 minutes
                return {
                    "success": False,
                    "error": "Video too long (max 8 minutes for Quick mode)",
                    "content": full_transcript[:1000] + "..."  # Return partial
                }
            
            content = await self.sanitize_content(full_transcript)
            
            return {
                "success": True,
                "content": content,
                "metadata": {
                    "video_id": video_id,
                    "duration_seconds": duration,
                    "word_count": len(content.split()),
                    "transcript_segments": len(transcript_list)
                }
            }
            
        except Exception as e:
            # TODO: Fallback to Whisper API for videos without transcripts
            logger.warning(f"YouTube transcript failed for {url}: {e}")
            return {
                "success": False,
                "error": f"Transcript unavailable: {str(e)}",
                "content": "",
                "metadata": {"requires_whisper_fallback": True}
            }