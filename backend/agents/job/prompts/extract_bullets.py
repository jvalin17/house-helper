"""Prompt for extracting experience and project data from page content.

Given raw text from a URL (portfolio, LinkedIn, GitHub, project page), the LLM
extracts structured work experiences AND project descriptions.
"""

import json
import re

MAX_TEXT_LENGTH = 5000

SYSTEM_PROMPT = """You are a knowledge extractor for a job application tool. You read page content and extract TWO types of information:

1. **Work Experiences** — jobs, roles, positions with achievement bullets
2. **Projects** — software projects, open source work, side projects with what was built

STRICT RULES:
1. ONLY extract what is EXPLICITLY described in the text
2. Do NOT infer or fabricate — only extract what the text clearly states
3. For experiences: include company, job title, and action-oriented achievement bullets
4. For projects: include project name, description, and technologies used
5. Keep bullet text concise — one line per achievement
6. Preserve specific numbers, metrics, and technologies mentioned

Return JSON in this exact format:
{
  "experiences": [
    {
      "company": "Company Name",
      "title": "Job Title",
      "bullets": ["Achievement 1", "Achievement 2"]
    }
  ],
  "projects": [
    {
      "name": "Project Name",
      "description": "What the project does",
      "tech_stack": "Python, React, etc."
    }
  ]
}

If the page has no work experiences, return an empty experiences array.
If the page has no projects, return an empty projects array."""


def build_prompt(page_text: str) -> str:
    """Build the user prompt for knowledge extraction from a page."""
    truncated_text = page_text[:MAX_TEXT_LENGTH]
    return f"""Extract work experiences and projects from this page content.

<page_content>
{truncated_text}
</page_content>

Return JSON with experiences and projects arrays. Return empty arrays for types not found on this page."""


def parse_bullet_response(llm_response: str) -> dict:
    """Parse the LLM response into experiences and projects."""
    cleaned_response = llm_response.strip()

    # Strip markdown code blocks
    if cleaned_response.startswith("```"):
        cleaned_response = re.sub(r"^```(?:json)?\s*", "", cleaned_response)
        cleaned_response = re.sub(r"\s*```$", "", cleaned_response)

    try:
        parsed = json.loads(cleaned_response)
        experiences = parsed.get("experiences", [])
        projects = parsed.get("projects", [])
        if not isinstance(experiences, list):
            experiences = []
        if not isinstance(projects, list):
            projects = []
        return {"experiences": experiences, "projects": projects}
    except (json.JSONDecodeError, AttributeError):
        return {"experiences": [], "projects": []}
