"""Generate test PDF v4 with realistic mixed data."""

from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import MagicMock
import weasyprint

template_dir = Path("app/templates")
env = Environment(loader=FileSystemLoader(str(template_dir)))
t = env.get_template("pdf/fact_check_report.html")

check = MagicMock()
check.id = "7f43432a-86dc-47a4-80ce-e280dc7113b0"
check.input_url = "https://example.com/non-compete-clauses-employment-law"
check.created_at = datetime(2026, 3, 11, 16, 6, 0)
check.processing_time_ms = 53400
check.entry_mode = "focused"

sources = [
    (
        "lawworks.ca",
        "Franchise non-competition enforcement in Canada: A guide for franchisors",
        "commentary",
        "analysis",
        "https://www.lawworks.ca/franchise-disputes/franchise-non-competition",
        "Serious issue: The non-compete clause must appear commercially reasonable and legally enforceable, with evidence showing a clear breach.",
        datetime(2025, 6, 26),
    ),
    (
        "employmentlawworldview.com",
        "Global Trends in Non-competes - Employment Law Worldview",
        "reporting",
        "news_reporting",
        "https://www.employmentlawworldview.com/global-trends-in-non-competes",
        "Non-competes or clauses that restrict employees from engaging in a competing business are an important tool employers use.",
        datetime(2026, 2, 18),
    ),
    (
        "bowriveremploymentlaw.com",
        "Non-Competition Clause Had Too Much Protection",
        "commentary",
        "analysis",
        "https://bowriveremploymentlaw.com/non-competition-covenant-found-unreasonable",
        "The clause attempts to limit the employee from being involved in any manner whatsoever in any business in direct competition.",
        datetime(2025, 10, 8),
    ),
    (
        "ascentemploymentlaw.ca",
        "Non-Competes, Non-Solicitation and Confidentiality Clauses in BC",
        "commentary",
        "analysis",
        "https://ascentemploymentlaw.ca/blog/try-and-stop-me-implications",
        "The non-compete must contain each of those elements and they must only be restrictive enough to protect the business interest.",
        datetime(2025, 3, 26),
    ),
    (
        "whitecase.com",
        "White and Case Global Non-Compete Resource Center (NCRC)",
        "primary",
        "data",
        "https://www.whitecase.com/insight-tool/white-case-global-non-compete",
        "The proposal follows a consultation period that explored alternatives including complete prohibition of post-termination restrictions.",
        datetime(2025, 9, 29),
    ),
    (
        "achkarlaw.com",
        "Non-Compete Agreements in Ontario: Are They Enforceable After the 2022 Ban?",
        "commentary",
        "analysis",
        "https://achkarlaw.com/insights/ontario/non-compete-agreements",
        "In most employment situations, non-compete clauses are illegal in Ontario following the Working for Workers Act, 2021.",
        datetime(2026, 2, 24),
    ),
    (
        "cfib-fcei.ca",
        "How employment contracts protect your bottom line: Q&A - CFIB",
        "commentary",
        "analysis",
        "https://www.cfib-fcei.ca/en/tools-resources/how-employment-contracts",
        "The stipulated duration, territory, and scope of activity must be proportionate to the interests being protected.",
        datetime(2025, 4, 4),
    ),
    (
        "carbertwaite.com",
        "Ambiguous and Overbroad Non-Compete Clause Sinks Employer Injunction",
        "reporting",
        "news_reporting",
        "https://carbertwaite.com/news-legal-commentary/ambiguous-and-overbroad",
        "The Applicants had the onus of demonstrating: (1) serious issue to be tried; (2) irreparable harm; (3) balance of convenience.",
        datetime(2025, 11, 25),
    ),
    (
        "canadianconsultingengineer.com",
        "Non-solicit And Non-compete Clauses For Engineers",
        "commentary",
        "analysis",
        "https://www.canadianconsultingengineer.com/features/non-solicit-and-non-compete",
        "In the realm of employment law, non-solicit and non-compete clauses are critical for protecting proprietary interests.",
        datetime(2025, 4, 2),
    ),
    (
        "yycemploymentlawgrp.com",
        "Are you Subject to a Non-Compete by Your Employer?",
        "commentary",
        "analysis",
        "https://yycemploymentlawgrp.com/are-you-subject-to-a-non-compete",
        "In Alberta, a non-competition clause in an employment agreement can be enforceable but only under strict conditions.",
        datetime(2025, 4, 5),
    ),
    (
        "nortonrosefulbright.com",
        "Alternatives to traditional non-competes - Norton Rose Fulbright",
        "primary",
        "official_statement",
        "https://www.nortonrosefulbright.com/en/knowledge/publications",
        "Its terms are minimally restrictive, impairing a departed employees ability to work only to the minimum extent necessary.",
        datetime(2025, 12, 11),
    ),
    (
        "hylandkc.com",
        "Non-Compete Agreements: What You Need to Know Before Signing",
        "commentary",
        "analysis",
        "https://hylandkc.com/blog/non-compete-agreements-what-you-need",
        "Financial strain: Defending yourself in court or taking a lower-paying job can hurt your income.",
        datetime(2025, 6, 5),
    ),
    (
        "langlois.ca",
        "Non-compete clauses and remote work: rethinking traditional restrictions",
        "commentary",
        "analysis",
        "http://langlois.ca/en/insights/non-compete-clauses-and-remote-work",
        "Recent years have seen the integration of remote work, blurring the physical boundaries of the workplace.",
        datetime(2025, 8, 7),
    ),
    (
        "blueprintlaw.ca",
        "Non-Competition vs. Non-Solicitation Clauses in Canada: Key Legal Differences",
        "commentary",
        "analysis",
        "https://www.blueprintlaw.ca/non-compete-vs-non-solicit-canada",
        "The Supreme Court of Canada upheld a non-competition clause in a business sale context.",
        datetime(2025, 8, 17),
    ),
    (
        "mcelaw.com",
        "Key Considerations for Drafting an Enforceable Non-Compete Agreement",
        "commentary",
        "analysis",
        "https://mcelaw.com/blog/key-considerations-for-drafting-an-enforceable",
        "A well-drafted non-compete agreement can help prevent employees from taking sensitive knowledge to a competitor.",
        datetime(2025, 5, 8),
    ),
]

