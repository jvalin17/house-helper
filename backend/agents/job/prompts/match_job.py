"""Prompt for deep job matching analysis."""

import json


def build_prompt(knowledge: dict, job: dict) -> str:
    job_title = job.get("title", "the position")
    company = job.get("company", "the company")
    parsed = job.get("parsed_data", {})

    return f"""Analyze how well this candidate matches the following job:

**Position:** {job_title} at {company}
**Job Requirements:**
{json.dumps(parsed, indent=2, default=str)}

**Candidate's Profile:**
{json.dumps(knowledge, indent=2, default=str)}

Provide a detailed analysis as JSON:
{{
  "overall_score": 0.0-1.0,
  "skills_analysis": {{
    "matched": ["skill1", "skill2"],
    "gaps": ["skill3"],
    "transferable": ["related skill that partially covers a gap"]
  }},
  "experience_analysis": "brief assessment of experience relevance",
  "strengths": ["strength1", "strength2"],
  "gaps": ["gap1", "gap2"],
  "recommendations": ["suggestion to strengthen application"]
}}

Return only valid JSON."""


SYSTEM_PROMPT = "You are a career advisor. Analyze job-candidate fit with honesty and specificity. Highlight both strengths and gaps."
