"""Resume parser — extract structured data from DOCX/PDF resumes.

No LLM needed. Uses document structure (bold headers, date patterns,
bullet points) to identify sections and parse entries.
"""

import re
from pathlib import Path

from shared.algorithms.entity_extractor import extract_skills_from_text

# Section header patterns (case-insensitive)
SECTION_HEADERS = {
    "experience": re.compile(
        r"^(work\s+)?experience|employment(\s+history)?|professional\s+experience",
        re.IGNORECASE,
    ),
    "education": re.compile(r"^education|academic", re.IGNORECASE),
    "skills": re.compile(
        r"^(technical\s+)?skills|competencies|technologies|proficiencies",
        re.IGNORECASE,
    ),
    "projects": re.compile(r"^(side\s+)?projects|portfolio|personal\s+projects", re.IGNORECASE),
    "summary": re.compile(
        r"^(professional\s+)?summary|objective|profile|about",
        re.IGNORECASE,
    ),
    "certifications": re.compile(r"^certifications?|licenses?", re.IGNORECASE),
}

# Date patterns
MONTH_MAP = {
    "jan": "01", "january": "01", "feb": "02", "february": "02",
    "mar": "03", "march": "03", "apr": "04", "april": "04",
    "may": "05", "jun": "06", "june": "06",
    "jul": "07", "july": "07", "aug": "08", "august": "08",
    "sep": "09", "september": "09", "oct": "10", "october": "10",
    "nov": "11", "november": "11", "dec": "12", "december": "12",
}

DATE_PATTERN = re.compile(
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|"
    r"july?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\.?\s*(\d{4})",
    re.IGNORECASE,
)

# Experience line: "Company | Title<tab>Date – Date" or "Company — Title<tab>Date"
EXPERIENCE_LINE = re.compile(
    r"^(.+?)\s*[|–—-]\s*(.+?)(?:\t|\s{2,})(.+)$"
)

# Education line: "Degree, Institution<tab>Date"
EDUCATION_LINE = re.compile(
    r"^(.+?)(?:,\s*|\t|\s{2,})(.+?)(?:\t|\s{2,})(\w+\s+\d{4})$"
)

# Skills category: "Category: skill1, skill2, skill3"
SKILLS_CATEGORY = re.compile(r"^([^:]+):\s*(.+)$")


def parse_date(text: str) -> str | None:
    """Parse a date string into YYYY-MM format."""
    if not text or not text.strip():
        return None

    text = text.strip()
    if text.lower() in ("present", "current", "now"):
        return None

    match = DATE_PATTERN.search(text)
    if match:
        month_str = match.group(1).lower()
        year = match.group(2)
        month = MONTH_MAP.get(month_str, "01")
        return f"{year}-{month}"

    return None


def parse_experience_entry(line: str) -> dict:
    """Parse a 'Company | Title<tab>Date – Date' line."""
    match = EXPERIENCE_LINE.match(line.strip())
    if not match:
        return {"company": None, "title": line.strip(), "start_date": None, "end_date": None}

    part1 = match.group(1).strip()
    part2 = match.group(2).strip()
    date_part = match.group(3).strip()

    # Split date range on – or -
    dates = re.split(r"\s*[–—-]\s*", date_part, maxsplit=1)
    start_date = parse_date(dates[0]) if dates else None
    end_date = parse_date(dates[1]) if len(dates) > 1 else None

    return {
        "company": part1,
        "title": part2,
        "start_date": start_date,
        "end_date": end_date,
    }


def detect_sections(paragraphs: list[dict]) -> dict[str, list[dict]]:
    """Group paragraphs into detected sections."""
    sections: dict[str, list[dict]] = {}
    current_section = "header"
    sections["header"] = []

    for para in paragraphs:
        text = para["text"].strip()
        if not text:
            continue

        # Check if this is a section header
        matched_section = None
        if para.get("is_bold") or para.get("is_heading"):
            for section_name, pattern in SECTION_HEADERS.items():
                if pattern.match(text):
                    matched_section = section_name
                    break

        if matched_section:
            current_section = matched_section
            if current_section not in sections:
                sections[current_section] = []
            continue

        if current_section not in sections:
            sections[current_section] = []
        sections[current_section].append(para)

    return sections


