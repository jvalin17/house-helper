"""Prompt for generating a tailored resume — follows user's original format."""

import json


def build_prompt(knowledge: dict, job: dict, preferences: dict, original_resume: str | None = None) -> str:
    job_title = job.get("title", "the position")
    company = job.get("company", "the company")
    parsed = job.get("parsed_data", {})
    required_skills = parsed.get("required_skills", [])

    length = preferences.get("length", "1 page")
    tone = preferences.get("tone", "professional")

    if original_resume:
        return f"""Rewrite this resume tailored for the following job.
KEEP THE EXACT SAME FORMAT, STRUCTURE, AND SECTION ORDER as the original.
Only change the CONTENT to emphasize relevant experience for this role.

**Target Job:** {job_title} at {company}
**Required Skills:** {', '.join(required_skills)}

**Original Resume (FOLLOW THIS FORMAT EXACTLY):**
{original_resume}

**Candidate's Full Knowledge Bank (use for additional relevant details):**
{json.dumps(knowledge, indent=2, default=str)}

Rules:
1. Keep the SAME section headers, ordering, and layout as the original
2. Keep the candidate's REAL name, contact info, and dates
3. Do NOT invent a title — use the candidate's actual title
4. Rewrite bullet points to emphasize skills matching {', '.join(required_skills)}
5. Add quantified achievements where available in the knowledge bank
6. Do NOT fabricate any experience or skills not in the knowledge bank
7. Keep it to {length}
8. Output in Markdown

Return only the resume, no explanations."""

    # Fallback if no original resume available
    return f"""Generate a resume for the following job using ONLY the candidate's real data.

**Position:** {job_title} at {company}
**Required Skills:** {', '.join(required_skills)}

**Candidate's Knowledge Bank:**
{json.dumps(knowledge, indent=2, default=str)}

Rules:
1. Use the candidate's REAL name and titles — do NOT invent titles
2. Do NOT fabricate experience or skills
3. Use quantified achievements where available
4. Keep it to {length}, {tone} tone
5. Output in Markdown

Return only the resume, no explanations."""


SYSTEM_PROMPT = "You are a resume editor. You rewrite resumes to better match specific jobs while keeping the candidate's original format and real information. Never fabricate or invent details."
