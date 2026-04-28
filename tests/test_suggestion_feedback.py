"""TDD tests for suggestion feedback — reject bad LLM suggestions.

Core behavior:
1. User can flag a suggestion as incorrect
2. Flagged suggestions are stored locally
3. The analyze_fit prompt includes rejected suggestions so LLM avoids them
4. Filtering works on partial text match (same bullet, different wording)
"""

import json
import sqlite3
from pathlib import Path

import pytest

from shared.db import connect_sync


@pytest.fixture
def db():
    return connect_sync(db_path=Path(":memory:"))


class TestSuggestionFeedbackStorage:
    """Test storing rejected suggestions in the database."""

    def test_save_rejected_suggestion(self, db):
        from agents.job.repositories.feedback_repo import SuggestionFeedbackRepo

        repo = SuggestionFeedbackRepo(db)
        repo.save_rejection(
            suggestion_text="Reword 'Designed a feedback system for emails' to emphasize LLM sentiment analysis",
            reason="This bullet doesn't involve LLMs — it's a rule-based system",
            original_bullet="Designed a feedback system for emails and push that analyzes user sentiment",
        )

        rejections = repo.list_rejections()
        assert len(rejections) == 1
        assert "LLM sentiment" in rejections[0]["suggestion_text"]

    def test_list_rejections_empty(self, db):
        from agents.job.repositories.feedback_repo import SuggestionFeedbackRepo

        repo = SuggestionFeedbackRepo(db)
        assert repo.list_rejections() == []

    def test_delete_rejection(self, db):
        from agents.job.repositories.feedback_repo import SuggestionFeedbackRepo

        repo = SuggestionFeedbackRepo(db)
        repo.save_rejection(
            suggestion_text="Bad suggestion",
            reason="Wrong",
            original_bullet="Original text",
        )
        rejections = repo.list_rejections()
        assert len(rejections) == 1

        repo.delete_rejection(rejections[0]["id"])
        assert repo.list_rejections() == []

    def test_multiple_rejections(self, db):
        from agents.job.repositories.feedback_repo import SuggestionFeedbackRepo

        repo = SuggestionFeedbackRepo(db)
        repo.save_rejection("Bad suggestion 1", "reason 1", "bullet 1")
        repo.save_rejection("Bad suggestion 2", "reason 2", "bullet 2")

        rejections = repo.list_rejections()
        assert len(rejections) == 2


class TestSuggestionFiltering:
    """Test that rejected suggestions are filtered from LLM output."""

    def test_exact_match_filtered(self, db):
        from agents.job.repositories.feedback_repo import SuggestionFeedbackRepo
        from agents.job.services.suggestion_filter import filter_suggestions

        repo = SuggestionFeedbackRepo(db)
        repo.save_rejection(
            suggestion_text="Reword email feedback bullet to emphasize LLM sentiment analysis",
            reason="Not accurate",
            original_bullet="Designed a feedback system for emails",
        )

        suggestions = [
            {"type": "reword_bullet", "description": "Reword email feedback bullet to emphasize LLM sentiment analysis", "impact": "+3%", "source": "Same experience"},
            {"type": "add_bullet", "description": "Add Kubernetes experience", "impact": "+2%", "source": "Knowledge bank"},
        ]

        filtered = filter_suggestions(suggestions, repo.list_rejections())
        assert len(filtered) == 1
        assert "Kubernetes" in filtered[0]["description"]

    def test_partial_match_filtered(self, db):
        """Same bullet targeted but different wording — should still be caught."""
        from agents.job.repositories.feedback_repo import SuggestionFeedbackRepo
        from agents.job.services.suggestion_filter import filter_suggestions

        repo = SuggestionFeedbackRepo(db)
        repo.save_rejection(
            suggestion_text="Emphasize LLM sentiment analysis in email feedback bullet",
            reason="Not accurate",
            original_bullet="Designed a feedback system for emails and push that analyzes user sentiment",
        )

        # LLM suggests same thing with different wording
        suggestions = [
            {"type": "reword_bullet", "description": "Highlight LLM sentiment analysis work from Zillow - 'Built feedback system analyzing user sentiment using LLMs'", "impact": "+3%", "source": "Zillow experience"},
            {"type": "add_bullet", "description": "Add React frontend skills section", "impact": "+2%", "source": "Knowledge bank"},
        ]

        filtered = filter_suggestions(suggestions, repo.list_rejections())
        # The LLM sentiment suggestion should be filtered because the original_bullet matches
        assert len(filtered) == 1
        assert "React" in filtered[0]["description"]

    def test_no_rejections_returns_all(self, db):
        from agents.job.services.suggestion_filter import filter_suggestions

        suggestions = [
            {"type": "add_bullet", "description": "Add something", "impact": "+2%", "source": "KB"},
        ]
        filtered = filter_suggestions(suggestions, [])
        assert len(filtered) == 1

    def test_zillow_email_bullet_specifically(self, db):
        """The exact scenario the user reported — Zillow email/LLM suggestion keeps appearing."""
        from agents.job.repositories.feedback_repo import SuggestionFeedbackRepo
        from agents.job.services.suggestion_filter import filter_suggestions

        repo = SuggestionFeedbackRepo(db)
        repo.save_rejection(
            suggestion_text="Highlight LLM sentiment analysis work from Zillow under a Gen AI section",
            reason="This bullet is about rule-based sentiment, not LLM/Gen AI",
            original_bullet="Designed a feedback system for emails and push that analyzes user sentiment using LLMs to drive content optimization",
        )

        # Next time LLM suggests something similar
        suggestions = [
            {"type": "reword_bullet", "description": "Expand 'Built notification pipeline' to emphasize ML model integration", "impact": "+5%", "source": "Zillow experience"},
            {"type": "reword_bullet", "description": "Reframe email feedback system as Gen AI sentiment analysis platform", "impact": "+4%", "source": "Zillow experience"},
            {"type": "add_bullet", "description": "Add GraphQL API development experience", "impact": "+2%", "source": "Knowledge bank"},
        ]

        filtered = filter_suggestions(suggestions, repo.list_rejections())
        # The "Gen AI sentiment" suggestion should be caught
        assert len(filtered) == 2
        descriptions = [s["description"] for s in filtered]
        assert any("notification pipeline" in d for d in descriptions)
        assert any("GraphQL" in d for d in descriptions)
        assert not any("sentiment" in d.lower() for d in descriptions)


class TestPromptInjection:
    """Test that rejected suggestions are included in the LLM prompt."""

    def test_build_prompt_includes_rejections(self):
        from agents.job.prompts.analyze_fit import build_prompt

        rejections = [
            {"suggestion_text": "Emphasize LLM sentiment analysis", "original_bullet": "feedback system for emails", "reason": "Not accurate"},
        ]

        prompt = build_prompt(
            original_resume="Test resume",
            knowledge={"experiences": [], "skills": []},
            job={"title": "SWE", "parsed_data": {"required_skills": ["Python"]}},
            rejections=rejections,
        )

        assert "LLM sentiment analysis" in prompt
        assert "NOT suggest" in prompt or "avoid" in prompt.lower() or "rejected" in prompt.lower()
