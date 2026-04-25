"""Prompt for generating a tailored resume."""

import json


def build_prompt(knowledge: dict, job: dict, preferences: dict) -> str:
    job_title = job.get("title", "the position")
    company = job.get("company", "the company")
    parsed = job.get("parsed_data", {})
    required_skills = parsed.get("required_skills", [])

    length = preferences.get("length", "1 page")
    tone = preferences.get("tone", "professional")
    sections = preferences.get("sections", ["summary", "experience", "skills", "education", "projects"])

    return f"""Generate a tailored resume in Markdown format for the following job:

**Position:** {job_title} at {company}
**Required Skills:** {', '.join(required_skills)}

**Candidate's Knowledge Bank:**
{json.dumps(knowledge, indent=2, default=str)}

**Preferences:**
- Length: {length}
- Tone: {tone}
- Sections to include: {', '.join(sections)}

Instructions:
1. Select the most relevant experiences, skills, and achievements that match this job
2. Frame bullet points to emphasize relevant skills and impact
3. Use quantified achievements where available
4. Keep it to {length}
5. Use a {tone} tone
6. Output clean Markdown with ## headers for each section

Return only the resume in Markdown, no explanations."""


SYSTEM_PROMPT = "You are an expert resume writer. Create tailored, ATS-friendly resumes that highlight the candidate's most relevant experience for each specific job posting."
