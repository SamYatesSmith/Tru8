"""Peer-reviewed society journals are primary, and consumer health sites are not.

Found 2026-08-03 while comparing two runs of the same claim: `_ACADEMIC_PATTERNS`
covered the big commercial platforms and a few flagship titles but omitted
journals that learned societies publish on their own domains. The New England
Journal of Medicine classified as COMMENTARY, and in TRU-577F-AB3F an AHA
Scientific Statement in *Circulation* sat in the same tier as a Drinkaware
explainer.

Two halves are tested, and the second matters as much as the first:

  * the added venues are primary/academic, through BOTH consumers of the pattern
    (`_classify_heuristic` and `_high_confidence_override`, the latter being the
    one that beats the LLM in the normal path); and
  * the sites that were correctly commentary STAY commentary. The failure mode
    for a fix like this is sweeping up every health-adjacent domain — the pool
    that exposed the bug contained eleven commentary items and only two of them
    were wrong.

Design + blast radius: audit/2026-08-03_journal_tier_classification_design.md
"""

import pytest

from app.pipeline.evidence_classifier import (
    _classify_heuristic,
    _high_confidence_override,
)


def _evidence(url: str, title: str = "A study") -> dict:
    return {
        "evidence_id": f"ev-{url}",
        "title": title,
        "source": url.split("/")[2],
        "url": url,
        "snippet": "…",
    }


# Every entry is a peer-reviewed venue whose URL alone settles the tier — the
# bar _high_confidence_override sets. Each names the publication so a future
# reader can check the claim rather than trust the list.
SOCIETY_JOURNALS = [
    (
        "https://www.nejm.org/doi/full/10.1056/NEJMoa2032183",
        "New England Journal of Medicine",
    ),
    (
        "https://www.ahajournals.org/doi/10.1161/CIR.0000000000001341",
        "AHA — Circulation",
    ),
    (
        "https://www.ajconline.org/article/S0002-9149(25)00",
        "American Journal of Cardiology",
    ),
    ("https://www.annals.org/doi/10.7326/M20-1234", "Annals of Internal Medicine"),
    ("https://www.acpjournals.org/doi/10.7326/M23-0001", "ACP Journals"),
    ("https://diabetesjournals.org/care/article/47/1/1", "ADA — Diabetes Care"),
    ("https://aacrjournals.org/cancerres/article/84/1/1", "AACR — Cancer Research"),
    ("https://ashpublications.org/blood/article/143/1/1", "ASH — Blood"),
    ("https://www.atsjournals.org/doi/10.1164/rccm.202301", "ATS — AJRCCM"),
    ("https://journals.physiology.org/doi/10.1152/jappl.2024", "APS — Physiology"),
    ("https://www.jneurosci.org/content/44/1/1", "Journal of Neuroscience"),
    ("https://bmcmedicine.biomedcentral.com/articles/10.1186/s12916", "BMC Medicine"),
    ("https://www.embopress.org/doi/full/10.15252/embj.2024", "EMBO Journal"),
    ("https://elifesciences.org/articles/12345", "eLife"),
    ("https://www.tandfonline.com/doi/full/10.1080/00016489", "Taylor & Francis"),
    ("https://journals.sagepub.com/doi/10.1177/0956797624", "SAGE"),
    (
        "https://www.cambridge.org/core/journals/psychological-medicine/article",
        "Cambridge University Press",
    ),
    ("https://karger.com/nef/article/148/1/1", "Karger"),
    ("https://ieeexplore.ieee.org/document/10123456", "IEEE Xplore"),
]

