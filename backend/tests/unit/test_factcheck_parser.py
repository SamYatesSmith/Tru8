"""
Unit tests for Fact-Check Parser

Tests the parsing logic for Snopes and PolitiFact articles.
"""

import pytest
from bs4 import BeautifulSoup
from app.services.factcheck_parser import (
    FactCheckParser,
    SnopesParser,
    PolitiFactParser
)


class TestSnopesParser:
    """Test Snopes article parsing"""

    def test_extract_claim_from_claim_cont(self):
        """Test extracting claim from claim_cont div"""
        html = """
        <html>
            <div class="claim_cont">
                Trump hosted a 90,000-square-foot ballroom project
            </div>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        parser = SnopesParser()

        claim = parser._extract_claim(soup)
        assert claim == "Trump hosted a 90,000-square-foot ballroom project"

    def test_extract_claim_from_meta_tag(self):
        """Test extracting claim from og:description meta tag"""
        html = """
        <html>
            <meta property="og:description" content="Claim: The White House was exempt from historic preservation laws">
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        parser = SnopesParser()

        claim = parser._extract_claim(soup)
        assert claim == "The White House was exempt from historic preservation laws"

    def test_extract_rating_true(self):
        """Test extracting 'True' rating"""
        html = """
        <html>
            <div class="rating_title_wrap">True</div>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        parser = SnopesParser()

        rating = parser._extract_rating(soup)
        assert rating == "True"

    def test_extract_rating_false(self):
        """Test extracting 'False' rating"""
        html = """
        <html>
            <span class="rating">False</span>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        parser = SnopesParser()

        rating = parser._extract_rating(soup)
        assert rating == "False"

    def test_extract_rating_mixture(self):
        """Test extracting 'Mixture' rating"""
        html = """
        <html>
            <img class="rating_img" alt="Mixture" src="rating.png">
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        parser = SnopesParser()

        rating = parser._extract_rating(soup)
        assert rating == "Mixture"

    def test_parse_full_article(self):
        """Test parsing complete Snopes article structure"""
        html = """
        <html>
            <div class="claim_cont">The rendering of Trump's ballroom is fake</div>
            <div class="rating_title_wrap">True</div>
            <div class="single-body">
                <p><strong>What's True:</strong> The viral rendering is not an official architectural plan.</p>
                <p><strong>What's False:</strong> The ballroom project itself is real and confirmed.</p>
            </div>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        parser = SnopesParser()

        result = parser.parse(soup, "https://www.snopes.com/fact-check/trump-ballroom")

        assert result is not None
        assert result['target_claim'] == "The rendering of Trump's ballroom is fake"
        assert result['rating'] == "True"

    def test_parse_malformed_html(self):
        """Test handling of malformed HTML"""
        html = "<html><div>Incomplete"
        soup = BeautifulSoup(html, 'html.parser')
        parser = SnopesParser()

        result = parser.parse(soup, "https://www.snopes.com/bad-url")
        assert result is None  # Should return None for unparseable content


