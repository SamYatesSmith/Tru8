"""Evidence Classifier — batched LLM classification of evidence tier and type.

Assigns Tier (proximity to original information) and Type (nature of content)
to each evidence item. Uses a single batched LLM call per batch of up to 30 items,
with a heuristic fallback for failures.

Philosophy (locked 2026-02-16):
  Classify, don't score. Tier + Type, not credibility numbers.
  A Tier 1 government dataset from a questionable government is still "primary".
  A BBC opinion column is still "commentary". The tier describes proximity, not quality.

Canonical doc: audit/pipeline-issues/fireside_discussion.md
"""

import json
import logging
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

import httpx

from app.core.config import settings
from app.services.google_ai import call_google_ai, call_google_ai_with_usage

logger = logging.getLogger(__name__)

# ── Valid classification values ────────────────────────────────────────────

VALID_TIERS = {"primary", "reporting", "commentary"}
VALID_TYPES = {
    "data",
    "official_statement",
    "news_reporting",
    "analysis",
    "opinion",
    "academic",
}

DEFAULT_TIER = "commentary"
DEFAULT_TYPE = "news_reporting"

BATCH_SIZE = 30

# ── Classification prompt ──────────────────────────────────────────────────

CLASSIFICATION_SYSTEM_PROMPT = """\
You are an evidence classification engine. You assign two labels to each evidence item:

**Tier** — proximity to the original information:
- primary: The thing itself. Government data, official statements, court filings, \
original research, raw statistics, primary documents, datasets.
- reporting: Someone investigated, interviewed, verified. News organisations, \
investigative outlets, specialist correspondents, field reporting.
- commentary: Interpretation of primary sources or reporting. Op-eds, analysis, \
editorials, blog posts, think-tank output.

Tier describes proximity, NOT quality. A government dataset from a questionable \
government is still "primary". A BBC opinion column is still "commentary".

**Type** — nature of the content:
- data: Numbers, datasets, measurements
- official_statement: Press releases, government communications
- news_reporting: Event coverage, investigation
- analysis: In-depth contextual pieces, explainers
- opinion: Stated perspective, editorials
- academic: Peer-reviewed, studies

Rules:
- Every item MUST get exactly one tier and one type.
- Use the evidence title, source/domain, URL, and snippet to determine classification.
- If uncertain, prefer the more conservative label (closer to primary, closer to data).
"""

CLASSIFICATION_USER_PROMPT = """\
Classify each evidence item below by tier and type.

{evidence_text}

Respond with JSON only:
{{
  "classifications": [
    {{"index": 0, "tier": "<primary|reporting|commentary>", "type": "<data|official_statement|news_reporting|analysis|opinion|academic>"}},
    ...
  ]
}}

Include one entry per evidence item. The index must match the item number above."""


# ── Heuristic patterns ────────────────────────────────────────────────────

_GOV_PATTERNS = re.compile(
    r"\.(gov|gov\.uk|parliament\.uk|congress\.gov|europa\.eu|govt\.nz|gc\.ca)"
    r"|whitehouse\.gov|govinfo\.gov|legislation\.gov\.uk"
    r"|bankofengland\.co\.uk|ecb\.europa\.eu|federalreserve\.gov"
    r"|supremecourt\.uk|sec\.gov|who\.int(?!/data)",
    re.IGNORECASE,
)

_ACADEMIC_PATTERNS = re.compile(
    r"\.(edu|ac\.uk|ac\.jp)"
    r"|pubmed\.ncbi|arxiv\.org|nature\.com|sciencedirect\.com"
    r"|springer\.com|wiley\.com|jstor\.org|ncbi\.nlm\.nih\.gov"
    r"|scholar\.google|thelancet\.com|jamanetwork\.com|science\.org"
    r"|ipcc\.ch|semanticscholar\.org|openalex\.org|academic\.oup\.com"
    r"|clinicaltrials\.gov|researchgate\.net|ssrn\.com|biorxiv\.org"
    r"|medrxiv\.org|pubs\.acs\.org|pmc\.ncbi|cell\.com|pnas\.org"
    r"|bmj\.com|frontiersin\.org|mdpi\.com|plos\.org|royalsocietypublishing\.org",
    re.IGNORECASE,
)

