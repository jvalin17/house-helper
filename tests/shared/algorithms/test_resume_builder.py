"""Tests for resume_builder — template-based resume assembly without LLM."""

from shared.algorithms.resume_builder import build_resume, build_cover_letter


SAMPLE_KNOWLEDGE = {
    "experiences": [
        {
            "title": "Senior Software Engineer",
            "company": "TechCorp",
            "start_date": "2021-01",
            "end_date": "2024-03",
            "description": "Built microservices with Python and FastAPI",
        },
        {
            "title": "Software Engineer",
            "company": "StartupInc",
            "start_date": "2018-06",
            "end_date": "2020-12",
            "description": "Full-stack development with React and Node.js",
        },
    ],
    "skills": [
        {"name": "Python", "category": "language"},
        {"name": "React", "category": "framework"},
        {"name": "Docker", "category": "tool"},
        {"name": "FastAPI", "category": "framework"},
    ],
    "achievements": [
        {
            "description": "Reduced API latency by 40%",
            "metric": "40% reduction",
            "experience_id": 1,
        },
    ],
    "education": [
        {
            "institution": "State University",
            "degree": "BS",
            "field": "Computer Science",
            "end_date": "2018-05",
        },
    ],
    "projects": [
        {
            "name": "OpenSource CLI Tool",
            "description": "A developer productivity tool",
            "tech_stack": ["Python", "Click"],
        },
    ],
}

SAMPLE_JOB = {
    "title": "Backend Engineer",
    "company": "BigTech",
    "parsed_data": {
        "required_skills": ["Python", "FastAPI", "Docker"],
        "preferred_skills": ["Kubernetes", "AWS"],
    },
}


class TestBuildResume:
    """Build a resume from knowledge bank + job + preferences."""

    def test_returns_markdown_string(self):
        result = build_resume(SAMPLE_KNOWLEDGE, SAMPLE_JOB, {})
        assert isinstance(result, str)
        assert len(result) > 100

    def test_contains_experience(self):
        result = build_resume(SAMPLE_KNOWLEDGE, SAMPLE_JOB, {})
        assert "TechCorp" in result
        assert "Senior Software Engineer" in result

    def test_contains_skills(self):
        result = build_resume(SAMPLE_KNOWLEDGE, SAMPLE_JOB, {})
        assert "Python" in result

    def test_contains_education(self):
        result = build_resume(SAMPLE_KNOWLEDGE, SAMPLE_JOB, {})
        assert "State University" in result

    def test_contains_achievements(self):
        result = build_resume(SAMPLE_KNOWLEDGE, SAMPLE_JOB, {})
        assert "40%" in result

    def test_respects_sections_preference(self):
        prefs = {"sections": ["experience", "skills"]}
        result = build_resume(SAMPLE_KNOWLEDGE, SAMPLE_JOB, prefs)
        assert "TechCorp" in result
        assert "Python" in result
        # Education excluded
        assert "State University" not in result

    def test_empty_knowledge_bank(self):
        empty_kb = {
            "experiences": [],
            "skills": [],
            "achievements": [],
            "education": [],
            "projects": [],
        }
        result = build_resume(empty_kb, SAMPLE_JOB, {})
        assert isinstance(result, str)


class TestBuildCoverLetter:
    """Build a cover letter from knowledge bank + job."""

    def test_returns_markdown_string(self):
        result = build_cover_letter(SAMPLE_KNOWLEDGE, SAMPLE_JOB, {})
        assert isinstance(result, str)
        assert len(result) > 50

    def test_mentions_company(self):
        result = build_cover_letter(SAMPLE_KNOWLEDGE, SAMPLE_JOB, {})
        assert "BigTech" in result

    def test_mentions_role(self):
        result = build_cover_letter(SAMPLE_KNOWLEDGE, SAMPLE_JOB, {})
        assert "Backend Engineer" in result

    def test_mentions_relevant_skills(self):
        result = build_cover_letter(SAMPLE_KNOWLEDGE, SAMPLE_JOB, {})
        assert "Python" in result

    def test_empty_knowledge_bank(self):
        empty_kb = {
            "experiences": [],
            "skills": [],
            "achievements": [],
            "education": [],
            "projects": [],
        }
        result = build_cover_letter(empty_kb, SAMPLE_JOB, {})
        assert isinstance(result, str)
        assert "BigTech" in result
