import re
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class ClaimClassifier:
    """Classify claims by type and verifiability"""

    def __init__(self):
        # Opinion indicators
        self.opinion_patterns = [
            r"\b(i think|i believe|in my opinion|i feel|seems like)\b",
            r"\b(people think|some think|experts believe|many believe)\b",  # Third-person opinions
            r"\b(beautiful|ugly|amazing|terrible|best|worst)\b",
            r"\b(should|ought to|must|need to)\b"  # Normative
        ]

        # Prediction indicators
        self.prediction_patterns = [
            r"\b(will|going to|predict|forecast|expect)\b",
            r"\b(in the future|next year|by 20\d{2})\b"
        ]

        # Personal experience indicators
        self.personal_patterns = [
            r"\b(i saw|i heard|i experienced|happened to me)\b"
        ]

        # Legal claim indicators (patterns match against lowercased text)
        self.legal_patterns = [
            r"\b(19\d{2}|20\d{2})\s+(\w+\s+){0,5}(law|statute|act|legislation|bill)\b",  # "1964 Civil Rights Act" or "1952 federal law"
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

        # NEW: Domain detection with spaCy (lazy loaded for Phase 5: Government API Integration)
        self.nlp = None  # Lazy load only when ENABLE_API_RETRIEVAL=True

        # Domain classification keywords and scoring
        self.domain_keywords = {
            "Finance": {
                "keywords": ["unemployment", "gdp", "inflation", "economy", "market", "stock",
                           "interest", "fiscal", "monetary", "treasury", "growth", "recession"],
                "entities": ["MONEY", "PERCENT"],
                "orgs": ["ons", "fed", "treasury", "bank of england", "federal reserve"]
            },
            "Health": {
                "keywords": ["health", "medical", "disease", "vaccine", "hospital", "doctor",
                           "patient", "treatment", "covid", "pandemic", "nhs", "medicine"],
                "entities": [],
                "orgs": ["nhs", "who", "cdc", "nihr", "world health"]
            },
            "Government": {
                "keywords": ["company", "business", "corporation", "registered", "director",
                           "filing", "incorporation", "shareholder"],
                "entities": ["ORG"],
                "orgs": ["companies house"]
            },
            "Climate": {
                "keywords": ["climate", "temperature", "weather", "carbon", "emissions",
                           "greenhouse", "warming", "celsius", "fahrenheit"],
                "entities": [],
                "orgs": ["met office", "noaa"]
            },
            "Demographics": {
                "keywords": ["population", "census", "demographic", "people", "household",
                           "birth", "death", "migration", "ethnicity"],
                "entities": [],
                "orgs": ["ons", "census"]
            },
            "Science": {
                "keywords": ["research", "study", "journal", "science", "experiment",
                           "peer-review", "publication", "findings", "paper"],
                "entities": [],
                "orgs": ["pubmed", "nature", "science"]
            },
            "Law": {
                "keywords": ["statute", "regulation", "act", "bill", "court", "ruling",
                           "section", "subsection", "amended", "legislation"],
                "entities": ["LAW"],
                "orgs": ["parliament", "congress", "supreme court"]
            }
        }

    def classify(self, claim_text: str) -> Dict[str, Any]:
        """Classify claim type and assess verifiability"""
        claim_lower = claim_text.lower()

        # Check for legal claims FIRST (statutes, laws, regulations)
        # Legal claims take precedence over opinion/normative language
        if any(re.search(pattern, claim_lower) for pattern in self.legal_patterns):
            metadata = self._extract_legal_metadata(claim_text, claim_lower)
            return {
                "claim_type": "legal",
                "is_verifiable": True,
                "reason": "This claim references legal statutes, laws, or regulations that can be verified",
                "confidence": 0.9,
                "metadata": metadata
            }

        # Check for opinion
        if any(re.search(pattern, claim_lower) for pattern in self.opinion_patterns):
            return {
                "claim_type": "opinion",
                "is_verifiable": False,
                "reason": "This appears to be a subjective opinion or value judgment",
                "confidence": 0.85
            }

        # Check for prediction
        if any(re.search(pattern, claim_lower) for pattern in self.prediction_patterns):
            return {
                "claim_type": "prediction",
                "is_verifiable": False,  # Can't verify future
                "reason": "This is a prediction about future events",
                "confidence": 0.8,
                "note": "We can assess the basis for the prediction, but cannot verify its truth"
            }

        # Check for personal experience
        if any(re.search(pattern, claim_lower) for pattern in self.personal_patterns):
            return {
                "claim_type": "personal_experience",
                "is_verifiable": False,
                "reason": "This is a personal experience that cannot be externally verified",
                "confidence": 0.75
            }

        # Default: factual claim
        return {
            "claim_type": "factual",
            "is_verifiable": True,
            "reason": "This appears to be a factual claim that can be verified",
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

    # ========== NEW METHODS FOR DOMAIN DETECTION (Phase 5: Government API Integration) ==========

    def detect_domain(self, claim_text: str) -> Dict[str, Any]:
        """
        NEW METHOD: Detect domain for API routing using spaCy NER

        Returns:
            {
                "domain": str,  # Finance, Health, Government, etc.
                "domain_confidence": float,  # 0-1
                "jurisdiction": str,  # UK, US, EU, Global
                "key_entities": List[str]
            }
        """
        # Early return for empty or whitespace-only claims
        if not claim_text or not claim_text.strip():
            return {
                "domain": "General",
                "domain_confidence": 0.0,
                "jurisdiction": "Global",
                "key_entities": []
            }

        # Lazy load spaCy only when needed
        if self.nlp is None:
            self._load_spacy()

        try:
            doc = self.nlp(claim_text)

            # Extract entities
            entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents]

            # Score each domain
            domain, confidence = self._score_domains(claim_text, entities)

            # Detect jurisdiction
            jurisdiction = self._detect_jurisdiction(claim_text, doc)

            return {
                "domain": domain,
                "domain_confidence": confidence,
                "jurisdiction": jurisdiction,
                "key_entities": [ent.text for ent in doc.ents]
            }
        except Exception as e:
            logger.error(f"Domain detection failed: {e}", exc_info=True)
            # Fallback to General domain
            return {
                "domain": "General",
                "domain_confidence": 0.1,
                "jurisdiction": "Global",
                "key_entities": []
            }

    def _load_spacy(self):
        """Lazy load spaCy model with custom patterns"""
        try:
            import spacy

            self.nlp = spacy.load("en_core_web_sm")

            # Add custom entity ruler for domain-specific entities
            if "entity_ruler" not in self.nlp.pipe_names:
                ruler = self.nlp.add_pipe("entity_ruler", before="ner")

                patterns = [
                    # Government/Companies
                    {"label": "ORG", "pattern": [{"LOWER": "companies"}, {"LOWER": "house"}]},
                    {"label": "ORG", "pattern": [{"LOWER": "nhs"}]},
                    {"label": "ORG", "pattern": [{"LOWER": "ons"}]},
                    {"label": "ORG", "pattern": [{"LOWER": "met"}, {"LOWER": "office"}]},

                    # Health organizations
                    {"label": "ORG", "pattern": [{"LOWER": "who"}]},
                    {"label": "ORG", "pattern": [{"LOWER": "cdc"}]},
                    {"label": "ORG", "pattern": [{"LOWER": "world"}, {"LOWER": "health"}]},

                    # Financial terms
                    {"label": "FINANCIAL", "pattern": [{"LOWER": "gdp"}]},
                    {"label": "FINANCIAL", "pattern": [{"LOWER": "unemployment"}]},
                    {"label": "FINANCIAL", "pattern": [{"LOWER": "inflation"}]},

                    # Climate terms
                    {"label": "CLIMATE", "pattern": [{"LOWER": "carbon"}, {"LOWER": "emissions"}]},
                ]

                ruler.add_patterns(patterns)

            logger.info("spaCy model loaded for domain detection")

        except OSError:
            logger.error("spaCy model not found. Run: python -m spacy download en_core_web_sm")
            raise
        except Exception as e:
            logger.error(f"Failed to load spaCy: {e}", exc_info=True)
            raise

    def _score_domains(self, claim_text: str, entities: List[Dict]) -> tuple:
        """
        Score each domain and return highest with confidence

        Scoring system:
        - Keyword match: +1 point each
        - Entity match: +2 points each
        - Organization match: +3 points each
        """
        claim_lower = claim_text.lower()
        scores = {domain: 0 for domain in self.domain_keywords}

        for domain, config in self.domain_keywords.items():
            # Check keywords (+1 point each)
            for keyword in config["keywords"]:
                if keyword in claim_lower:
                    scores[domain] += 1

            # Check entities (+2 points each)
            for entity in entities:
                if entity["label"] in config["entities"]:
                    scores[domain] += 2

            # Check organizations (+3 points each)
            for entity in entities:
                if entity["label"] == "ORG":
                    entity_text_lower = entity["text"].lower()
                    if any(org in entity_text_lower for org in config["orgs"]):
                        scores[domain] += 3

        # Get highest scoring domain
        max_domain = max(scores, key=scores.get)
        max_score = scores[max_domain]

        # Calculate confidence (0-1 scale)
        # 0 points = 0.1 confidence (General)
        # 5+ points = 0.9 confidence
        confidence = min(0.1 + (max_score * 0.15), 0.95)

        if max_score == 0:
            return "General", 0.1

        return max_domain, confidence

    def _detect_jurisdiction(self, claim_text: str, doc) -> str:
        """
        Detect jurisdiction from text and entities.

        Priority order:
        1. Organization entities (highest signal)
        2. Explicit location indicators
        3. GPE entities
        4. Default to Global
        """
        claim_lower = claim_text.lower()

        # Extract all entities for checking
        entities_lower = [ent.text.lower() for ent in doc.ents]

        # PRIORITY 1: Organization-based jurisdiction (strongest signal)
        # These organizations are definitively tied to specific jurisdictions
        uk_orgs = ["ons", "nhs", "companies house", "met office", "uk parliament",
                   "bank of england", "fca", "hmrc", "ofsted"]
        us_orgs = ["federal reserve", "fed", "cdc", "fda", "congress",
                   "supreme court", "irs", "sec", "epa"]

        for org in uk_orgs:
            if org in claim_lower or org in entities_lower:
                return "UK"

        for org in us_orgs:
            if org in claim_lower or org in entities_lower:
                return "US"

        # PRIORITY 2: Explicit location indicators
        # UK indicators
        uk_indicators = ["uk", "britain", "british", "united kingdom",
                         "westminster", "england", "scotland", "wales", "northern ireland"]
        if any(ind in claim_lower for ind in uk_indicators):
            return "UK"

        # US indicators
        us_indicators = ["usa", "america", "american", "united states",
                        "senate", "house of representatives", "washington dc"]
        if any(ind in claim_lower for ind in us_indicators):
            return "US"

        # EU indicators
        eu_indicators = ["eu", "european union", "brussels", "european commission",
                        "eurozone", "european central bank", "ecb"]
        if any(ind in claim_lower for ind in eu_indicators):
            return "EU"

        # PRIORITY 3: Check GPE (Geo-Political Entity) entities
        for ent in doc.ents:
            if ent.label_ == "GPE":
                ent_text = ent.text.lower()
                if ent_text in ["uk", "britain", "england", "scotland", "wales", "northern ireland"]:
                    return "UK"
                if ent_text in ["us", "usa", "america", "united states"]:
                    return "US"
                if ent_text in ["eu", "europe"]:
                    return "EU"

        # PRIORITY 4: Default to Global
        return "Global"

    def get_classification_summary(self, claims: list[Dict[str, Any]]) -> Dict[str, Any]:
        """Get summary statistics for a batch of classified claims"""
        total = len(claims)
        if total == 0:
            return {
                "total_claims": 0,
                "verifiable": 0,
                "non_verifiable": 0,
                "types": {}
            }

        verifiable_count = sum(1 for c in claims if c.get("is_verifiable", True))
        type_counts = {}

        for claim in claims:
            classification = claim.get("classification", {})
            claim_type = classification.get("claim_type", "factual")
            type_counts[claim_type] = type_counts.get(claim_type, 0) + 1

        return {
            "total_claims": total,
            "verifiable": verifiable_count,
            "non_verifiable": total - verifiable_count,
            "verifiable_percentage": round((verifiable_count / total) * 100, 1),
            "types": type_counts
        }