_WIRE_SERVICES = re.compile(
    # Wire services + major international news
    r"reuters\.com|apnews\.com|ap\.org|bbc\.co\.uk|bbc\.com"
    r"|theguardian\.com|nytimes\.com|washingtonpost\.com"
    r"|ft\.com|economist\.com|bloomberg\.com|cnbc\.com"
    # UK news
    r"|independent\.co\.uk|telegraph\.co\.uk|mirror\.co\.uk"
    r"|dailymail\.co\.uk|news\.sky\.com|channel4\.com|itv\.com"
    # US news
    r"|cnn\.com|foxnews\.com|nbcnews\.com|cbsnews\.com|abcnews\.go\.com"
    r"|npr\.org|usatoday\.com|latimes\.com|forbes\.com"
    # Tech news
    r"|techcrunch\.com|wired\.com|theverge\.com|arstechnica\.com"
    # International
    r"|aljazeera\.com|dw\.com|france24\.com|politico\.eu|politico\.com"
    # Sports news
    r"|espn\.com|skysports\.com|theathletic\.com"
    # Investigative
    r"|propublica\.org|bellingcat\.com|investigate-europe\.eu",
    re.IGNORECASE,
)

_DATA_PORTALS = re.compile(
    r"ons\.gov\.uk|bls\.gov|worldbank\.org|data\.who\.int"
    r"|fred\.stlouisfed\.org|data\.gov|eurostat\.ec"
    r"|stats\.oecd\.org|imf\.org"
    r"|ourworldindata\.org|data\.un\.org|census\.gov"
    r"|gbif\.org|ncei\.noaa\.gov|tidesandcurrents\.noaa\.gov"
    r"|england\.nhs\.uk|company-information\.service\.gov\.uk"
    r"|clinicaltrials\.gov|wikidata\.org",
    re.IGNORECASE,
)

# Think tanks and research institutes → commentary/analysis
_THINK_TANKS = re.compile(
    r"ifs\.org\.uk|chathamhouse\.org|brookings\.edu|rand\.org"
    r"|cfr\.org|piie\.com|rusi\.org|carnegieendowment\.org"
    r"|csis\.org|heritage\.org|urban\.org|aei\.org"
    r"|carbonbrief\.org",
    re.IGNORECASE,
)

# Blog and user-generated content platforms → commentary/opinion
_BLOG_PLATFORMS = re.compile(
    r"medium\.com|substack\.com|wordpress\.com|blogspot\.com" r"|tumblr\.com|ghost\.io",
    re.IGNORECASE,
)

# Social media → commentary/opinion
# Note: x.com needs boundary anchor to avoid matching vox.com, fox.com, etc.
_SOCIAL_MEDIA = re.compile(
    r"reddit\.com|(?:^|[/\.])x\.com|twitter\.com|facebook\.com"
    r"|tiktok\.com|instagram\.com|threads\.net",
    re.IGNORECASE,
)

# Magazines and opinion journals → commentary (opinion or analysis by title)
_MAGAZINES = re.compile(
    r"spectator\.co\.uk|newstatesman\.com|theatlantic\.com"
    r"|newyorker\.com|prospectmagazine\.co\.uk|slate\.com"
    r"|salon\.com|thenation\.com|theconversation\.com"
    r"|vox\.com",
    re.IGNORECASE,
)

# Fact-check / explainer outlets → reporting/analysis
_FACTCHECK_OUTLETS = re.compile(
    r"factcheck\.org|fullfact\.org|snopes\.com|politifact\.com",
    re.IGNORECASE,
)

# Reference platforms → commentary/analysis
_REFERENCE_PLATFORMS = re.compile(
    r"wikipedia\.org|youtube\.com|youtu\.be",
    re.IGNORECASE,
)

# Archive services — try to classify the underlying content
_ARCHIVE_SERVICES = re.compile(
    r"web\.archive\.org|archive\.org(?!/details)" r"|chroniclingamerica\.loc\.gov",
    re.IGNORECASE,
)

# B5b: Tabloid / speculative outlets that currently slip into wire-service
# classification but publish opinion and speculation as often as reporting.
# The quality floor forces these to commentary/opinion regardless of the
# LLM's content-based verdict. Aligned with "classify, don't score" — we're
# labelling honestly, not excluding.
_TABLOID_DOMAINS = re.compile(
    r"dailystar\.co\.uk|thesun\.co\.uk|mirror\.co\.uk"
    r"|nypost\.com|dailymail\.co\.uk|thedailybeast\.com"
    r"|rt\.com|sputniknews\.com",
    re.IGNORECASE,
)

