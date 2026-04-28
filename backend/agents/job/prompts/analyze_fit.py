"""Prompt for analyzing resume-to-job fit BEFORE generating a new resume.

This is step 1 — analysis only. No resume generation.
Returns: current match, knowledge bank match, suggested improvements.
User picks which suggestions to apply, THEN we generate.
"""

import json


def _build_rejections_section(rejections: list[dict] | None) -> str:
    """Build the rejected suggestions section for the prompt."""
    if not rejections:
        return ""

    lines = [
        "**REJECTED SUGGESTIONS — do NOT suggest these again:**",
        "The user has explicitly marked these suggestions as incorrect. Do NOT suggest similar changes.",
    ]
    for rej in rejections:
        lines.append(f"- REJECTED: \"{rej.get('suggestion_text', '')}\"")
        if rej.get("original_bullet"):
            lines.append(f"  Original bullet: \"{rej['original_bullet']}\"")
        if rej.get("reason"):
            lines.append(f"  Reason: {rej['reason']}")
    lines.append("")
    return "\n".join(lines)


def build_prompt(
    original_resume: str,
    knowledge: dict,
    job: dict,
    rejections: list[dict] | None = None,
) -> str:
    job_title = job.get("title", "the position")
    company = job.get("company", "the company")
    parsed = job.get("parsed_data", {})
    required_skills = parsed.get("required_skills", [])
    job_desc = parsed.get("description", "")

    return f"""Analyze how well this candidate's CURRENT RESUME matches a specific job.
Then analyze how much ADDITIONAL knowledge they have that could improve the match.

**Target Job:** {job_title} at {company}
**Required Skills:** {', '.join(required_skills)}
**Job Description:** {job_desc[:1500]}

**Current Resume (what they'd submit today):**
{original_resume[:3000]}

**Full Knowledge Bank (ALL their experience, including things NOT on the resume):**
{json.dumps(knowledge, indent=2, default=str)}

Return ONLY this JSON:
{{
  "current_resume_match": 65,
  "knowledge_bank_match": 82,
  "match_gap": "+17% possible with resume edits",

  "strengths": ["strength from current resume that matches"],
  "gaps": ["skill or experience the job wants but resume doesn't show"],

  "suggested_improvements": [
    {{
      "type": "add_bullet",
      "description": "Add ML/AI sub-section under Skills — your LLM sentiment analysis and recommendation system work are buried in Zillow bullets",
      "impact": "+5%",
      "source": "Already in knowledge bank — Zillow experience"
    }},
    {{
      "type": "reword_bullet",
      "description": "Reword 'Built notification pipeline' to emphasize distributed processing and throughput — e.g., 'Designed event-driven notification system processing 2M+ daily deliveries'",
      "impact": "+3%",
      "source": "Same experience, better framing for the era"
    }},
    {{
      "type": "add_project",
      "description": "Add FileComparison project — shows Python tooling skills",
      "impact": "+2%",
      "source": "Knowledge bank — projects"
    }},
    {{
      "type": "cover_letter_only",
      "description": "Address Kubernetes gap in cover letter — 'I haven't shipped K8s in production but I've owned the deployment envelope around models'",
      "impact": "Addresses gap without fabricating",
      "source": "Honest framing"
    }},
    {{
      "type": "consider",
      "description": "This role may be a stretch — check if the company has backend/platform roles that better match your profile",
      "impact": "Better role fit",
      "source": "Career strategy"
    }}
  ],

  "summary": "Your current resume shows 65% match. With edits from your knowledge bank, you could reach 82%. The main gaps are [X, Y] which should be addressed in the cover letter rather than fabricated."
}}

{_build_rejections_section(rejections)}

Rules:
1. Be HONEST about gaps — don't sugar-coat
2. Only suggest improvements from REAL knowledge bank data
3. For missing skills: suggest cover letter framing, not fabrication
4. Include strategic advice (is this the right role? better alternatives?)
5. Each suggestion has type, description, impact, and source
6. NEVER add modern buzzwords to old experience. If someone built a notification pipeline in 2018, do NOT reframe it as "ML inference" or "AI-driven" unless ML/AI were actually involved. Use terminology accurate to what was done at the time. Emphasize scale, throughput, architecture — not retroactive AI labeling.
7. Return valid JSON only"""


SYSTEM_PROMPT = "You are a career strategist. You give honest, specific, actionable resume advice. You never suggest fabricating experience. You tell candidates when a role might not be the best fit."
