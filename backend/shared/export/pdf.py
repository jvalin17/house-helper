"""PDF exporter — converts resume content to PDF via WeasyPrint.

Handles both markdown format (from fallback builder) and plain text
format (from LLM template assembly). Detects format automatically.
"""

import re

import markdown
from weasyprint import HTML

BASE_CSS = """
@page {
    size: letter;
    margin: 0.4in 0.5in;
}
body {
    font-family: Arial, 'Helvetica Neue', sans-serif;
    font-size: 9.5pt;
    line-height: 1.3;
    color: #222;
    margin: 0;
    padding: 0;
}
h1 { font-size: 13pt; margin: 0; padding: 0; color: #1a1a1a; text-align: center; }
h2 {
    font-size: 9.5pt; font-weight: bold; text-transform: uppercase;
    margin: 6px 0 2px 0; padding-bottom: 1px;
    border-bottom: 0.5px solid #999; letter-spacing: 0.5px;
}
h3 { font-size: 9pt; font-weight: bold; margin: 4px 0 1px 0; }
.contact { font-size: 8pt; color: #555; margin: 0 0 4px 0; text-align: center; line-height: 1.3; }
.role-header { font-weight: bold; margin: 4px 0 0 0; font-size: 9pt; }
.role-dates { float: right; font-weight: normal; color: #555; font-size: 8pt; }
ul { padding-left: 14px; margin: 0 0 3px 0; }
li { margin-bottom: 0; font-size: 9pt; line-height: 1.25; }
p { margin: 1px 0; font-size: 9pt; }
"""

# Section headers in plain text resumes (ALL CAPS, short lines)
SECTION_HEADERS = {
    "SUMMARY", "PROFESSIONAL SUMMARY", "OBJECTIVE", "PROFILE",
    "WORK EXPERIENCE", "EXPERIENCE", "PROFESSIONAL EXPERIENCE", "EMPLOYMENT",
    "EDUCATION", "ACADEMIC",
    "TECHNICAL SKILLS", "SKILLS", "TECHNOLOGIES", "COMPETENCIES",
    "PROJECTS", "RELEVANT PROJECTS", "PERSONAL PROJECTS", "SIDE PROJECTS",
    "CERTIFICATIONS", "AWARDS", "ACHIEVEMENTS",
}

# Role header pattern: "Company | Title<tab>Dates" or "Company — Title  Dates"
ROLE_PATTERN = re.compile(r"^(.+?)\s*[|–—]\s*(.+?)(?:\t|\s{2,})(.+)$")


def _is_section_header(line: str) -> bool:
    stripped = line.strip().upper()
    return stripped in SECTION_HEADERS or any(stripped.startswith(h) for h in SECTION_HEADERS)


def _preprocess_lines(content: str) -> list[str]:
    """Clean up common plain-text resume artifacts before HTML conversion."""
    # Strip non-breaking spaces and zero-width chars
    content = content.replace("\u00a0", " ")
    content = re.sub(r"[\u200b\u200c\u200d\ufeff\u00ad]", "", content)
    raw = content.split("\n")
    result: list[str] = []
    i = 0
    while i < len(raw):
        line = raw[i].strip()

        # Skip empty lines
        if not line:
            result.append("")
            i += 1
            continue

        # Standalone bullet marker — join with next non-empty line
        if line in ("●", "•", "-", "◦"):
            if i + 1 < len(raw) and raw[i + 1].strip():
                result.append(f"- {raw[i + 1].strip()}")
                i += 2
                continue

        # Line starting with bullet marker
        if line.startswith("●") or line.startswith("•"):
            result.append(f"- {line.lstrip('●•').strip()}")
            i += 1
            continue

        # Standalone date line (e.g., "May 2016") — append to previous line
        if re.match(r"^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{4}$", line, re.IGNORECASE):
            if result and result[-1]:
                result[-1] = f"{result[-1]}\t{line}"
            else:
                result.append(line)
            i += 1
            continue

        result.append(line)
        i += 1

    return result


def _plain_text_to_html(content: str) -> str:
    """Convert plain text resume to structured HTML."""
    lines = _preprocess_lines(content)
    html_parts: list[str] = []
    in_bullets = False
    first_line = True
    contact_lines: list[str] = []

    for line in lines:
        stripped = line.strip() if line else ""
        if not stripped:
            if in_bullets:
                html_parts.append("</ul>")
                in_bullets = False
            # Flush contact lines when we hit a blank line after header
            if contact_lines and first_line:
                html_parts.append(f'<div class="contact">{" | ".join(contact_lines)}</div>')
                contact_lines = []
                first_line = False
            continue

        # Header zone: name + contact lines before first section
        if first_line:
            if not html_parts:  # very first line = name
                html_parts.append(f"<h1>{stripped}</h1>")
                continue
            if not _is_section_header(stripped):
                contact_lines.append(stripped)
                continue
            # Hit first section header — flush contact, end header zone
            if contact_lines:
                html_parts.append(f'<div class="contact">{"<br/>".join(contact_lines)}</div>')
                contact_lines = []
            first_line = False
            # fall through to section header handling

        # Section header (ALL CAPS)
        if _is_section_header(stripped):
            if in_bullets:
                html_parts.append("</ul>")
                in_bullets = False
            html_parts.append(f"<h2>{stripped.title()}</h2>")
            continue

        # Role header (Company | Title  Dates)
        role_match = ROLE_PATTERN.match(stripped)
        if role_match and not stripped.startswith("-") and not stripped.startswith("•"):
            if in_bullets:
                html_parts.append("</ul>")
                in_bullets = False
            company = role_match.group(1).strip()
            title = role_match.group(2).strip()
            dates = role_match.group(3).strip()
            html_parts.append(f'<div class="role-header"><strong>{company} | {title}</strong><span class="role-dates">{dates}</span></div>')
            continue

        # Skill category line (e.g., "Languages: Python, Java" or "- Proficient: Python, Java")
        clean_for_cat = stripped.lstrip("-•").strip()
        if ":" in clean_for_cat and len(clean_for_cat.split(":")[0].split()) <= 4:
            if in_bullets:
                html_parts.append("</ul>")
                in_bullets = False
            category = clean_for_cat.split(":")[0]
            rest = clean_for_cat[len(category) + 1:].strip()
            html_parts.append(f"<p><strong>{category}:</strong> {rest}</p>")
            continue

        # Bullet point
        if stripped.startswith("-") or stripped.startswith("•"):
            if not in_bullets:
                html_parts.append("<ul>")
                in_bullets = True
            bullet_text = stripped.lstrip("-•").strip()
            html_parts.append(f"<li>{bullet_text}</li>")
            continue

        # Regular paragraph
        html_parts.append(f"<p>{stripped}</p>")
        first_line = False

    if in_bullets:
        html_parts.append("</ul>")

    return "\n".join(html_parts)


def _is_markdown(content: str) -> bool:
    """Detect if content is markdown (has ## headers) vs plain text."""
    return bool(re.search(r"^#{1,3}\s", content, re.MULTILINE))


class PdfExporter:
    def export(self, content: str, metadata: dict) -> bytes:
        if _is_markdown(content):
            html_body = markdown.markdown(content)
        else:
            html_body = _plain_text_to_html(content)

        full_html = f"""
        <html>
        <head><style>{BASE_CSS}</style></head>
        <body>{html_body}</body>
        </html>
        """
        return HTML(string=full_html).write_pdf()

    def format_name(self) -> str:
        return "pdf"