evs = []
evidence_index = {}
tier_counts = {"primary": 0, "reporting": 0, "commentary": 0}
type_counts: dict[str, int] = {}

for i, (src, title, tier, etype, url, snip, pub) in enumerate(sources):
    ev = MagicMock()
    ev_id = f"ev-{i+1:03d}"
    ev.evidence_id = ev_id
    ev.id = f"uuid-{i+1}"
    ev.source = src
    ev.title = title
    ev.snippet = snip
    ev.url = url
    ev.tier = tier
    ev.evidence_type = etype
    ev.published_date = pub
    ev.relevance_score = 4.5 - i * 0.15
    evs.append(ev)
    evidence_index[ev_id] = i + 1
    tier_counts[tier] = tier_counts.get(tier, 0) + 1
    type_counts[etype] = type_counts.get(etype, 0) + 1

claims = [
    {
        "text": "Non-compete clauses in employment contracts may be unenforceable if they go beyond what is reasonably necessary to protect legitimate business interests",
        "claim_type": "definitional",
        "claim_map": None,
        "orientation": "Of 2 elements examined, retrieved evidence is insufficient to assess any.",
        "elements": [
            {
                "description": "A non-compete clause must be evaluated based on its scope relative to the protection of legitimate business interests.",
                "state": "unresolved",
                "evidence_refs": [
                    {"evidence_id": "ev-013", "relationship": "supports"},
                    {"evidence_id": "ev-001", "relationship": "supports"},
                    {"evidence_id": "ev-014", "relationship": "supports"},
                    {"evidence_id": "ev-002", "relationship": "context"},
                    {"evidence_id": "ev-006", "relationship": "context"},
                ],
                "uncertainty": None,
            },
            {
                "description": "If the scope of a non-compete clause is found to be beyond what is reasonably necessary for protecting legitimate business interests, it is considered unenforceable.",
                "state": "unresolved",
                "evidence_refs": [],
                "uncertainty": "No historical comparison available.",
            },
        ],
        "evidence": evs,
        "evidence_index": evidence_index,
    }
]

html = t.render(
    check=check,
    claims=claims,
    total_evidence=15,
    total_elements=2,
    tier_counts=tier_counts,
    type_counts=type_counts,
    now=datetime.now(timezone.utc),
)

pdf = weasyprint.HTML(string=html).write_pdf()
out = Path("C:/Users/james/Downloads/tru8-test-v4.pdf")
out.write_bytes(pdf)
print(f"PDF: {len(pdf)} bytes -> {out}")
