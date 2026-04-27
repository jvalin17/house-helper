"""Prompt for generating a tailored resume — preserves user's exact format."""

import json


def build_prompt(knowledge: dict, job: dict, preferences: dict, original_resume: str | None = None) -> str:
    job_title = job.get("title", "the position")
    company = job.get("company", "the company")
    parsed = job.get("parsed_data", {})
    required_skills = parsed.get("required_skills", [])

    if original_resume:
        return f"""You are editing a resume for a specific job application.

STRICT RULES:
1. Keep the EXACT same format, spacing, section headers, and layout as the original
2. Keep the candidate's REAL name, contact info, titles, and companies — never change these
3. Keep it to 1 page — same length as original
4. Only modify: bullet point WORDING to emphasize relevant skills
5. You may REORDER bullet points within each role to put the most relevant ones first
6. You may swap which projects are shown if knowledge bank has alternatives that match better
7. Do NOT add any experience, skill, or achievement not in the knowledge bank
8. Do NOT change section headers (SUMMARY, TECHNICAL SKILLS, WORK EXPERIENCE, etc.)
9. In SUMMARY: adjust the focus toward the target role but keep the same length and style
10. In TECHNICAL SKILLS: keep the same categories, you may reorder skills within each category

**Target Job:** {job_title} at {company}
**Required Skills:** {', '.join(required_skills)}

**Original Resume (MATCH THIS FORMAT EXACTLY):**
{original_resume}

**Full Knowledge Bank (use for alternative experiences/projects if they match better):**
{json.dumps(knowledge, indent=2, default=str)}

After the resume, add a section:
---
MATCH ANALYSIS:
- Estimated match: X%
- Strengths: [what matches well]
- Gaps: [what's missing]
- Suggestions: [what the candidate could do to improve their match]

Return the resume followed by the match analysis."""

    # Fallback if no original resume
    return f"""Generate a 1-page resume for this job using ONLY the candidate's real data.

**Position:** {job_title} at {company}
**Required Skills:** {', '.join(required_skills)}

**Candidate's Knowledge Bank:**
{json.dumps(knowledge, indent=2, default=str)}

Rules:
1. Use the candidate's REAL name and titles — never invent
2. Do NOT fabricate experience or skills
3. Keep to 1 page
4. After the resume, add match analysis with estimated %, strengths, gaps, suggestions

Return the resume followed by match analysis."""


SYSTEM_PROMPT = "You are a resume editor. You make minimal, precise edits to existing resumes to better match specific jobs. You never change the format, never invent details, and always preserve the candidate's real information. Keep the exact same visual structure."