def parse_resume_docx(file_path: Path) -> dict:
    """Parse a DOCX resume into structured data."""
    from docx import Document

    doc = Document(str(file_path))
    paragraphs = _extract_paragraphs_docx(doc)
    return _parse_paragraphs(paragraphs)


def parse_resume_pdf(file_path: Path) -> dict:
    """Parse a PDF resume into structured data."""
    import fitz

    doc = fitz.open(str(file_path))
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()

    # Strip zero-width unicode characters that break pattern matching
    text = re.sub(r"[\u200b\u200c\u200d\ufeff\u00ad]", "", text)

    # Pre-process: join standalone bullet markers (●, •) with the next line
    raw_lines = text.split("\n")
    joined_lines: list[str] = []
    i = 0
    while i < len(raw_lines):
        stripped = raw_lines[i].strip()
        # Standalone bullet marker — join with next non-empty line
        if stripped in ("●", "•", "-", "◦") and i + 1 < len(raw_lines):
            next_text = raw_lines[i + 1].strip()
            if next_text:
                joined_lines.append(f"- {next_text}")
                i += 2
                continue
        # Line starting with bullet marker
        if stripped.startswith("●") or stripped.startswith("•"):
            joined_lines.append(f"- {stripped.lstrip('●•').strip()}")
        else:
            joined_lines.append(stripped)
        i += 1

    # PDF doesn't give us formatting info easily, so treat each line as a paragraph
    paragraphs = []
    for stripped in joined_lines:
        if not stripped:
            continue
        # Heuristic: ALL CAPS or short bold-like lines are likely headers
        is_likely_header = stripped.isupper() and len(stripped) < 40
        is_list = stripped.startswith("- ")
        paragraphs.append({
            "text": stripped,
            "is_bold": is_likely_header,
            "is_heading": is_likely_header,
            "is_list": is_list,
            "style": "heading" if is_likely_header else ("list" if is_list else "body"),
        })

    return _parse_paragraphs(paragraphs)


def parse_resume(file_path: Path) -> dict:
    """Parse a resume file — auto-detects format from extension."""
    suffix = file_path.suffix.lower()

    if suffix == ".docx":
        return parse_resume_docx(file_path)
    elif suffix == ".pdf":
        return parse_resume_pdf(file_path)
    elif suffix == ".txt":
        text = file_path.read_text()
        paragraphs = [
            {"text": line.strip(), "is_bold": line.strip().isupper(), "is_heading": False, "style": "body"}
            for line in text.split("\n") if line.strip()
        ]
        return _parse_paragraphs(paragraphs)
    else:
        raise ValueError(
            f"Unsupported resume format: {suffix}. "
            f"Supported: .docx, .pdf, .txt"
        )


def _extract_paragraphs_docx(doc) -> list[dict]:
    """Extract paragraphs from a python-docx Document with formatting info."""
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        is_bold = any(run.bold for run in para.runs) if para.runs else False
        style_name = para.style.name if para.style else ""
        is_list = "list" in style_name.lower()

        paragraphs.append({
            "text": text,
            "is_bold": is_bold,
            "is_heading": "heading" in style_name.lower(),
            "style": style_name,
            "is_list": is_list,
        })

    return paragraphs


def _parse_paragraphs(paragraphs: list[dict]) -> dict:
    """Parse structured paragraphs into a resume data dict."""
    sections = detect_sections(paragraphs)

    contact = _parse_contact(sections.get("header", []))
    summary = _parse_summary(sections.get("summary", []))
    experiences = _parse_experiences(sections.get("experience", []))
    education = _parse_education(sections.get("education", []))
    skills = _parse_skills(sections.get("skills", []))
    projects = _parse_projects(sections.get("projects", []))

    return {
        "contact": contact,
        "summary": summary,
        "experiences": experiences,
        "education": education,
        "skills": skills,
        "projects": projects,
    }


def _parse_contact(paragraphs: list[dict]) -> dict:
    """Extract contact info from header paragraphs."""
    if not paragraphs:
        return {}

    name = paragraphs[0]["text"] if paragraphs else ""
    contact = {"name": name}

    for para in paragraphs[1:]:
        text = para["text"]
        if "@" in text or "email" in text.lower():
            contact["raw_contact"] = text
        if "linkedin" in text.lower() or "github" in text.lower():
            contact["raw_links"] = text

    return contact


