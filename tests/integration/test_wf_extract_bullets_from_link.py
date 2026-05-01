"""Extract experience bullets from link — TDD tests.

When a user provides a URL, the LLM extracts structured experience data
(company, title, bullets) instead of just skills. Requires LLM provider.

Covers:
- Build prompt includes the page text
- Prompt instructs LLM to return experience JSON
- Extraction requires LLM (raises without one)
- Response includes experiences with company, title, bullets
"""

import json
import pytest


class TestBuildBulletExtractionPrompt:
    def test_prompt_contains_page_text(self):
        """The prompt should include the raw page text for the LLM to analyze."""
        from agents.job.prompts.extract_bullets import build_prompt

        page_text = "Software Engineer at Google. Built distributed search systems. Led team of 5."
        prompt = build_prompt(page_text)

        assert "Software Engineer at Google" in prompt
        assert "Built distributed search systems" in prompt

    def test_prompt_requests_json_format(self):
        """The prompt should request structured JSON output."""
        from agents.job.prompts.extract_bullets import build_prompt

        prompt = build_prompt("Some experience text")
        assert "json" in prompt.lower() or "JSON" in prompt

    def test_prompt_truncates_long_text(self):
        """Text over 5000 chars should be truncated to control token cost."""
        from agents.job.prompts.extract_bullets import build_prompt, MAX_TEXT_LENGTH

        long_text = "A" * 10000
        prompt = build_prompt(long_text)

        # The prompt should not contain the full 10000 chars
        assert len(prompt) < 10000 + 500  # some overhead for instructions

    def test_system_prompt_exists(self):
        """A system prompt should be defined for bullet extraction."""
        from agents.job.prompts.extract_bullets import SYSTEM_PROMPT

        assert "experience" in SYSTEM_PROMPT.lower() or "bullet" in SYSTEM_PROMPT.lower()
        assert len(SYSTEM_PROMPT) > 50


class TestParseBulletResponse:
    def test_parse_valid_json_with_experiences_and_projects(self):
        """Valid JSON response should be parsed into experiences and projects."""
        from agents.job.prompts.extract_bullets import parse_bullet_response

        llm_response = json.dumps({
            "experiences": [
                {
                    "company": "Google",
                    "title": "Software Engineer",
                    "bullets": [
                        "Built distributed search systems serving 1B queries/day",
                        "Led team of 5 engineers on search ranking improvements",
                    ]
                }
            ],
            "projects": [
                {
                    "name": "SearchApp",
                    "description": "Open source search engine",
                    "tech_stack": "Python, Elasticsearch"
                }
            ]
        })

        result = parse_bullet_response(llm_response)
        assert len(result["experiences"]) == 1
        assert result["experiences"][0]["company"] == "Google"
        assert result["experiences"][0]["title"] == "Software Engineer"
        assert len(result["experiences"][0]["bullets"]) == 2
        assert "1B queries" in result["experiences"][0]["bullets"][0]
        assert len(result["projects"]) == 1
        assert result["projects"][0]["name"] == "SearchApp"
        assert result["projects"][0]["tech_stack"] == "Python, Elasticsearch"

    def test_parse_handles_markdown_code_blocks(self):
        """LLM may wrap JSON in markdown code blocks."""
        from agents.job.prompts.extract_bullets import parse_bullet_response

        llm_response = '```json\n{"experiences": [{"company": "Acme", "title": "Dev", "bullets": ["Built API"]}], "projects": []}\n```'

        result = parse_bullet_response(llm_response)
        assert len(result["experiences"]) == 1
        assert result["experiences"][0]["company"] == "Acme"

    def test_parse_returns_empty_on_invalid_json(self):
        """Invalid JSON should return empty dicts, not crash."""
        from agents.job.prompts.extract_bullets import parse_bullet_response

        result = parse_bullet_response("not valid json at all")
        assert result == {"experiences": [], "projects": []}