# B5a: Joke / parody markers in arXiv titles or snippets. Conservative —
# only unambiguous signals. Catches cases like the K2-18b April Fool's
# paper "Evidence for THC and CBD in the Atmosphere of K2-18b".
_ARXIV_JOKE_MARKERS: Tuple[str, ...] = (
    "thc",
    "cbd",
    "tetrahydrocannabinol",
    "cannabidiol",
    "420 hours",
    "april fool",
    "april 1st",
    "april 1,",
    "alien invasion",
    "flat earth",
)

# Title-based markers for opinion content
_TITLE_OPINION_MARKERS = re.compile(
    r"\bopinion\b|\bop-ed\b|\beditorial\b|\bcolumn\b"
    r"|\bletter(?:s)? to the editor\b|\bmy view\b"
    r"|\bi think\b|\bi argue\b|\bi believe\b",
    re.IGNORECASE,
)

# Title-based markers for analysis content
_TITLE_ANALYSIS_MARKERS = re.compile(
    r"\banalysis\b|\bexplainer\b|\bexplained\b|\bin-depth\b"
    r"|\bbriefing(?:\s+note)?\b|\bassessment\b",
    re.IGNORECASE,
)


def _classify_heuristic(evidence: Dict[str, Any]) -> Tuple[str, str]:
    """Classify a single evidence item using URL/source pattern matching.

    Uses a cascade of URL patterns with title/snippet keyword refinement.
    Returns (tier, evidence_type) tuple.
    """
    url = evidence.get("url", "")
    source = evidence.get("source", evidence.get("domain", ""))
    title = evidence.get("title", "")
    combined = f"{url} {source} {title}".lower()

    # API adapter results — primary source; type depends on adapter
    provider = evidence.get("external_source_provider", "")
    if provider:
        _ACADEMIC_PROVIDERS = {"Semantic Scholar", "OpenAlex", "PubMed", "CrossRef"}
        if provider in _ACADEMIC_PROVIDERS:
            return ("primary", "academic")
        return ("primary", "data")

    # Fact-check articles (flag from pipeline) → reporting/analysis
    if evidence.get("is_factcheck"):
        return ("reporting", "analysis")

    # Data portals → primary/data (before gov — some are on .gov domains)
    if _DATA_PORTALS.search(url) or _DATA_PORTALS.search(source):
        return ("primary", "data")

    # Think tanks (before academic — some have .edu domains)
    if _THINK_TANKS.search(url) or _THINK_TANKS.search(source):
        return ("commentary", "analysis")

    # Academic sources → primary/academic (before gov — NIH/PubMed are on .gov)
    if _ACADEMIC_PATTERNS.search(url) or _ACADEMIC_PATTERNS.search(source):
        return ("primary", "academic")

    # Government sources → primary/official_statement
    if _GOV_PATTERNS.search(url) or _GOV_PATTERNS.search(source):
        return ("primary", "official_statement")

    # Archive services → primary/data (historical primary sources)
    if _ARCHIVE_SERVICES.search(url) or _ARCHIVE_SERVICES.search(source):
        return ("primary", "data")

    # Fact-check / explainer outlets → reporting/analysis
    if _FACTCHECK_OUTLETS.search(url) or _FACTCHECK_OUTLETS.search(source):
        return ("reporting", "analysis")

    # Major news organisations → reporting/news_reporting (with opinion/analysis override)
    if _WIRE_SERVICES.search(url) or _WIRE_SERVICES.search(source):
        if _TITLE_OPINION_MARKERS.search(combined):
            return ("commentary", "opinion")
        if _TITLE_ANALYSIS_MARKERS.search(combined):
            return ("commentary", "analysis")
        return ("reporting", "news_reporting")

    # Magazines → commentary (opinion default, analysis if title suggests it)
    if _MAGAZINES.search(url) or _MAGAZINES.search(source):
        if _TITLE_ANALYSIS_MARKERS.search(combined):
            return ("commentary", "analysis")
        return ("commentary", "opinion")

    # Blog platforms → commentary/opinion
    if _BLOG_PLATFORMS.search(url) or _BLOG_PLATFORMS.search(source):
        return ("commentary", "opinion")

    # Social media → commentary/opinion
    if _SOCIAL_MEDIA.search(url) or _SOCIAL_MEDIA.search(source):
        return ("commentary", "opinion")

    # Reference platforms (Wikipedia, YouTube) → commentary/analysis
    if _REFERENCE_PLATFORMS.search(url) or _REFERENCE_PLATFORMS.search(source):
        return ("commentary", "analysis")

    # --- Title/snippet keyword fallback (no URL match) ---
    # Check title for opinion markers
    if _TITLE_OPINION_MARKERS.search(title):
        return ("commentary", "opinion")

    # Check title for analysis markers
    if _TITLE_ANALYSIS_MARKERS.search(title):
        return ("commentary", "analysis")

    # Default → commentary/news_reporting
    return (DEFAULT_TIER, DEFAULT_TYPE)


