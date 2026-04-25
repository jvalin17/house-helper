"""Prompt for generating a tailored cover letter."""

import json


def build_prompt(knowledge: dict, job: dict, preferences: dict) -> str:
    job_title = job.get("title", "the position")
    company = job.get("company", "the company")
    parsed = job.get("parsed_data", {})
    required_skills = parsed.get("required_skills", [])

    tone = preferences.get("tone", "professional")

    return f"""Write a cover letter for the following job application:

**Position:** {job_title} at {company}
**Required Skills:** {', '.join(required_skills)}

**Candidate's Background:**
{json.dumps(knowledge, indent=2, default=str)}

**Tone:** {tone}

Instructions:
1. Address to "Dear Hiring Manager"
2. Open with enthusiasm for the specific role and company
3. Highlight 2-3 most relevant experiences that match the job requirements
4. Include specific achievements with metrics where available
5. Close with a call to action
6. Keep it concise — 3-4 paragraphs max
7. Output clean Markdown

Return only the cover letter, no explanations."""


SYSTEM_PROMPT = "You are an expert cover letter writer. Create compelling, personalized cover letters that connect the candidate's experience to the specific job requirements."
