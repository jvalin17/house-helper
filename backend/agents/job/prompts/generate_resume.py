"""Prompt for resume content decisions — Claude returns JSON, our code assembles.

Claude analyzes ALL knowledge bank data against the job and decides:
1. Which bullets to keep, swap, or reword per role
2. Whether side projects should be added as RELEVANT PROJECTS section
3. What the match improvement is vs the original resume
"""

import json


def build_prompt(knowledge: dict, job: dict, preferences: dict, original_resume: str | None = None) -> str:
    job_title = job.get("title", "the position")
    company = job.get("company", "the company")
    parsed = job.get("parsed_data", {})
    required_skills = parsed.get("required_skills", [])
    job_desc = parsed.get("description", "")
    max_bullets = preferences.get("max_bullets", 6)
    allow_2_pages = preferences.get("allow_2_pages", False)

    return f"""You are optimizing a resume for a specific job. Analyze ALL the candidate's knowledge
(experiences, side projects, achievements from any source) against this job posting.

**Target Job:** {job_title} at {company}
**Required Skills:** {', '.join(required_skills)}
**Job Description:** {job_desc[:1500]}

**Candidate's FULL Knowledge Bank (includes resume + side projects + extra achievements):**
{json.dumps(knowledge, indent=2, default=str)}

{"**Original Resume Text:**" + chr(10) + original_resume[:2000] if original_resume else ""}

Your task: select the BEST content from the ENTIRE knowledge bank to maximize match with this job.

Return ONLY this JSON:
{{
  "summary": "2-3 sentence summary tailored for this role",
  "experience_edits": [
    {{
      "company": "CompanyName",
      "title": "Their actual title",
      "bullets": [
        "most relevant bullet, reworded to emphasize matching skills",
        "second most relevant bullet"
      ],
      "swaps": [
        {{
          "removed": "original bullet that was less relevant",
          "added": "knowledge bank bullet that matches better",
          "reason": "Docker experience matches job requirement",
          "match_improvement": "+3%"
        }}
      ]
    }}
  ],
  "relevant_projects": [
    {{
      "name": "ProjectName",
      "description": "why this project is relevant to the job",
      "tech_stack": ["relevant", "technologies"]
    }}
  ],
  "original_match_percent": 63,
  "new_match_percent": 73,
  "match_improvement": "+10%",
  "skills_to_highlight": ["Python", "Kafka"],
  "strengths": ["strength 1"],
  "gaps": ["gap 1"],
  "suggestions": ["suggestion to improve match further"]
}}

Rules:
1. Use ONLY real data from the knowledge bank — NEVER fabricate
2. Keep real job titles, companies, dates
3. Max {max_bullets} bullets per role — replace weak ones with stronger matches from knowledge bank
4. If a side project or unlisted achievement matches better than a current bullet, SWAP it and explain why
5. Include relevant_projects ONLY if they meaningfully increase the match
6. {"Allow up to 2 pages of content if knowledge bank has strong matches" if allow_2_pages else "Keep to 1 page — replace, don't add"}
7. Show the match improvement: original % vs new %
8. Return valid JSON only, no markdown fences"""


SYSTEM_PROMPT = "You are a resume optimization expert. You select the best content from a candidate's full knowledge bank to maximize job match. You explain every swap. You never fabricate. Return only valid JSON."