def _high_confidence_override(evidence: Dict[str, Any]) -> Optional[Tuple[str, str]]:
    """Return (tier, type) only when URL identity is unambiguous.

    These are publisher-identity checks — sciencedirect.com IS an academic
    publisher, ons.gov.uk IS a government data portal. When the URL matches,
    the tier is structural fact, not interpretation. Returns None for
    sources where URL alone doesn't determine tier.
    """
    url = evidence.get("url", "")
    source = evidence.get("source", evidence.get("domain", ""))

    # API adapter results are always primary
    provider = evidence.get("external_source_provider", "")
    if provider:
        _ACADEMIC_PROVIDERS = {"Semantic Scholar", "OpenAlex", "PubMed", "CrossRef"}
        if provider in _ACADEMIC_PROVIDERS:
            return ("primary", "academic")
        return ("primary", "data")

    # Data portals before academic/gov (some overlap on .gov domains)
    if _DATA_PORTALS.search(url) or _DATA_PORTALS.search(source):
        return ("primary", "data")

    # Academic publishers → primary/academic
    if _ACADEMIC_PATTERNS.search(url) or _ACADEMIC_PATTERNS.search(source):
        return ("primary", "academic")

    # Government domains → primary/official_statement
    if _GOV_PATTERNS.search(url) or _GOV_PATTERNS.search(source):
        return ("primary", "official_statement")

    return None  # Not high-confidence — defer to LLM


def _arxiv_smell_test(evidence: Dict[str, Any]) -> Optional[str]:
    """B5a: detect parody / unvetted preprints on arXiv.

    arXiv is a preprint server with minimal vetting — satirical or joke
    papers appear annually (e.g. the K2-18b April Fool's "THC and CBD"
    paper). Without this check, the URL-identity override upgrades every
    arxiv.org item to primary/academic regardless of content.

    Returns an `exclusion_reason` string if hard joke markers are found —
    the caller should set `receipt_status="excluded"` and surface the
    receipt in the Librarian. For weak signals (single author, zero
    citations, no peer review), mutates the evidence item in place to
    demote to commentary/opinion and returns None.

    Conservative: only known joke vocabulary triggers exclusion. False
    positives here cost more than false negatives — a real paper
    dropped by accident is a quality loss.
    """
    url = (evidence.get("url") or "").lower()
    if "arxiv.org" not in url:
        return None

    title = (evidence.get("title") or "").lower()
    snippet = (evidence.get("snippet") or "").lower()
    text = f"{title} {snippet}"

    for marker in _ARXIV_JOKE_MARKERS:
        if marker in text:
            return f"arxiv_parody_smell_test:{marker}"

    # Weak-signal demotion: single-author + zero-citation arXiv items are
    # unvetted and often speculative. Keep them in the evidence set but
    # label honestly as commentary/opinion rather than primary/academic.
    metadata = evidence.get("metadata") or {}
    authors = metadata.get("authors") or []
    citations = metadata.get("citation_count") or 0
    if isinstance(authors, list) and len(authors) <= 1 and citations == 0:
        evidence["tier"] = "commentary"
        evidence["evidence_type"] = "opinion"
        evidence["classification_method"] = "arxiv_unvetted_demotion"

    return None