class TestPolitiFactParser:
    """Test PolitiFact article parsing"""

    def test_extract_claim_from_statement_quote(self):
        """Test extracting claim from m-statement__quote"""
        html = """
        <html>
            <div class="m-statement__quote">
                "The Infrastructure Bill allocates $110 billion to roads"
            </div>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        parser = PolitiFactParser()

        claim = parser._extract_claim(soup)
        assert claim == "The Infrastructure Bill allocates $110 billion to roads"

    def test_extract_claim_removes_quotes(self):
        """Test that quotes are stripped from claim"""
        html = """
        <html>
            <div class="m-statement__quote">"Quoted claim here"</div>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        parser = PolitiFactParser()

        claim = parser._extract_claim(soup)
        assert claim == "Quoted claim here"
        assert '"' not in claim

    def test_extract_rating_true(self):
        """Test extracting 'True' rating"""
        html = """
        <html>
            <div class="m-statement__meter">
                <img class="c-image__original" alt="true" src="meter.png">
            </div>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        parser = PolitiFactParser()

        rating = parser._extract_rating(soup)
        assert rating == "True"

    def test_extract_rating_pants_on_fire(self):
        """Test extracting 'Pants on Fire' rating"""
        html = """
        <html>
            <div class="m-statement__meter">
                <img alt="pants-fire" src="meter.png">
            </div>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        parser = PolitiFactParser()

        rating = parser._extract_rating(soup)
        assert rating == "Pants on Fire"

    def test_extract_rating_false(self):
        """Test extracting 'False' rating"""
        html = """
        <html>
            <div class="m-statement__meter">
                <img alt="false" src="meter.png">
            </div>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        parser = PolitiFactParser()

        rating = parser._extract_rating(soup)
        assert rating == "False"

    def test_extract_summary(self):
        """Test extracting article summary"""
        html = """
        <html>
            <div class="m-textblock">
                <p>This is the first substantial paragraph explaining the fact-check in detail.</p>
                <p>Second paragraph with more details.</p>
            </div>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        parser = PolitiFactParser()

        summary = parser._extract_summary(soup)
        assert summary == "This is the first substantial paragraph explaining the fact-check in detail."

    def test_parse_full_article(self):
        """Test parsing complete PolitiFact article"""
        html = """
        <html>
            <div class="m-statement__quote">"Biden cancelled student debt"</div>
            <div class="m-statement__meter">
                <img alt="Half True" src="meter.png">
            </div>
            <div class="m-textblock">
                <p>Biden announced a student debt cancellation program, but it was blocked by courts.</p>
            </div>
        </html>
        """
        soup = BeautifulSoup(html, 'html.parser')
        parser = PolitiFactParser()

        result = parser.parse(soup, "https://www.politifact.com/factchecks/student-debt")

        assert result is not None
        assert result['target_claim'] == "Biden cancelled student debt"
        assert result['rating'] == "Half True"
        assert "student debt cancellation program" in result['summary']


class TestFactCheckParser:
    """Test main FactCheckParser class"""

    def test_is_factcheck_domain_snopes(self):
        """Test detection of Snopes domain"""
        parser = FactCheckParser()
        assert parser._is_factcheck_domain("https://www.snopes.com/fact-check/test")
        assert parser._is_factcheck_domain("https://snopes.com/test")

    def test_is_factcheck_domain_politifact(self):
        """Test detection of PolitiFact domain"""
        parser = FactCheckParser()
        assert parser._is_factcheck_domain("https://www.politifact.com/factchecks/test")
        assert parser._is_factcheck_domain("https://politifact.com/test")

    def test_is_factcheck_domain_factcheck_org(self):
        """Test detection of FactCheck.org domain"""
        parser = FactCheckParser()
        assert parser._is_factcheck_domain("https://www.factcheck.org/test")

    def test_is_factcheck_domain_non_factcheck(self):
        """Test that non-fact-check domains return False"""
        parser = FactCheckParser()
        assert not parser._is_factcheck_domain("https://www.nytimes.com/article")
        assert not parser._is_factcheck_domain("https://www.bbc.co.uk/news")

    @pytest.mark.asyncio
    async def test_parse_factcheck_evidence_no_evidence(self):
        """Test handling of empty evidence list"""
        parser = FactCheckParser()
        claims = [{"text": "Test claim", "position": 0}]
        evidence = {}

        result = await parser.parse_factcheck_evidence(claims, evidence)
        assert result == {}

    @pytest.mark.asyncio
    async def test_parse_factcheck_evidence_non_factcheck(self):
        """Test that non-fact-check evidence passes through unchanged"""
        parser = FactCheckParser()
        claims = [{"text": "Test claim", "position": 0}]
        evidence = {
            "0": [
                {
                    "url": "https://www.nytimes.com/article",
                    "title": "News article",
                    "is_factcheck": False
                }
            ]
        }

        result = await parser.parse_factcheck_evidence(claims, evidence)
        assert result["0"][0]["url"] == "https://www.nytimes.com/article"
        assert "factcheck_parse_success" not in result["0"][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
