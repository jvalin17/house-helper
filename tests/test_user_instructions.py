"""TDD tests for user instructions in resume generation.

The user can type custom instructions on the analysis screen
(e.g., "Show 6 years experience", "Focus on backend only").
These are passed to the LLM generate prompt.
"""

import pytest

from agents.job.prompts.generate_resume import build_prompt


class TestUserInstructionsInPrompt:
    def test_instructions_included_in_prompt(self):
        """User instructions should appear in the generate prompt."""
        preferences = {
            "user_instructions": "Show only 6 years of experience, skip the AutomationCo role entirely",
        }
        prompt = build_prompt(
            knowledge={"experiences": [], "skills": []},
            job={"title": "SWE", "parsed_data": {"required_skills": ["Python"]}},
            preferences=preferences,
            original_resume="SUMMARY\nTest resume\nWORK EXPERIENCE\nTestCo | Eng\tJan 2020",
        )
        assert "6 years" in prompt
        assert "skip the AutomationCo" in prompt.lower() or "AutomationCo" in prompt

    def test_no_instructions_no_section(self):
        """When no instructions provided, prompt should not have an instructions section."""
        preferences = {}
        prompt = build_prompt(
            knowledge={"experiences": [], "skills": []},
            job={"title": "SWE", "parsed_data": {"required_skills": ["Python"]}},
            preferences=preferences,
            original_resume="SUMMARY\nTest resume",
        )
        assert "Additional instructions" not in prompt
        assert "user_instructions" not in prompt.lower()

    def test_empty_instructions_ignored(self):
        """Empty string instructions should be treated same as no instructions."""
        preferences = {"user_instructions": "   "}
        prompt = build_prompt(
            knowledge={"experiences": [], "skills": []},
            job={"title": "SWE", "parsed_data": {"required_skills": ["Python"]}},
            preferences=preferences,
            original_resume="SUMMARY\nTest resume",
        )
        assert "Additional instructions" not in prompt

    def test_instructions_with_suggestions(self):
        """Instructions should work alongside selected suggestions."""
        preferences = {
            "user_instructions": "Target this as a mid-level role",
            "apply_suggestions": [
                {"type": "reword_bullet", "description": "Emphasize scale", "impact": "+3%", "source": "KB"},
            ],
        }
        prompt = build_prompt(
            knowledge={"experiences": [], "skills": []},
            job={"title": "SWE", "parsed_data": {"required_skills": ["Python"]}},
            preferences=preferences,
            original_resume="SUMMARY\nTest resume",
        )
        assert "mid-level" in prompt
        assert "Emphasize scale" in prompt

    def test_years_of_experience_instruction(self):
        """Common use case: user wants to show fewer years."""
        preferences = {
            "user_instructions": "Only show 4 years of most recent experience",
        }
        prompt = build_prompt(
            knowledge={"experiences": [], "skills": []},
            job={"title": "SWE", "parsed_data": {"required_skills": ["Python"]}},
            preferences=preferences,
            original_resume="SUMMARY\nTest resume",
        )
        assert "4 years" in prompt
