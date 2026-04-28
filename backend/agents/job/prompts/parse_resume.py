"""Prompt for LLM-based resume parsing.

Used when the algorithmic parser can't extract structured data
(especially PDFs with messy text extraction).

Guardrails:
- ONLY extract what is explicitly in the text
- NEVER fabricate experiences, skills, or education
- Return empty arrays if a section doesn't exist
"""

SYSTEM_PROMPT = """You extract structured data from resume text. You return ONLY what is explicitly present in the text. You never infer, guess, or add information that isn't there."""


def build_prompt(text: str) -> str:
    return f"""Extract structured resume data from the text inside <resume_text> tags.

<resume_text>
{text[:4000]}
</resume_text>

Return ONLY this JSON structure. Every field must come directly from the text above.
If a section doesn't exist in the resume, return an empty array for it.

{{
  "experiences": [
    {{
      "company": "Company Name",
      "title": "Job Title",
      "start_date": "YYYY-MM or null",
      "end_date": "YYYY-MM or null (null means present)",
      "bullets": ["achievement 1", "achievement 2"]
    }}
  ],
  "skills": [
    {{"name": "Python", "category": "languages"}},
    {{"name": "AWS", "category": "cloud"}}
  ],
  "education": [
    {{
      "institution": "University Name",
      "degree": "BS/MS/PhD",
      "field": "Computer Science",
      "end_date": "YYYY-MM or null"
    }}
  ],
  "projects": [
    {{
      "name": "Project Name",
      "description": "What it does",
      "url": "github.com/... or null",
      "tech_stack": ["Python", "React"]
    }}
  ]
}}

Rules:
1. Extract ONLY what is in the text — never fabricate
2. Use YYYY-MM format for dates (e.g., "2022-10"). Convert "Oct 2022" to "2022-10"
3. For skills, categorize as: languages, frameworks, cloud, databases, tools, other
4. Bullets should be the actual achievement text, not summaries
5. Return valid JSON only, no markdown fences"""
