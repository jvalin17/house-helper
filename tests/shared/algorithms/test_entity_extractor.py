"""Tests for entity_extractor — spaCy-based skill/company/title extraction.

These tests require spaCy + en_core_web_md model.
Skipped if not installed.
"""

import pytest

try:
    from shared.algorithms.entity_extractor import (
        extract_entities,
        extract_skills_from_text,
        is_available,
    )
    HAS_SPACY = is_available()
except ImportError:
    HAS_SPACY = False

requires_spacy = pytest.mark.skipif(
    not HAS_SPACY,
    reason="spaCy or en_core_web_md not installed",
)


class TestIsAvailable:
    def test_reports_availability(self):
        from shared.algorithms.entity_extractor import is_available

        result = is_available()
        assert isinstance(result, bool)


@requires_spacy
class TestExtractEntities:
    """Extract named entities (companies, locations, etc.) from text."""

    def test_extracts_organization(self):
        entities = extract_entities("I worked at Google for 3 years")
        org_names = [e["text"] for e in entities if e["label"] == "ORG"]
        assert "Google" in org_names

    def test_extracts_date(self):
        entities = extract_entities("From January 2020 to March 2023")
        date_entities = [e for e in entities if e["label"] == "DATE"]
        assert len(date_entities) > 0

    def test_empty_text_returns_empty(self):
        entities = extract_entities("")
        assert entities == []

    def test_returns_structured_entities(self):
        entities = extract_entities("I worked at Microsoft in Seattle")
        assert all("text" in e and "label" in e for e in entities)


class TestExtractSkillsFromText:
    """Extract technical skills using regex patterns — no spaCy needed."""

    def test_extracts_known_patterns(self):
        text = "Experience with Python, React, and Docker required"
        skills = extract_skills_from_text(text)
        assert "Python" in skills
        assert "React" in skills
        assert "Docker" in skills

    def test_empty_text_returns_empty(self):
        skills = extract_skills_from_text("")
        assert skills == []

    def test_returns_strings(self):
        text = "Must know Java and Kubernetes"
        skills = extract_skills_from_text(text)
        assert all(isinstance(s, str) for s in skills)
        assert "Java" in skills
        assert "Kubernetes" in skills

    def test_deduplicates(self):
        text = "Python and Python and more Python"
        skills = extract_skills_from_text(text)
        assert skills.count("Python") == 1

    def test_case_insensitive_dedup(self):
        text = "python and Python"
        skills = extract_skills_from_text(text)
        assert len(skills) == 1

    def test_handles_dotjs_variants(self):
        text = "Experience with Node.js and React"
        skills = extract_skills_from_text(text)
        skill_lower = [s.lower() for s in skills]
        assert "react" in skill_lower