def _apply_quality_floor(evidence: Dict[str, Any]) -> Optional[str]:
    """B5b: force tabloid / social-media / blog items to commentary/opinion
    regardless of the LLM or URL-identity override verdict.

    The LLM can correctly read a tabloid's prose as "news-like" (since
    tabloid writing imitates reporting style), and so misclassify Daily
    Mail / Daily Star / Sun content as reporting/news_reporting. This
    floor is a last-pass override: if the URL is in a known opinion /
    social / speculation domain, label it honestly as commentary/opinion.

    Aligned with fireside-doc principle "classify, don't score" — we're
    labelling, not excluding. The item still appears in the evidence set.

    Returns the floor name if applied, else None.
    """
    url = evidence.get("url", "") or ""
    source = evidence.get("source", evidence.get("domain", "")) or ""

    if _TABLOID_DOMAINS.search(url) or _TABLOID_DOMAINS.search(source):
        evidence["tier"] = "commentary"
        evidence["evidence_type"] = "opinion"
        evidence["classification_method"] = "tabloid_floor"
        return "tabloid_floor"

    if _SOCIAL_MEDIA.search(url) or _SOCIAL_MEDIA.search(source):
        if evidence.get("tier") != "commentary":
            evidence["tier"] = "commentary"
            evidence["evidence_type"] = "opinion"
            evidence["classification_method"] = "social_media_floor"
            return "social_media_floor"

    if _BLOG_PLATFORMS.search(url) or _BLOG_PLATFORMS.search(source):
        if evidence.get("tier") != "commentary":
            evidence["tier"] = "commentary"
            evidence["evidence_type"] = "opinion"
            evidence["classification_method"] = "blog_platform_floor"
            return "blog_platform_floor"

    return None


# ── Evidence Classifier ───────────────────────────────────────────────────


