import pytest
from app.utils.source_validator import SourceValidator

def test_filters_revision_guides():
    validator = SourceValidator()
    evidence = [{
        'title': 'Y13 Ethics Revision Guide Paper 2',
        'url': 'https://king-james.co.uk/wp-content/uploads/revision.pdf',
        'source': 'king-james.co.uk'
    }]

    validated, stats = validator.validate_sources(evidence)

    assert len(validated) == 0
    assert stats['filtered_count'] == 1
    assert 'Educational material' in stats['filtered_sources'][0]['reason']

def test_allows_bbc_news():
    validator = SourceValidator()
    evidence = [{
        'title': 'UK News Report on Policy Changes',
        'url': 'https://bbc.co.uk/news/uk-123456',
        'source': 'BBC'
    }]

    validated, stats = validator.validate_sources(evidence)

    assert len(validated) == 1
    assert stats['filtered_count'] == 0

def test_allows_gov_education():
    validator = SourceValidator()
    evidence = [{
        'title': 'Department for Education Statistics',
        'url': 'https://gov.uk/education/statistics-report',
        'source': 'GOV.UK'
    }]

    validated, stats = validator.validate_sources(evidence)

    assert len(validated) == 1  # Should PASS (authoritative)
    assert stats['filtered_count'] == 0

def test_filters_student_uploads():
    validator = SourceValidator()
    evidence = [{
        'title': 'Class Notes on British Politics',
        'url': 'https://university.edu/uploads/student-notes.pdf',
        'source': 'university.edu'
    }]

    validated, stats = validator.validate_sources(evidence)

    assert len(validated) == 0
    assert stats['filtered_count'] == 1

def test_filters_exam_prep():
    validator = SourceValidator()
    evidence = [{
        'title': 'GCSE Physics Exam Prep Guide',
        'url': 'https://studysite.com/gcse/physics',
        'source': 'studysite.com'
    }]

    validated, stats = validator.validate_sources(evidence)

    assert len(validated) == 0
    assert stats['filtered_count'] == 1
    assert 'Educational material' in stats['filtered_sources'][0]['reason']

def test_filters_forums():
    validator = SourceValidator()
    evidence = [{
        'title': 'Discussion: What do you think about climate change?',
        'url': 'https://reddit.com/r/science/discussion',
        'source': 'Reddit'
    }]

    validated, stats = validator.validate_sources(evidence)

    assert len(validated) == 0
    assert stats['filtered_count'] == 1
    assert 'Low-quality source' in stats['filtered_sources'][0]['reason']

def test_mixed_evidence_list():
    validator = SourceValidator()
    evidence = [
        {
            'title': 'BBC Breaking News',
            'url': 'https://bbc.co.uk/news/uk-123',
            'source': 'BBC'
        },
        {
            'title': 'Study Guide for A-Level Students',
            'url': 'https://school.edu/study-guides/history',
            'source': 'school.edu'
        },
        {
            'title': 'Government Report on Economy',
            'url': 'https://gov.uk/reports/economy-2024',
            'source': 'GOV.UK'
        }
    ]

    validated, stats = validator.validate_sources(evidence)

    assert len(validated) == 2  # BBC and GOV.UK should pass
    assert stats['filtered_count'] == 1  # Study guide should be filtered
    assert stats['original_count'] == 3

def test_empty_evidence_list():
    validator = SourceValidator()
    evidence = []

    validated, stats = validator.validate_sources(evidence)

    assert len(validated) == 0
    assert stats['filtered_count'] == 0
    assert stats['original_count'] == 0

def test_authoritative_education_domains():
    validator = SourceValidator()
    # Test that gov.uk/education is allowed
    evidence = [{
        'title': 'Department for Education Report',
        'url': 'https://education.gov.uk/statistics/annual-report',
        'source': 'education.gov.uk'
    }]

    validated, stats = validator.validate_sources(evidence)

    assert len(validated) == 1  # Should pass (authoritative)
    assert stats['filtered_count'] == 0
