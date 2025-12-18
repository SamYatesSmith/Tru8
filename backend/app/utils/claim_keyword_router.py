"""
Claim Keyword Router

Detects domain-specific keywords in individual claim text and returns ADDITIONAL
adapters to query alongside existing article-level routing.

This is additive - keyword adapters are added to the existing domain-based adapter list,
not replacing them. Fast regex matching (~1ms per claim), no LLM calls.

Example:
    - Article domain: Politics
    - Claim: "Oil prices dropped 20%"
    - Keyword match: "oil" -> Alpha Vantage
    - Result: Politics adapters + Alpha Vantage
"""

import re
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class KeywordMatch:
    """Represents a keyword match with its associated adapter"""
    keyword: str
    pattern: str
    adapter_name: str
    confidence: float = 0.8


class ClaimKeywordRouter:
    """
    Detect keywords in claim text and return matching adapters.

    Singleton pattern - patterns compiled once at init, reused across claims.
    """

    # Keyword rules mapping patterns to adapter names
    # Format: adapter_name -> list of (pattern, keyword_description)
    # COMPREHENSIVE LIST - covers cross-domain claim scenarios
    KEYWORD_RULES: Dict[str, List[tuple]] = {

        # ============================================================
        # GovInfo.gov - US legislation, statutes, regulations, bills
        # ============================================================
        "GovInfo.gov": [
            # Named acts with years
            (r"\b(?:the\s+)?(?:\w+\s+){0,3}act\s+of\s+(?:19|20)\d{2}\b", "act of YYYY"),
            (r"\b(?:19|20)\d{2}\s+(?:\w+\s+){0,3}act\b", "YYYY act"),
            # Bill references
            (r"\bh\.?r\.?\s*\d+\b", "H.R. bill"),
            (r"\bs\.?\s*\d+\b", "S. bill"),
            (r"\bsenate\s+bill\b", "senate bill"),
            (r"\bhouse\s+bill\b", "house bill"),
            # Legal terms
            (r"\blegislation\b", "legislation"),
            (r"\bstatute\b", "statute"),
            (r"\bpublic\s+law\b", "public law"),
            (r"\bfederal\s+(?:law|regulation|rule|code)\b", "federal law"),
            (r"\bexecutive\s+order\b", "executive order"),
            (r"\bconstitutional(?:ly)?\b", "constitutional"),
            (r"\bamendment\b", "amendment"),
            (r"\b(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|fourteenth)\s+amendment\b", "amendment"),
            # Congress
            (r"\bcongress(?:ional|man|woman)?\b", "congress"),
            (r"\bsenator\b", "senator"),
            (r"\brepresentative\b", "representative"),
            # Regulatory
            (r"\bregulat(?:ion|ory|ed|or)\b", "regulation"),
            (r"\bcode\s+of\s+federal\s+regulations\b", "CFR"),
            (r"\bcfr\b", "CFR"),
            (r"\bu\.?s\.?c\.?\b", "USC"),
            # Legal actions
            (r"\bsigned\s+into\s+law\b", "signed into law"),
            (r"\bpassed\s+(?:by\s+)?(?:the\s+)?(?:house|senate|congress)\b", "passed by congress"),
            (r"\bvetoed?\b", "veto"),
            (r"\bbipartisan\b", "bipartisan"),
            (r"\bfilibuster\b", "filibuster"),
        ],

        # ============================================================
        # Alpha Vantage - Stocks, forex, crypto, commodities
        # ============================================================
        "Alpha Vantage": [
            # Oil & Gas
            (r"\b(?:crude\s+)?oil(?:\s+prices?)?\b", "oil"),
            (r"\bcrude\b", "crude"),
            (r"\bbrent\b", "brent"),
            (r"\bwti\b", "wti"),
            (r"\bpetroleum\b", "petroleum"),
            (r"\bnatural\s+gas\b", "natural gas"),
            (r"\bopec\b", "OPEC"),
            (r"\bbarrel(?:s)?\b", "barrel"),
            (r"\bgasoline\b", "gasoline"),
            (r"\bdiesel\b", "diesel"),
            (r"\bfuel\s+prices?\b", "fuel price"),
            # Precious metals
            (r"\bgold\s+(?:price|futures?|market)\b", "gold"),
            (r"\bsilver\s+(?:price|futures?|market)\b", "silver"),
            (r"\bplatinum\b", "platinum"),
            (r"\bpalladium\b", "palladium"),
            # Industrial metals
            (r"\bcopper\s+(?:price|futures?)\b", "copper"),
            (r"\baluminum\b", "aluminum"),
            (r"\bzinc\b", "zinc"),
            (r"\bnickel\b", "nickel"),
            (r"\biron\s+ore\b", "iron ore"),
            (r"\bsteel\s+(?:price|futures?)\b", "steel"),
            # Agricultural commodities
            (r"\bwheat\s+(?:price|futures?)\b", "wheat"),
            (r"\bcorn\s+(?:price|futures?)\b", "corn"),
            (r"\bsoybean\b", "soybean"),
            (r"\bcoffee\s+(?:price|futures?)\b", "coffee"),
            (r"\bcocoa\s+(?:price|futures?)\b", "cocoa"),
            (r"\bsugar\s+(?:price|futures?)\b", "sugar"),
            (r"\bcotton\s+(?:price|futures?)\b", "cotton"),
            (r"\blumber\s+(?:price|futures?)\b", "lumber"),
            # Stocks
            (r"\bstock\s+(?:price|market)\b", "stock"),
            (r"\bshare\s+(?:price|value)\b", "share price"),
            (r"\bequity\s+(?:market|prices?)\b", "equity"),
            (r"\bmarket\s+cap(?:italization)?\b", "market cap"),
            (r"\bearnings\s+(?:per\s+share|report)\b", "earnings"),
            (r"\bdividend\b", "dividend"),
            (r"\bipo\b", "IPO"),
            (r"\bstock\s+split\b", "stock split"),
            (r"\btrading\s+(?:volume|session)\b", "trading"),
            # Indices
            (r"\bnasdaq\b", "NASDAQ"),
            (r"\bdow\s+jones\b", "Dow Jones"),
            (r"\bs&p\s*500\b", "S&P 500"),
            (r"\bftse\s*(?:100|250)?\b", "FTSE"),
            (r"\bdax\b", "DAX"),
            (r"\bnikkei\b", "Nikkei"),
            (r"\bhang\s+seng\b", "Hang Seng"),
            (r"\bstoxx\b", "STOXX"),
            # Forex
            (r"\bforex\b", "forex"),
            (r"\bexchange\s+rate\b", "exchange rate"),
            (r"\bcurrency\s+(?:market|pair|exchange)\b", "currency"),
            (r"\bdollar\s+(?:to|vs|against|index)\b", "dollar"),
            (r"\beuro\s+(?:to|vs|against)\b", "euro"),
            (r"\bpound\s+(?:to|vs|against|sterling)\b", "pound"),
            (r"\byen\s+(?:to|vs|against)\b", "yen"),
            (r"\byuan\b", "yuan"),
            (r"\brenminbi\b", "renminbi"),
            # Crypto
            (r"\bbitcoin\b", "bitcoin"),
            (r"\bethereum\b", "ethereum"),
            (r"\bcrypto(?:currency|currencies)?\b", "crypto"),
            (r"\bblockchain\b", "blockchain"),
            (r"\baltcoin\b", "altcoin"),
            (r"\bdefi\b", "DeFi"),
            (r"\bnft\b", "NFT"),
            (r"\bdogecoin\b", "dogecoin"),
            (r"\bripple\b", "ripple"),
            (r"\blitecoin\b", "litecoin"),
        ],

        # ============================================================
        # FRED - US economic indicators and statistics
        # ============================================================
        "FRED": [
            # Employment
            (r"\bunemployment(?:\s+rate)?\b", "unemployment"),
            (r"\bjobless(?:ness)?\b", "jobless"),
            (r"\bjobs?\s+(?:report|growth|numbers?|added|lost|created)\b", "jobs"),
            (r"\blabor\s+(?:market|force|statistics|participation)\b", "labor"),
            (r"\bpayroll(?:s)?\b", "payroll"),
            (r"\bworkforce\b", "workforce"),
            (r"\bnonfarm\s+payrolls?\b", "nonfarm payrolls"),
            (r"\binitial\s+(?:jobless\s+)?claims\b", "jobless claims"),
            # GDP & Growth
            (r"\b(?:us\s+)?gdp\b", "GDP"),
            (r"\beconomic\s+growth\b", "economic growth"),
            (r"\brecession\b", "recession"),
            (r"\bexpansion\b", "expansion"),
            (r"\bcontraction\b", "contraction"),
            (r"\bquarterly\s+growth\b", "quarterly growth"),
            # Inflation
            (r"\binflation(?:\s+rate)?\b", "inflation"),
            (r"\bdeflation\b", "deflation"),
            (r"\bcpi\b", "CPI"),
            (r"\bconsumer\s+price(?:\s+index)?\b", "consumer price"),
            (r"\bppi\b", "PPI"),
            (r"\bproducer\s+price(?:\s+index)?\b", "producer price"),
            (r"\bcost\s+of\s+living\b", "cost of living"),
            (r"\bpurchasing\s+power\b", "purchasing power"),
            (r"\bcore\s+inflation\b", "core inflation"),
            (r"\bpce\b", "PCE"),
            # Interest rates & Fed
            (r"\binterest\s+rates?\b", "interest rate"),
            (r"\bfed(?:eral)?\s+(?:funds?|reserve)\b", "Fed"),
            (r"\bfed\s+(?:raised|cut|lowered|hiked|held)\b", "Fed policy"),
            (r"\bmonetary\s+policy\b", "monetary policy"),
            (r"\brate\s+(?:hike|cut|increase|decrease)\b", "rate change"),
            (r"\bfomc\b", "FOMC"),
            (r"\bquantitative\s+easing\b", "QE"),
            (r"\btapering\b", "tapering"),
            (r"\bbasis\s+points?\b", "basis points"),
            # Housing
            (r"\bhousing\s+(?:starts?|market|prices?|sales?)\b", "housing"),
            (r"\bhome\s+(?:sales?|prices?)\b", "home sales"),
            (r"\bmortgage\s+(?:rates?|applications?)\b", "mortgage"),
            (r"\breal\s+estate\s+(?:market|prices?)\b", "real estate"),
            # Trade
            (r"\btrade\s+(?:deficit|surplus|balance|gap)\b", "trade"),
            (r"\bimports?\b", "imports"),
            (r"\bexports?\b", "exports"),
            (r"\bcurrent\s+account\b", "current account"),
            # Debt
            (r"\bnational\s+debt\b", "national debt"),
            (r"\bfederal\s+debt\b", "federal debt"),
            (r"\bdebt\s+ceiling\b", "debt ceiling"),
            (r"\bdeficit\b", "deficit"),
            (r"\bbudget\s+(?:deficit|surplus)\b", "budget"),
            # Consumer
            (r"\bconsumer\s+(?:spending|confidence|sentiment)\b", "consumer"),
            (r"\bretail\s+sales\b", "retail sales"),
            (r"\bpersonal\s+(?:income|spending)\b", "personal income"),
            # Industrial
            (r"\bindustrial\s+production\b", "industrial production"),
            (r"\bmanufacturing\s+(?:index|output|pmi)\b", "manufacturing"),
            (r"\bpmi\b", "PMI"),
            (r"\bcapacity\s+utilization\b", "capacity utilization"),
        ],

        # ============================================================
        # PubMed - Medical research, health, diseases
        # ============================================================
        "PubMed": [
            # Research
            (r"\bclinical\s+trial\b", "clinical trial"),
            (r"\bstudy\s+(?:shows?|finds?|found|suggests?|reveals?)\b", "study"),
            (r"\bresearch(?:ers?)?\s+(?:shows?|finds?|found|suggests?)\b", "research"),
            (r"\bscientists?\s+(?:discovered?|found|say)\b", "scientists"),
            (r"\bpeer[- ]reviewed\b", "peer-reviewed"),
            (r"\bmeta[- ]analysis\b", "meta-analysis"),
            (r"\brandomized\s+(?:controlled\s+)?trial\b", "RCT"),
            (r"\bplacebo\b", "placebo"),
            (r"\bdouble[- ]blind\b", "double-blind"),
            # Vaccines & treatments
            (r"\bvaccine\b", "vaccine"),
            (r"\bvaccination\b", "vaccination"),
            (r"\bimmunization\b", "immunization"),
            (r"\btreatment\b", "treatment"),
            (r"\btherapy\b", "therapy"),
            (r"\bdrug\b", "drug"),
            (r"\bmedication\b", "medication"),
            (r"\bantibiotics?\b", "antibiotics"),
            (r"\bantiviral\b", "antiviral"),
            (r"\bchemotherapy\b", "chemotherapy"),
            (r"\bimmunotherapy\b", "immunotherapy"),
            (r"\bradiotherapy\b", "radiotherapy"),
            (r"\bsurgery\b", "surgery"),
            # Diseases - Major
            (r"\bdisease\b", "disease"),
            (r"\bcancer\b", "cancer"),
            (r"\btumou?r\b", "tumor"),
            (r"\bdiabetes\b", "diabetes"),
            (r"\bheart\s+(?:disease|attack|failure)\b", "heart disease"),
            (r"\bcardiovascular\b", "cardiovascular"),
            (r"\bstroke\b", "stroke"),
            (r"\balzheimer'?s?\b", "alzheimer's"),
            (r"\bdementia\b", "dementia"),
            (r"\bparkinson'?s?\b", "parkinson's"),
            (r"\bobesity\b", "obesity"),
            (r"\basthma\b", "asthma"),
            (r"\barthritis\b", "arthritis"),
            (r"\bosteoporosis\b", "osteoporosis"),
            (r"\bepilepsy\b", "epilepsy"),
            (r"\bmultiple\s+sclerosis\b", "multiple sclerosis"),
            (r"\bautoimmune\b", "autoimmune"),
            # Infectious diseases
            (r"\bcovid(?:-?19)?\b", "COVID"),
            (r"\bcoronavirus\b", "coronavirus"),
            (r"\bsars[- ]cov[- ]?2\b", "SARS-CoV-2"),
            (r"\binfluenza\b", "influenza"),
            (r"\bflu\s+(?:season|virus|vaccine|shot)\b", "flu"),
            (r"\bhiv\b", "HIV"),
            (r"\baids\b", "AIDS"),
            (r"\bmalaria\b", "malaria"),
            (r"\btuberculosis\b", "tuberculosis"),
            (r"\bhepatitis\b", "hepatitis"),
            (r"\bmeasles\b", "measles"),
            (r"\bpolio\b", "polio"),
            (r"\bebola\b", "ebola"),
            (r"\bzika\b", "zika"),
            (r"\bmpox\b", "mpox"),
            (r"\bvirus\b", "virus"),
            (r"\bbacteria\b", "bacteria"),
            (r"\binfection\b", "infection"),
            (r"\bpathogen\b", "pathogen"),
            (r"\boutbreak\b", "outbreak"),
            (r"\bepidemic\b", "epidemic"),
            (r"\bpandemic\b", "pandemic"),
            # Medical terms
            (r"\bsymptoms?\b", "symptoms"),
            (r"\bdiagnos(?:is|ed|tic)\b", "diagnosis"),
            (r"\bprognosis\b", "prognosis"),
            (r"\bmortality(?:\s+rate)?\b", "mortality"),
            (r"\bsurvival\s+rate\b", "survival rate"),
            (r"\bside\s+effects?\b", "side effects"),
            (r"\badverse\s+(?:events?|effects?|reactions?)\b", "adverse effects"),
            (r"\befficacy\b", "efficacy"),
            (r"\beffectiveness\b", "effectiveness"),
            (r"\bdosage\b", "dosage"),
            (r"\bdose\b", "dose"),
            # Mental health
            (r"\bdepression\b", "depression"),
            (r"\banxiety\b", "anxiety"),
            (r"\bmental\s+health\b", "mental health"),
            (r"\bschizophrenia\b", "schizophrenia"),
            (r"\bbipolar\b", "bipolar"),
            (r"\bptsd\b", "PTSD"),
            (r"\bsuicide\b", "suicide"),
            # Body systems
            (r"\bimmune\s+system\b", "immune system"),
            (r"\bnervous\s+system\b", "nervous system"),
            (r"\bdigestive\b", "digestive"),
            (r"\brespiratory\b", "respiratory"),
            (r"\bliver\b", "liver"),
            (r"\bkidney\b", "kidney"),
            (r"\blung\b", "lung"),
            (r"\bbrain\b", "brain"),
        ],

        # ============================================================
        # NOAA CDO - Climate data, weather records, natural disasters
        # ============================================================
        "NOAA CDO": [
            # Temperature records
            (r"\btemperature\s+record\b", "temperature record"),
            (r"\brecord\s+(?:high|low|hot|cold)\b", "record temperature"),
            (r"\bhottest\s+(?:day|month|year|summer|on\s+record)\b", "hottest"),
            (r"\bcoldest\s+(?:day|month|year|winter|on\s+record)\b", "coldest"),
            (r"\bwarmest\b", "warmest"),
            (r"\ball[- ]time\s+(?:high|low)\b", "all-time record"),
            (r"\bheat\s+(?:wave|record|index)\b", "heat"),
            # Climate
            (r"\bclimate\s+(?:change|data|record|crisis)\b", "climate"),
            (r"\bglobal\s+(?:warming|temperature)\b", "global warming"),
            (r"\bgreenhouse\s+gas(?:es)?\b", "greenhouse gas"),
            (r"\bcarbon\s+(?:emissions?|dioxide|footprint)\b", "carbon"),
            (r"\bco2\s+(?:levels?|emissions?|concentration)\b", "CO2"),
            (r"\bmethane\b", "methane"),
            # Sea & ice
            (r"\bsea\s+level\b", "sea level"),
            (r"\bice\s+(?:cap|sheet|melt)\b", "ice"),
            (r"\bglacier\b", "glacier"),
            (r"\barctic\b", "arctic"),
            (r"\bantarctic\b", "antarctic"),
            (r"\bpermafrost\b", "permafrost"),
            (r"\bocean\s+(?:temperature|warming|acidification)\b", "ocean"),
            # Precipitation
            (r"\bprecipitation\b", "precipitation"),
            (r"\brainfall\b", "rainfall"),
            (r"\bsnowfall\b", "snowfall"),
            (r"\binches\s+of\s+(?:rain|snow)\b", "precipitation"),
            # Natural disasters
            (r"\bhurricane\b", "hurricane"),
            (r"\btyphoon\b", "typhoon"),
            (r"\bcyclone\b", "cyclone"),
            (r"\btropical\s+storm\b", "tropical storm"),
            (r"\btornado\b", "tornado"),
            (r"\bflood(?:ing|waters?)?\b", "flood"),
            (r"\bdrought\b", "drought"),
            (r"\bwildfire\b", "wildfire"),
            (r"\bforest\s+fire\b", "forest fire"),
            (r"\bblizzard\b", "blizzard"),
            (r"\bheat\s*wave\b", "heatwave"),
            (r"\bcold\s+snap\b", "cold snap"),
            (r"\bel\s+ni[ñn]o\b", "El Nino"),
            (r"\bla\s+ni[ñn]a\b", "La Nina"),
            # Historical weather
            (r"\bhistoric(?:al)?\s+(?:weather|storm|flood|drought|temperatures?)\b", "historic weather"),
            (r"\bsince\s+records?\s+began\b", "since records began"),
        ],

        # ============================================================
        # ONS - UK economic statistics
        # ============================================================
        "ONS Economic Statistics": [
            (r"\buk\s+unemployment\b", "UK unemployment"),
            (r"\buk\s+gdp\b", "UK GDP"),
            (r"\buk\s+(?:economy|economic)\b", "UK economy"),
            (r"\buk\s+inflation\b", "UK inflation"),
            (r"\buk\s+(?:population|census)\b", "UK population"),
            (r"\buk\s+(?:trade|exports?|imports?)\b", "UK trade"),
            (r"\buk\s+(?:wages?|earnings?|income)\b", "UK wages"),
            (r"\buk\s+(?:housing|property)\s+(?:market|prices?)\b", "UK housing"),
            (r"\buk\s+retail\s+sales?\b", "UK retail"),
            (r"\buk\s+(?:jobs?|employment)\b", "UK employment"),
            (r"\bbritish\s+(?:economy|gdp|unemployment|inflation)\b", "British economy"),
            (r"\bbank\s+of\s+england\b", "Bank of England"),
            (r"\bsterling\b", "sterling"),
            (r"\bons\s+(?:data|statistics|figures?)\b", "ONS"),
        ],

        # ============================================================
        # Football-Data.org - Football/soccer statistics
        # ============================================================
        "Football-Data.org": [
            # Standings & tables
            (r"\bleague\s+(?:standings?|table|position)\b", "league table"),
            (r"\bpremier\s+league(?:\s+table)?\b", "Premier League"),
            (r"\bla\s+liga\b", "La Liga"),
            (r"\bbundesliga\b", "Bundesliga"),
            (r"\bserie\s+a\b", "Serie A"),
            (r"\bligue\s+1\b", "Ligue 1"),
            (r"\bchampions\s+league\b", "Champions League"),
            (r"\beuropa\s+league\b", "Europa League"),
            (r"\bworld\s+cup\b", "World Cup"),
            (r"\beuro\s+(?:20)?\d{2}\b", "Euros"),
            # Statistics
            (r"\btop\s+scor(?:er|ing)\b", "top scorer"),
            (r"\bgoal\s+scor(?:er|ing)\b", "goal scorer"),
            (r"\bgoals?\s+(?:scored|tally|record)\b", "goals"),
            (r"\bassists?\b", "assists"),
            (r"\bclean\s+sheets?\b", "clean sheets"),
            (r"\bpoints?\s+(?:tally|total|deduction)\b", "points"),
            (r"\bgoal\s+difference\b", "goal difference"),
            (r"\bwin(?:ning)?\s+streak\b", "winning streak"),
            (r"\bunbeaten\s+(?:run|streak)\b", "unbeaten"),
            # Match results
            (r"\bmatch\s+(?:result|score)\b", "match result"),
            (r"\bfootball\s+(?:results?|scores?|stats?)\b", "football"),
            (r"\bsoccer\s+(?:results?|scores?|stats?)\b", "soccer"),
            (r"\bfinal\s+score\b", "final score"),
        ],

        # ============================================================
        # Transfermarkt - Football transfers and valuations
        # ============================================================
        "Transfermarkt": [
            (r"\btransfer\s+(?:fee|window|market|deadline)\b", "transfer"),
            (r"\bsigned\s+(?:for|with|by)\b", "signed"),
            (r"\bmarket\s+value\b", "market value"),
            (r"\btransfer(?:red)?\s+(?:to|from)\b", "transferred"),
            (r"\b(?:million|billion)\s+(?:euro|pound|dollar)s?\s+(?:deal|transfer|fee|signing)\b", "transfer fee"),
            (r"\brelease\s+clause\b", "release clause"),
            (r"\bbuyout\s+clause\b", "buyout clause"),
            (r"\bcontract\s+(?:extension|renewal|expir(?:es|y)|length)\b", "contract"),
            (r"\bfree\s+(?:transfer|agent)\b", "free transfer"),
            (r"\bloan\s+(?:deal|move|spell)\b", "loan"),
            (r"\bworld\s+record\s+(?:fee|transfer|signing)\b", "record transfer"),
            (r"\brecord\s+signing\b", "record signing"),
        ],

        # ============================================================
        # WeatherAPI - Weather forecasts (current/future)
        # ============================================================
        "WeatherAPI": [
            (r"\bweather\s+(?:forecast|prediction|outlook)\b", "forecast"),
            (r"\btemperature\s+(?:tomorrow|today|tonight|this\s+week|next\s+week)\b", "temperature"),
            (r"\bwill\s+(?:rain|snow|storm|be\s+(?:hot|cold|sunny|cloudy))\b", "prediction"),
            (r"\bexpected\s+(?:rain|snow|weather|temperature|high|low)\b", "expected"),
            (r"\b(?:rain|snow|storms?|sunshine)\s+(?:is\s+)?(?:expected|forecast|predicted)\b", "expected weather"),
            (r"\bforecast(?:ed|s)?\s+(?:to|for|at)\b", "forecast"),
            (r"\bweather\s+(?:warning|alert|advisory)\b", "weather warning"),
            (r"\b(?:high|low)\s+of\s+\d+\s*(?:degrees?|°|f|c)\b", "temperature high/low"),
            (r"\bchance\s+of\s+(?:rain|snow|storms?|showers?)\b", "precipitation chance"),
        ],

        # ============================================================
        # GBIF - Biodiversity and species data
        # ============================================================
        "GBIF": [
            # Species
            (r"\bspecies\b", "species"),
            (r"\bendangered\b", "endangered"),
            (r"\bcritically\s+endangered\b", "critically endangered"),
            (r"\bthreatened\s+species\b", "threatened"),
            (r"\bextinct(?:ion)?\b", "extinction"),
            (r"\biucn\s+(?:red\s+list|status)\b", "IUCN"),
            # Habitat & ecology
            (r"\bhabitat(?:\s+loss)?\b", "habitat"),
            (r"\bbiodiversity\b", "biodiversity"),
            (r"\becosystem\b", "ecosystem"),
            (r"\bwildlife\b", "wildlife"),
            (r"\bfauna\b", "fauna"),
            (r"\bflora\b", "flora"),
            # Conservation
            (r"\bconservation\b", "conservation"),
            (r"\bprotected\s+(?:area|species|habitat)\b", "protected"),
            (r"\bnature\s+reserve\b", "nature reserve"),
            (r"\bnational\s+park\b", "national park"),
            # Animals
            (r"\bmammal\b", "mammal"),
            (r"\breptile\b", "reptile"),
            (r"\bamphibian\b", "amphibian"),
            (r"\bbird\s+(?:species|population)\b", "birds"),
            (r"\binsect\s+(?:species|population|decline)\b", "insects"),
            (r"\bpollinator\b", "pollinator"),
            (r"\bbee\s+(?:population|colony|decline)\b", "bees"),
            (r"\bdeforestation\b", "deforestation"),
            (r"\breforestation\b", "reforestation"),
            (r"\binvasive\s+species\b", "invasive species"),
        ],

        # ============================================================
        # WHO - World Health Organization global health data
        # ============================================================
        "WHO": [
            (r"\bworld\s+health\s+organi[sz]ation\b", "WHO"),
            (r"\bwho\s+(?:says?|reports?|data|estimates?|guidelines?|recommends?)\b", "WHO"),
            (r"\bglobal\s+health\b", "global health"),
            (r"\b(?:global|worldwide|international)\s+(?:cases?|deaths?|mortality|outbreak)\b", "global stats"),
            (r"\bpandemic\s+(?:data|statistics|response|preparedness)\b", "pandemic"),
            (r"\bglobal\s+(?:death|mortality)\s+(?:toll|rate)\b", "global mortality"),
            (r"\bdisease\s+burden\b", "disease burden"),
            (r"\blife\s+expectancy\b", "life expectancy"),
            (r"\binfant\s+mortality\b", "infant mortality"),
            (r"\bmaternal\s+mortality\b", "maternal mortality"),
            (r"\bvaccination\s+(?:rate|coverage)\b", "vaccination rate"),
            (r"\bherd\s+immunity\b", "herd immunity"),
        ],

        # ============================================================
        # Companies House - UK company information
        # ============================================================
        "Companies House": [
            (r"\buk\s+compan(?:y|ies)\b", "UK company"),
            (r"\bcompanies\s+house\b", "Companies House"),
            (r"\bbritish\s+(?:company|firm|business|corporation)\b", "British company"),
            (r"\bdirector(?:s)?\s+(?:of|at)\b", "directors"),
            (r"\bregistered\s+(?:in\s+)?(?:the\s+)?(?:uk|england|wales|scotland)\b", "UK registered"),
            (r"\bcompany\s+(?:filing|accounts?|registration|number)\b", "company filing"),
            (r"\bltd\.?\b", "Ltd"),
            (r"\bplc\.?\b", "PLC"),
            (r"\bincorporated\s+(?:in\s+)?(?:uk|england)\b", "incorporated UK"),
        ],

        # ============================================================
        # Semantic Scholar / CrossRef - Academic research
        # ============================================================
        "Semantic Scholar": [
            (r"\bpeer[- ]reviewed\s+(?:study|paper|research|journal)\b", "peer-reviewed"),
            (r"\bacademic\s+(?:study|paper|research|journal)\b", "academic"),
            (r"\bscientific\s+(?:study|paper|research|journal|evidence)\b", "scientific"),
            (r"\bjournal\s+(?:article|paper|study)\b", "journal"),
            (r"\bpublished\s+(?:in|study|research)\b", "published research"),
            (r"\bcitations?\b", "citations"),
            (r"\bh[- ]index\b", "h-index"),
            (r"\bimpact\s+factor\b", "impact factor"),
        ],

        # ============================================================
        # Library of Congress - Historical records
        # ============================================================
        "Library of Congress": [
            (r"\bhistorical\s+(?:records?|documents?|archives?)\b", "historical records"),
            (r"\barchival\s+(?:records?|documents?|evidence)\b", "archival"),
            (r"\bprimary\s+source\b", "primary source"),
            (r"\bhistoric(?:al)?\s+(?:photographs?|images?|maps?)\b", "historical images"),
            (r"\bnewspaper\s+archives?\b", "newspaper archives"),
            (r"\blibrary\s+of\s+congress\b", "Library of Congress"),
        ],
    }

    def __init__(self):
        """Initialize with compiled regex patterns for fast matching"""
        self._compiled_patterns: Dict[str, List[tuple]] = {}

        for adapter_name, rules in self.KEYWORD_RULES.items():
            self._compiled_patterns[adapter_name] = [
                (re.compile(pattern, re.IGNORECASE), keyword_desc)
                for pattern, keyword_desc in rules
            ]

        logger.info(f"ClaimKeywordRouter initialized with {len(self.KEYWORD_RULES)} adapter rules")

    def detect_keywords(self, claim_text: str) -> List[KeywordMatch]:
        """
        Detect keywords in claim text and return matching adapters.

        Args:
            claim_text: The claim text to analyze

        Returns:
            List of KeywordMatch objects with matched keywords and adapter names
        """
        matches: List[KeywordMatch] = []
        seen_adapters: Set[str] = set()

        for adapter_name, patterns in self._compiled_patterns.items():
            for compiled_pattern, keyword_desc in patterns:
                if compiled_pattern.search(claim_text):
                    if adapter_name not in seen_adapters:
                        matches.append(KeywordMatch(
                            keyword=keyword_desc,
                            pattern=compiled_pattern.pattern,
                            adapter_name=adapter_name,
                            confidence=0.8
                        ))
                        seen_adapters.add(adapter_name)
                        logger.debug(f"Keyword match: '{keyword_desc}' -> {adapter_name}")
                        break  # One match per adapter is enough

        return matches

    def get_additional_adapters(
        self,
        claim_text: str,
        current_adapters: List[Any],
        api_registry: Optional[Any] = None
    ) -> List[Any]:
        """
        Get additional adapters to query based on claim keywords.

        This is ADDITIVE - returns adapters that should be added to the existing
        list, not replacing them. Automatically deduplicates against current adapters.

        Args:
            claim_text: The claim text to analyze
            current_adapters: List of adapters already selected for this claim
            api_registry: Optional APIAdapterRegistry instance (lazy loads if not provided)

        Returns:
            List of additional adapters to add (empty if none or all already included)
        """
        # Lazy load registry if not provided
        if api_registry is None:
            from app.services.government_api_client import get_api_registry
            api_registry = get_api_registry()

        # Get adapter names already in use
        current_adapter_names = {
            getattr(adapter, 'api_name', str(adapter))
            for adapter in current_adapters
        }

        # Detect keywords
        keyword_matches = self.detect_keywords(claim_text)

        if not keyword_matches:
            return []

        # Get adapters for matches, excluding those already in use
        additional_adapters = []
        for match in keyword_matches:
            if match.adapter_name not in current_adapter_names:
                adapter = api_registry.get_adapter_by_name(match.adapter_name)
                if adapter:
                    additional_adapters.append(adapter)
                    logger.info(
                        f"[KEYWORD ROUTING] Adding {match.adapter_name} "
                        f"(matched '{match.keyword}' in claim)"
                    )
                else:
                    logger.warning(
                        f"[KEYWORD ROUTING] Adapter '{match.adapter_name}' not found in registry"
                    )
            else:
                logger.debug(
                    f"[KEYWORD ROUTING] {match.adapter_name} already in adapters, skipping"
                )

        return additional_adapters


# Singleton instance
_router_instance: Optional[ClaimKeywordRouter] = None


def get_keyword_router() -> ClaimKeywordRouter:
    """Get the singleton ClaimKeywordRouter instance"""
    global _router_instance
    if _router_instance is None:
        _router_instance = ClaimKeywordRouter()
    return _router_instance