def _parse_summary(paragraphs: list[dict]) -> str:
    """Extract summary text."""
    return " ".join(p["text"] for p in paragraphs).strip()


def _parse_experiences(paragraphs: list[dict]) -> list[dict]:
    """Parse experience section into structured entries."""
    experiences = []
    current_exp = None

    for para in paragraphs:
        text = para["text"]
        is_list = para.get("is_list") or para.get("style", "").lower().startswith("list")

        if is_list and current_exp:
            current_exp["bullets"].append(text)
        else:
            # Try to parse as experience header line
            entry = parse_experience_entry(text)
            if entry.get("company") and entry.get("start_date"):
                if current_exp:
                    experiences.append(current_exp)
                current_exp = {**entry, "bullets": []}
            elif current_exp:
                current_exp["bullets"].append(text)
            else:
                # First non-parseable line, might be a bullet without list style
                pass

    if current_exp:
        experiences.append(current_exp)

    return experiences


def _parse_education(paragraphs: list[dict]) -> list[dict]:
    """Parse education section into structured entries."""
    education = []

    for para in paragraphs:
        text = para["text"]

        # Try "Degree, Institution<tab>Date" pattern
        # Also handle "Degree in Field, Institution<tab>Date"
        parts = re.split(r"\t|\s{2,}", text, maxsplit=1)
        if len(parts) == 2:
            desc = parts[0].strip()
            date_text = parts[1].strip()
            date = parse_date(date_text)

            # Split desc into degree + institution
            # Pattern: "Degree in/of Field, Institution"
            degree_match = re.match(r"(.+?),\s*(.+)$", desc)
            if degree_match:
                degree_part = degree_match.group(1).strip()
                institution = degree_match.group(2).strip()
            else:
                degree_part = desc
                institution = ""

            # Extract degree and field
            field_match = re.match(r"(.+?)\s+(?:in|of)\s+(.+)", degree_part)
            if field_match:
                degree = field_match.group(1).strip()
                field = field_match.group(2).strip()
            else:
                degree = degree_part
                field = ""

            education.append({
                "degree": degree,
                "field": field,
                "institution": institution,
                "end_date": date,
            })

    return education


def _parse_skills(paragraphs: list[dict]) -> list[dict]:
    """Parse skills section into categorized skills."""
    skills = []
    seen = set()

    for para in paragraphs:
        text = para["text"]

        # Try "Category: skill1, skill2, skill3"
        cat_match = SKILLS_CATEGORY.match(text)
        if cat_match:
            category = cat_match.group(1).strip().lower()
            skill_text = cat_match.group(2)
            # Split on commas, pipes, semicolons
            for skill_name in re.split(r"[,;|]", skill_text):
                skill_name = skill_name.strip()
                # Remove parenthetical notes like "(MySQL/MSSQL)"
                skill_name = re.sub(r"\s*\([^)]*\)", "", skill_name).strip()
                if skill_name and skill_name.lower() not in seen:
                    seen.add(skill_name.lower())
                    skills.append({"name": skill_name, "category": category})
        else:
            # Fall back to skill pattern extraction
            extracted = extract_skills_from_text(text)
            for skill_name in extracted:
                if skill_name.lower() not in seen:
                    seen.add(skill_name.lower())
                    skills.append({"name": skill_name, "category": "extracted"})

    return skills


def _parse_projects(paragraphs: list[dict]) -> list[dict]:
    """Parse projects section into structured entries."""
    projects = []
    current_project = None

    for para in paragraphs:
        text = para["text"]
        is_list = para.get("is_list") or para.get("style", "").lower().startswith("list")

        if is_list and current_project:
            current_project["description"] = (
                current_project.get("description", "") + " " + text
            ).strip()
        else:
            # Project header: "Name | url" or just "Name"
            parts = re.split(r"\s*[|]\s*", text, maxsplit=1)
            name = parts[0].strip()
            url = parts[1].strip() if len(parts) > 1 else None

            if current_project:
                projects.append(current_project)

            current_project = {
                "name": name,
                "url": url,
                "description": "",
                "tech_stack": [],
            }

    if current_project:
        # Extract tech stack from description
        if current_project["description"]:
            current_project["tech_stack"] = extract_skills_from_text(
                current_project["description"]
            )
        projects.append(current_project)

    return projects
