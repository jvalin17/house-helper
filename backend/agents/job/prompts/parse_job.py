"""Prompt for parsing a job posting into structured data."""


def build_prompt(text: str) -> str:
    return f"""Parse this job posting and extract structured data.
Return JSON with this structure:
{{
  "title": "Job Title",
  "company": "Company Name",
  "location": "City, State",
  "remote_status": "remote|hybrid|onsite|null",
  "salary_range": "$X - $Y or null",
  "required_skills": ["skill1", "skill2"],
  "preferred_skills": ["skill1", "skill2"],
  "experience_years": "X+ years or null",
  "education": "degree requirement or null",
  "description": "brief summary of the role"
}}

Job Posting:
{text}

Return only valid JSON, no markdown fences."""


SYSTEM_PROMPT = "You are a job posting parser. Extract structured data from job descriptions. Be precise and only include information explicitly stated in the posting."
