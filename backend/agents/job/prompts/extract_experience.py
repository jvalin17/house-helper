"""Prompt for extracting structured experience from free text."""


def build_prompt(text: str) -> str:
    return f"""Extract structured work experience from the following text.
Return JSON with this structure:
{{
  "experiences": [
    {{"title": "...", "company": "...", "start_date": "YYYY-MM", "end_date": "YYYY-MM or null", "description": "..."}}
  ],
  "skills": ["skill1", "skill2"],
  "achievements": [{{"description": "...", "metric": "..."}}]
}}

Text:
{text}

Return only valid JSON, no markdown fences."""


SYSTEM_PROMPT = "You are a resume parser. Extract structured data from unstructured text. Be precise with dates and job titles."
