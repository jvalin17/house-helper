"""Prompt for resume content decisions — Claude returns JSON, our code assembles.

Claude NEVER generates the resume format. It only decides:
1. Summary reworded for the target role
2. Which bullets to keep/reword per role
3. Skills to highlight

Our code uses these decisions + the user's original template to assemble the final doc.
"""

import json


def build_prompt(knowledge: dict, job: dict, preferences: dict, original_resume: str | None = None) -> str:
    job_title = job.get("title", "the position")
    company = job.get("company", "the company")
    parsed = job.get("parsed_data", {})
    required_skills = parsed.get("required_skills", [])
    job_desc = parsed.get("description", "")

    return f"""Analyze this candidate's fit for a job and return content decisions as JSON.
Do NOT write a resume. Just return structured decisions that will be used to fill a template.

**Target Job:** {job_title} at {company}
**Required Skills:** {', '.join(required_skills)}
**Job Description:** {job_desc[:1000]}

**Candidate's Knowledge Bank:**
{json.dumps(knowledge, indent=2, default=str)}

Return ONLY this JSON structure:
{{
  "summary": "2-3 sentence summary tailored for this role (use candidate's real experience, never fabricate)",
  "experience_edits": [
    {{
      "company": "Zillow",
      "title": "Software Engineer",
      "bullets": [
        "reworded bullet emphasizing relevant skills for this job",
        "another reworded bullet",
        "keep max 6 bullets per role, prioritize most relevant"
      ]
    }}
  ],
  "skills_to_highlight": ["Python", "Kafka", "Docker"],
  "match_percent": 75,
  "strengths": ["relevant strength 1", "strength 2"],
  "gaps": ["missing skill or experience"],
  "suggestions": ["what candidate could do to improve match"]
}}

Rules:
1. Use ONLY real data from the knowledge bank — never fabricate
2. Keep the candidate's real job titles and companies
3. Reword bullets to emphasize skills matching: {', '.join(required_skills)}
4. Max 6 bullets per role, put most relevant first
5. Summary should mention the target role type naturally
6. Return valid JSON only, no markdown fences"""


SYSTEM_PROMPT = "You are a career advisor. You analyze job fit and suggest content edits for resumes. You never fabricate experience. Return only valid JSON."
