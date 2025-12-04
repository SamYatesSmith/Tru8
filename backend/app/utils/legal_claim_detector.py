"""
Legal Claim Detector

Simplified claim classification focused on legal claim detection and statute metadata extraction.
Used for routing claims to legal APIs (GovInfo, Congress.gov).

Opinion/prediction/personal experience detection removed - LLM extraction handles these.
"""

import re
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class LegalClaimDetector:
    """Detect legal claims and extract statute metadata for API routing"""

    def __init__(self):
        # Legal claim indicators (patterns match against lowercased text)
        self.legal_patterns = [
            r"\b(19\d{2}|20\d{2})\s+(\w+\s+){0,5}(law|statute|act|legislation|bill)\b",  # "1964 Civil Rights Act" or "1952 federal law"
            r"\b(law|statute|act|legislation|bill)\s+of\s+(19\d{2}|20\d{2})\b",  # "Act of 1966" or "Law of 2010"
            r"\b(\d+)\s+u\.?s\.?c\.?\s+§?\s*(\d+[a-z]?(?:-\d+)?)\b",  # "42 usc 1983"
            r"\b(ukpga|uksi|asp)\s+\d{4}/\d+\b",  # "ukpga 2010/15"
            r"\bsection\s+\d+[a-z]?\b",  # "section 230"
            r"\b(public\s+law|pub\.?\s*l\.?)\s+\d+-\d+\b",  # "public law 117-58"
            r"\b(h\.?r\.?|s\.?)\s+\d+\b",  # "h.r. 1234" or "s. 456"
            r"\b(amendment|constitutional|constitutional\s+law)\b",  # Constitutional references
            r"\b(supreme\s+court|circuit\s+court|federal\s+court)\s+(ruled|decision|case)\b",  # Court cases
            r"\bstatute\s+(requires|mandates|prohibits|allows)\b",  # Statute language
            r"\b(according\s+to|under|pursuant\s+to)\s+(\w+\s+){0,3}(law|statute|legislation)\b",  # Specific legal references
            r"\bthe\s+(\w+\s+){0,3}(law|statute|legislation)\s+(requires|mandates|prohibits|allows|states|says)\b",  # "the X law requires"
            r"\b(title\s+\d+|chapter\s+\d+)\b",  # "title 42", "chapter 7"
            r"\b(illegal|unlawful|lawful)\s+under\b",  # Legality under law
            r"\b(violates?|complies?\s+with)\s+(\w+\s+){0,3}(law|act|statute)\b"  # Compliance/violation
        ]

    def classify(self, claim_text: str) -> Dict[str, Any]:
        """
        Detect if claim is legal and extract metadata.

        Returns:
            Dict with:
            - claim_type: "legal" or "factual"
            - is_legal: True if legal claim detected
            - metadata: Legal citation metadata if legal
        """
        claim_lower = claim_text.lower()

        # Check for legal claims (statutes, laws, regulations)
        if any(re.search(pattern, claim_lower) for pattern in self.legal_patterns):
            metadata = self._extract_legal_metadata(claim_text, claim_lower)
            return {
                "claim_type": "legal",
                "is_legal": True,
                "reason": "This claim references legal statutes, laws, or regulations",
                "confidence": 0.9,
                "metadata": metadata
            }

        # Default: Not a legal claim (LLM handles other classification)
        return {
            "claim_type": "factual",
            "is_legal": False,
            "reason": "No legal statute references detected",
            "confidence": 0.7
        }

    def _extract_legal_metadata(self, original_text: str, lower_text: str) -> Dict[str, Any]:
        """Extract legal citation metadata from claim text"""
        metadata = {
            "citations": [],
            "jurisdiction": None,
            "year": None,
            "statute_type": None
        }

        # Extract US Code citations (42 USC §1983, 42 U.S.C. 1983)
        usc_pattern = r"(\d+)\s+U\.?S\.?C\.?\s+§?\s*(\d+[a-z]?(?:-\d+)?)"
        usc_matches = re.finditer(usc_pattern, original_text, re.IGNORECASE)
        for match in usc_matches:
            metadata["citations"].append({
                "type": "USC",
                "title": match.group(1),
                "section": match.group(2),
                "full_text": match.group(0)
            })
            metadata["jurisdiction"] = "US"
            metadata["statute_type"] = "federal"

        # Extract UK legislation citations (ukpga 2010/15, uksi 2010/15)
        uk_pattern = r"(ukpga|uksi|asp)\s+(\d{4})/(\d+)"
        uk_matches = re.finditer(uk_pattern, lower_text)
        for match in uk_matches:
            metadata["citations"].append({
                "type": match.group(1).upper(),
                "year": match.group(2),
                "number": match.group(3),
                "full_text": match.group(0)
            })
            metadata["jurisdiction"] = "UK"
            metadata["year"] = match.group(2)

        # Extract Public Law citations (Public Law 117-58, Pub. L. 117-58)
        pl_pattern = r"(Public\s+Law|Pub\.?\s*L\.?)\s+(\d+)-(\d+)"
        pl_matches = re.finditer(pl_pattern, original_text, re.IGNORECASE)
        for match in pl_matches:
            metadata["citations"].append({
                "type": "Public Law",
                "congress": match.group(2),
                "number": match.group(3),
                "full_text": match.group(0)
            })
            metadata["jurisdiction"] = "US"
            metadata["statute_type"] = "federal"

        # Extract bill references (H.R. 1234, S. 456)
        bill_pattern = r"(H\.?R\.?|S\.?)\s+(\d+)"
        bill_matches = re.finditer(bill_pattern, original_text, re.IGNORECASE)
        for match in bill_matches:
            metadata["citations"].append({
                "type": "Bill",
                "chamber": "House" if match.group(1).upper().startswith("H") else "Senate",
                "number": match.group(2),
                "full_text": match.group(0)
            })
            metadata["jurisdiction"] = "US"

        # Extract year from "1952 federal law" or "1964 Civil Rights Act" patterns
        year_pattern = r"\b(19\d{2}|20\d{2})\s+(\w+\s+){0,5}(law|statute|act|legislation)"
        year_match = re.search(year_pattern, lower_text)
        if year_match and not metadata["year"]:
            metadata["year"] = year_match.group(1)
            if "federal" in year_match.group(0) or not metadata["jurisdiction"]:
                metadata["jurisdiction"] = "US"

        # Extract year from "Act of 1966" or "Law of 2010" patterns (reverse order)
        if not metadata["year"]:
            year_reverse_pattern = r"\b(law|statute|act|legislation)\s+of\s+(19\d{2}|20\d{2})\b"
            year_reverse_match = re.search(year_reverse_pattern, lower_text)
            if year_reverse_match:
                metadata["year"] = year_reverse_match.group(2)
                if not metadata["jurisdiction"]:
                    metadata["jurisdiction"] = "US"  # Default to US for dated acts

        # Extract Title/Chapter references
        title_pattern = r"Title\s+(\d+)|Chapter\s+(\d+)"
        title_match = re.search(title_pattern, original_text, re.IGNORECASE)
        if title_match:
            if title_match.group(1):
                metadata["title"] = title_match.group(1)
            if title_match.group(2):
                metadata["chapter"] = title_match.group(2)

        # Detect jurisdiction from context if not already set
        if not metadata["jurisdiction"]:
            if re.search(r"\b(federal|congress|senate|house of representatives)\b", lower_text):
                metadata["jurisdiction"] = "US"
            elif re.search(r"\b(parliament|westminster|uk|british)\b", lower_text):
                metadata["jurisdiction"] = "UK"

        return metadata