class EvidenceClassifier:
    """Batched LLM classifier for evidence tier and type."""

    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.google_ai_api_key = getattr(settings, "GOOGLE_AI_API_KEY", "")
        self.model = getattr(settings, "LLM_MODEL_NAME", "gpt-4o-mini")
        self.google_model = getattr(
            settings, "GOOGLE_LLM_MODEL", "gemini-2.5-flash-lite"
        )
        self.timeout = 45
        self.snippet_length = 300
        self._token_usage = {"input_tokens": 0, "output_tokens": 0}

    def get_token_usage(self) -> Dict[str, int]:
        """Return accumulated token usage across all LLM calls."""
        return self._token_usage

    async def classify_batch(
        self, evidence_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Classify evidence items with tier and evidence_type.

        Returns the same list with 'tier' and 'evidence_type' fields added
        to each item. Items that already have both fields set are skipped.
        Never raises — always returns with at least heuristic classifications.

        Args:
            evidence_items: List of evidence dicts, each with at least
                title, url/source, and snippet/text fields.

        Returns:
            The same list with 'tier' and 'evidence_type' added to each item.
        """
        if not evidence_items:
            return evidence_items

        # Partition: items needing classification vs already classified
        needs_classification: List[int] = []
        for i, item in enumerate(evidence_items):
            if item.get("tier") and item.get("evidence_type"):
                # Already classified — skip
                continue
            needs_classification.append(i)

        if not needs_classification:
            logger.info(
                "[EVIDENCE_CLASSIFIER] All %d items already classified, skipping",
                len(evidence_items),
            )
            return evidence_items

        logger.info(
            "[EVIDENCE_CLASSIFIER] Classifying %d of %d evidence items",
            len(needs_classification),
            len(evidence_items),
        )

        # Process in batches of BATCH_SIZE
        items_to_classify = [evidence_items[i] for i in needs_classification]
        classified_results: List[Optional[Tuple[str, str]]] = [None] * len(
            items_to_classify
        )

        for batch_start in range(0, len(items_to_classify), BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, len(items_to_classify))
            batch = items_to_classify[batch_start:batch_end]

            llm_results = await self._classify_batch_llm(batch)

            if llm_results:
                for offset, result in enumerate(llm_results):
                    if result is not None:
                        classified_results[batch_start + offset] = result

        # Apply results: LLM where available, heuristic fallback otherwise.
        # High-confidence URL patterns (academic publishers, government domains,
        # data portals) override the LLM when it disagrees on tier — these are
        # publisher identity, not content interpretation.
        llm_count = 0
        heuristic_count = 0
        override_count = 0

        for list_offset, original_index in enumerate(needs_classification):
            item = evidence_items[original_index]
            result = classified_results[list_offset]

            if result is not None:
                tier, evidence_type = result
                item["classification_method"] = "llm"
                llm_count += 1

                # Check if a high-confidence URL pattern disagrees
                hc = _high_confidence_override(item)
                if hc and hc[0] != tier:
                    logger.info(
                        "[CLASSIFIER OVERRIDE] %s: LLM=%s/%s → %s/%s (URL identity)",
                        (item.get("url", ""))[:60],
                        tier,
                        evidence_type,
                        hc[0],
                        hc[1],
                    )
                    tier, evidence_type = hc
                    item["classification_method"] = "llm+override"
                    override_count += 1

                item["tier"] = tier
                item["evidence_type"] = evidence_type
            else:
                tier, evidence_type = _classify_heuristic(item)
                item["tier"] = tier
                item["evidence_type"] = evidence_type
                item["classification_method"] = "heuristic"
                heuristic_count += 1

        # B5a + B5b: post-classification quality pass.
        # Runs AFTER the LLM + URL-identity override so it can correct mislabels.
        # arXiv smell test runs first (may exclude); quality floor second
        # (demotes tabloid / social / blog content to commentary/opinion).
        arxiv_excluded_count = 0
        arxiv_demoted_count = 0
        quality_floor_count = 0
        for item in evidence_items:
            reason = _arxiv_smell_test(item)
            if reason:
                item["receipt_status"] = "excluded"
                item["exclusion_reason"] = reason
                arxiv_excluded_count += 1
                logger.info(
                    "[ARXIV SMELL] Excluded %s: %s",
                    (item.get("url") or "")[:60],
                    reason,
                )
            elif item.get("classification_method") == "arxiv_unvetted_demotion":
                arxiv_demoted_count += 1

            floor = _apply_quality_floor(item)
            if floor:
                quality_floor_count += 1
                logger.info(
                    "[QUALITY FLOOR] %s applied to %s",
                    floor,
                    (item.get("url") or "")[:60],
                )

        # Log summary
        tier_counts = Counter(item.get("tier", "unknown") for item in evidence_items)
        type_counts = Counter(
            item.get("evidence_type", "unknown") for item in evidence_items
        )

        logger.info(
            "[EVIDENCE_CLASSIFIER] Classification complete: "
            "%d LLM, %d heuristic, %d overrides, "
            "%d arxiv excluded, %d arxiv demoted, %d quality floor. "
            "Tiers: %s. Types: %s",
            llm_count,
            heuristic_count,
            override_count,
            arxiv_excluded_count,
            arxiv_demoted_count,
            quality_floor_count,
            dict(tier_counts),
            dict(type_counts),
        )

        return evidence_items

    # ── LLM batch classification ──────────────────────────────────────────

    async def _classify_batch_llm(
        self, batch: List[Dict[str, Any]]
    ) -> List[Optional[Tuple[str, str]]]:
        """Classify a batch of evidence items via LLM.

        Returns a list of (tier, type) tuples, one per item. Items that
        could not be classified are None.
        """
        # Build evidence text for prompt
        evidence_parts = []
        for i, item in enumerate(batch):
            title = item.get("title", "Untitled")[:200]
            source = item.get("source", item.get("domain", "Unknown"))[:100]
            url = item.get("url", "")[:200]
            snippet = (item.get("snippet", item.get("text", item.get("content", ""))))[
                : self.snippet_length
            ]

            evidence_parts.append(
                f"[{i}] Title: {title}\n"
                f"    Source: {source}\n"
                f"    URL: {url}\n"
                f"    Snippet: {snippet}"
            )

        evidence_text = "\n\n".join(evidence_parts)
        user_prompt = CLASSIFICATION_USER_PROMPT.format(evidence_text=evidence_text)

        parsed = await self._call_llm(user_prompt)

        if parsed is None:
            return [None] * len(batch)

        return self._parse_classification_response(parsed, len(batch))

    def _parse_classification_response(
        self,
        raw: Dict[str, Any],
        expected_count: int,
    ) -> List[Optional[Tuple[str, str]]]:
        """Parse LLM classification response into validated (tier, type) tuples."""
        results: List[Optional[Tuple[str, str]]] = [None] * expected_count

        if isinstance(raw, list):
            classifications = raw
        else:
            classifications = raw.get("classifications", [])

        if not classifications:
            # Search for any list value that looks like classifications
            for key, value in raw.items():
                if isinstance(value, list) and len(value) > 0:
                    if isinstance(value[0], dict) and (
                        "tier" in value[0] or "type" in value[0]
                    ):
                        classifications = value
                        break

        if not classifications:
            logger.warning(
                "[EVIDENCE_CLASSIFIER] No classifications found in LLM response"
            )
            return results

        for entry in classifications:
            if not isinstance(entry, dict):
                continue

            index = entry.get("index")
            if index is None or not isinstance(index, int):
                continue
            if index < 0 or index >= expected_count:
                continue

            tier = entry.get("tier", "").lower().strip()
            evidence_type = entry.get("type", "").lower().strip()

            # Validate tier
            if tier not in VALID_TIERS:
                logger.debug(
                    "[EVIDENCE_CLASSIFIER] Invalid tier '%s' at index %d, "
                    "defaulting to '%s'",
                    tier,
                    index,
                    DEFAULT_TIER,
                )
                tier = DEFAULT_TIER

            # Validate type
            if evidence_type not in VALID_TYPES:
                logger.debug(
                    "[EVIDENCE_CLASSIFIER] Invalid type '%s' at index %d, "
                    "defaulting to '%s'",
                    evidence_type,
                    index,
                    DEFAULT_TYPE,
                )
                evidence_type = DEFAULT_TYPE

            results[index] = (tier, evidence_type)

        classified_count = sum(1 for r in results if r is not None)
        logger.debug(
            "[EVIDENCE_CLASSIFIER] Parsed %d/%d classifications from LLM",
            classified_count,
            expected_count,
        )

        return results

    # ── LLM call (Google primary, OpenAI fallback) ────────────────────────

    async def _call_llm(self, user_prompt: str) -> Optional[Dict[str, Any]]:
        """Call LLM with Google primary, OpenAI fallback. Returns parsed JSON or None.

        Token usage is accumulated on ``self._token_usage``.
        """
        # Try Google first
        if self.google_ai_api_key:
            try:
                parsed, usage = await self._call_google(user_prompt)
                if parsed is not None:
                    self._accumulate(usage)
                    logger.info(
                        "[EVIDENCE_CLASSIFIER] Classification completed via Google Gemini"
                    )
                    return parsed
            except Exception as e:
                logger.warning(
                    "[EVIDENCE_CLASSIFIER] Google classification failed: %s", e
                )

        # Fall back to OpenAI
        if self.openai_api_key:
            try:
                parsed, usage = await self._call_openai(user_prompt)
                if parsed is not None:
                    self._accumulate(usage)
                    logger.info(
                        "[EVIDENCE_CLASSIFIER] Classification completed via OpenAI"
                    )
                    return parsed
            except Exception as e:
                logger.warning(
                    "[EVIDENCE_CLASSIFIER] OpenAI classification failed: %s", e
                )

        logger.error(
            "[EVIDENCE_CLASSIFIER] Both LLM providers failed for classification"
        )
        return None

    def _accumulate(self, usage: Optional[Dict[str, int]]) -> None:
        """Add usage to running total."""
        if usage:
            self._token_usage["input_tokens"] += usage.get("input_tokens", 0)
            self._token_usage["output_tokens"] += usage.get("output_tokens", 0)

    async def _call_google(self, user_prompt: str) -> tuple:
        """Classify via Google Gemini API."""
        full_prompt = f"{CLASSIFICATION_SYSTEM_PROMPT}\n\n{user_prompt}"
        return await call_google_ai_with_usage(
            full_prompt,
            temperature=0.1,
            max_tokens=4000,
            timeout=self.timeout,
            model=self.google_model,
        )

    async def _call_openai(self, user_prompt: str) -> tuple:
        """Classify via OpenAI API."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": CLASSIFICATION_SYSTEM_PROMPT,
                        },
                        {
                            "role": "user",
                            "content": user_prompt,
                        },
                    ],
                    "max_tokens": 4000,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
            )

        if response.status_code != 200:
            logger.error(
                "[EVIDENCE_CLASSIFIER] OpenAI API error: %d", response.status_code
            )
            return None, None

        result = response.json()
        content = result["choices"][0]["message"]["content"]
        usage_raw = result.get("usage", {})
        usage = {
            "input_tokens": usage_raw.get("prompt_tokens", 0),
            "output_tokens": usage_raw.get("completion_tokens", 0),
        }
        return json.loads(content), usage
