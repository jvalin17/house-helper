"""TDD tests for matching jobs against a specific resume (not full KB).

When a saved resume is selected, TF-IDF and semantic matching should
use the resume's content text, not the full knowledge bank experiences.
Skills are still matched from KB (they represent the user's full skill set).
"""

import json
from pathlib import Path

import pytest

from shared.db import connect_sync
from agents.job.repositories.knowledge_repo import KnowledgeRepository
from agents.job.repositories.job_repo import JobRepository
from agents.job.services.job_matcher import JobMatcherService


@pytest.fixture
def db():
    conn = connect_sync(db_path=Path(":memory:"))
    # Create a job
    conn.execute(
        "INSERT INTO jobs (id, title, company, parsed_data) VALUES (1, 'Python Engineer', 'Acme', ?)",
        (json.dumps({"required_skills": ["Python", "AWS", "Docker"], "description": "Build Python microservices on AWS"}),),
    )
    conn.commit()
    return conn


@pytest.fixture
def kb(db):
    repo = KnowledgeRepository(db)
    repo.save_skill(name="Python", category="languages")
    repo.save_skill(name="Java", category="languages")
    repo.save_skill(name="AWS", category="cloud")
    repo.save_experience(type="job", title="SWE", company="BigCo",
                        description="Built Java microservices\nManaged AWS infrastructure\nLed Docker deployments")
    return repo


class TestMatchWithResume:
    def test_match_without_resume_uses_kb(self, db, kb):
        """Default: matching uses full KB experience text."""
        jr = JobRepository(db)
        svc = JobMatcherService(kb, jr)
        result = svc.match_job(1)
        assert result["score"] > 0

    def test_match_with_resume_text(self, db, kb):
        """When resume_text is provided, TF-IDF uses it instead of KB experiences."""
        jr = JobRepository(db)
        svc = JobMatcherService(kb, jr)

        # Resume that's very relevant to Python + AWS
        resume_text = "Python developer with 5 years AWS experience building microservices and Docker containers"
        result_with_resume = svc.match_job(1, resume_text=resume_text)

        # Resume that's irrelevant
        irrelevant_resume = "Graphic designer specializing in print media and illustration"
        result_irrelevant = svc.match_job(1, resume_text=irrelevant_resume)

        # Relevant resume should score higher
        assert result_with_resume["score"] > result_irrelevant["score"]

    def test_skills_still_from_kb(self, db, kb):
        """Skills overlap should still use KB skills, even when resume_text is provided."""
        jr = JobRepository(db)
        svc = JobMatcherService(kb, jr)

        # Resume text doesn't mention skills explicitly, but KB has Python + AWS
        result = svc.match_job(1, resume_text="Some resume content")
        features = result["breakdown"]
        # Skills overlap should still be > 0 because KB has Python + AWS
        assert features["skills_overlap"] > 0

    def test_batch_match_with_resume(self, db, kb):
        """Batch matching should accept resume_text too."""
        jr = JobRepository(db)
        svc = JobMatcherService(kb, jr)
        results = svc.match_batch([1], resume_text="Python AWS microservices Docker")
        assert len(results) == 1
        assert results[0]["score"] > 0