# Correctly commentary today. A fix that upgrades these has over-reached: they
# report ON research, they are not the peer-reviewed record.
CORRECTLY_NOT_ACADEMIC = [
    ("https://news.stanford.edu/stories/2025/08/moderate", "university news office"),
    (
        "https://www.publichealth.columbia.edu/news/new-research",
        "university news office",
    ),
    (
        "https://med.stanford.edu/news/insights/2025/08/alcohol",
        "university news office",
    ),
    (
        "https://www.health.harvard.edu/heart-health/alcohol",
        "consumer health publication",
    ),
    ("https://www.heart.org/en/healthy-living/healthy-eating", "society campaign site"),
    (
        "https://www.hopkinsmedicine.org/health/wellness-and-prevention",
        "hospital patient info",
    ),
    ("https://www.drinkaware.co.uk/facts/health-effects", "charity explainer"),
    ("https://www.heartfoundation.org.au/healthy-living/alcohol", "charity explainer"),
]


class TestSocietyJournalsAreAcademic:
    @pytest.mark.unit
    @pytest.mark.parametrize("url,publication", SOCIETY_JOURNALS)
    def test_heuristic_classifies_as_primary_academic(self, url, publication):
        tier, evidence_type = _classify_heuristic(_evidence(url))
        assert tier == "primary", f"{publication} ({url}) got tier={tier}"
        assert evidence_type == "academic", f"{publication} got type={evidence_type}"

    @pytest.mark.unit
    @pytest.mark.parametrize("url,publication", SOCIETY_JOURNALS)
    def test_override_beats_the_llm(self, url, publication):
        """The path that actually decides in production.

        The LLM classifies first; _high_confidence_override then corrects it on
        URL identity. If a venue is only in the heuristic it barely fires, since
        the heuristic is the fallback for when the LLM returns nothing.
        """
        result = _high_confidence_override(_evidence(url))
        assert result is not None, f"{publication} is not high-confidence"
        assert result == ("primary", "academic"), f"{publication} got {result}"


class TestTheFixDoesNotOverReach:
    @pytest.mark.unit
    @pytest.mark.parametrize("url,kind", CORRECTLY_NOT_ACADEMIC)
    def test_reporting_about_research_stays_out_of_primary(self, url, kind):
        """These were RIGHT before and must stay right.

        In the pool that exposed the bug, 11 items were commentary and only 2
        were misclassified. A change that moved all 11 would be a worse defect
        than the one it fixed.
        """
        tier, _ = _classify_heuristic(_evidence(url))
        assert tier != "primary", f"{kind} ({url}) was wrongly upgraded to primary"

    @pytest.mark.unit
    @pytest.mark.parametrize("url,kind", CORRECTLY_NOT_ACADEMIC)
    def test_not_treated_as_high_confidence_academic(self, url, kind):
        result = _high_confidence_override(_evidence(url))
        assert result != ("primary", "academic"), f"{kind} ({url}) wrongly overridden"

    @pytest.mark.unit
    def test_mdpi_deliberately_excluded(self):
        """Peer-reviewed but contested editorial standards.

        Excluded on purpose (design §4) so this change does not import an
        argument it does not need to have. If it is ever added, that should be a
        deliberate decision with its own reasoning, not a silent list edit.
        """
        assert _high_confidence_override(
            _evidence("https://www.mdpi.com/2072-6643/16/1/1")
        ) != (
            "primary",
            "academic",
        )


class TestTheOriginalDefect:
    @pytest.mark.unit
    def test_nejm_is_not_commentary(self):
        """The headline case, kept as its own named test."""
        tier, evidence_type = _classify_heuristic(
            _evidence("https://www.nejm.org/doi/full/10.1056/NEJMoa2032183")
        )
        assert (tier, evidence_type) == ("primary", "academic")

    @pytest.mark.unit
    def test_the_aha_scientific_statement_from_tru_577f_ab3f(self):
        """The exact URL from the report that exposed this, tiered commentary."""
        tier, _ = _classify_heuristic(
            _evidence(
                "https://www.ahajournals.org/doi/10.1161/CIR.0000000000001341",
                title="Alcohol Use and Cardiovascular Disease: A Scientific Statement",
            )
        )
        assert tier == "primary"
