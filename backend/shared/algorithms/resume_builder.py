"""Template-based resume and cover letter assembly.

No LLM needed — selects relevant entries from the knowledge bank
and assembles them into structured markdown documents.
This is the offline fallback when no LLM provider is configured.
"""

ALL_SECTIONS = ["experience", "skills", "achievements", "education", "projects"]


def build_resume(
    knowledge: dict,
    job: dict,
    preferences: dict,
) -> str:
    """Build a resume in markdown from knowledge bank data.

    Args:
        knowledge: Dict with experiences, skills, achievements, education, projects.
        job: Parsed job posting with title, company, parsed_data.
        preferences: User prefs (sections, length, tone — used to filter content).
    """
    sections = preferences.get("sections", ALL_SECTIONS)
    parts = []

    if "experience" in sections:
        parts.append(_build_experience_section(knowledge.get("experiences", [])))

    if "skills" in sections:
        parts.append(_build_skills_section(knowledge.get("skills", []), job))

    if "achievements" in sections:
        parts.append(_build_achievements_section(knowledge.get("achievements", [])))

    if "education" in sections:
        parts.append(_build_education_section(knowledge.get("education", [])))

    if "projects" in sections:
        parts.append(_build_projects_section(knowledge.get("projects", [])))

    # Filter out empty sections
    parts = [p for p in parts if p.strip()]

    return "\n\n".join(parts)


def build_cover_letter(
    knowledge: dict,
    job: dict,
    preferences: dict,
) -> str:
    """Build a cover letter in markdown from knowledge bank data."""
    job_title = job.get("title", "the position")
    company = job.get("company", "your company")
    parsed = job.get("parsed_data", {})
    required_skills = parsed.get("required_skills", [])

    user_skills = [s["name"] for s in knowledge.get("skills", [])]
    matching_skills = [s for s in required_skills if s in user_skills]
    experiences = knowledge.get("experiences", [])

    lines = [
        f"# Cover Letter — {job_title} at {company}",
        "",
        f"Dear Hiring Manager,",
        "",
        f"I am writing to express my interest in the {job_title} position at {company}.",
    ]

    if matching_skills:
        skills_str = ", ".join(matching_skills)
        lines.append(
            f" I bring hands-on experience with {skills_str}, "
            f"which aligns with your requirements."
        )

    if experiences:
        most_recent = experiences[0]
        lines.append(
            f" Most recently, I worked as {most_recent['title']} "
            f"at {most_recent['company']}, where {most_recent.get('description', 'I contributed to key initiatives')}."
        )

    lines.extend([
        "",
        "I look forward to discussing how my experience can contribute to your team.",
        "",
        "Best regards",
    ])

    return "\n".join(lines)


def _build_experience_section(experiences: list[dict]) -> str:
    if not experiences:
        return ""

    lines = ["## Experience", ""]
    for exp in experiences:
        date_range = _format_date_range(exp.get("start_date"), exp.get("end_date"))
        lines.append(f"### {exp.get('title', 'Role')} — {exp.get('company', 'Company')}")
        lines.append(f"*{date_range}*")
        if exp.get("description"):
            lines.append(f"\n{exp['description']}")
        lines.append("")

    return "\n".join(lines)


def _build_skills_section(skills: list[dict], job: dict) -> str:
    if not skills:
        return ""

    # Group by category
    by_category: dict[str, list[str]] = {}
    for skill in skills:
        category = skill.get("category", "other")
        by_category.setdefault(category, []).append(skill["name"])

    lines = ["## Skills", ""]
    for category, skill_names in by_category.items():
        label = category.replace("_", " ").title()
        lines.append(f"**{label}:** {', '.join(skill_names)}")

    return "\n".join(lines)


def _build_achievements_section(achievements: list[dict]) -> str:
    if not achievements:
        return ""

    lines = ["## Key Achievements", ""]
    for achievement in achievements:
        desc = achievement.get("description", "")
        metric = achievement.get("metric", "")
        if metric:
            lines.append(f"- {desc} ({metric})")
        else:
            lines.append(f"- {desc}")

    return "\n".join(lines)


def _build_education_section(education: list[dict]) -> str:
    if not education:
        return ""

    lines = ["## Education", ""]
    for edu in education:
        degree = edu.get("degree", "")
        field = edu.get("field", "")
        institution = edu.get("institution", "")
        end_date = edu.get("end_date", "")

        degree_str = f"{degree} in {field}" if degree and field else degree or field
        date_str = f" ({end_date})" if end_date else ""
        lines.append(f"**{degree_str}** — {institution}{date_str}")

    return "\n".join(lines)


def _build_projects_section(projects: list[dict]) -> str:
    if not projects:
        return ""

    lines = ["## Projects", ""]
    for project in projects:
        name = project.get("name", "Project")
        desc = project.get("description", "")
        tech = project.get("tech_stack", [])
        # tech_stack may be a JSON string from DB — parse it
        if isinstance(tech, str):
            import json
            try:
                tech = json.loads(tech)
            except (json.JSONDecodeError, TypeError):
                tech = []

        lines.append(f"### {name}")
        if desc:
            lines.append(desc)
        if tech and isinstance(tech, list):
            lines.append(f"\n*Tech: {', '.join(tech)}*")
        lines.append("")

    return "\n".join(lines)


def _format_date_range(start: str | None, end: str | None) -> str:
    start_str = start or "Unknown"
    end_str = end or "Present"
    return f"{start_str} — {end_str}"
