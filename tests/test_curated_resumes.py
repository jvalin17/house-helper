"""TDD tests for curated saved resumes (max 5, user-controlled).

Resumes are generated to DB (ephemeral). User explicitly saves
the ones they want (max 5, named resume_26_v1). Unsaved resumes
are cleaned up automatically.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from shared.db import connect_sync
from agents.job.repositories.resume_repo import ResumeRepository


@pytest.fixture
def db():
    conn = connect_sync(db_path=Path(":memory:"))
    conn.execute("INSERT INTO jobs (id, title, company, parsed_data) VALUES (1, 'SWE', 'Google', '{}')")
    conn.execute("INSERT INTO jobs (id, title, company, parsed_data) VALUES (2, 'SDE', 'Amazon', '{}')")
    # Create some ephemeral resumes
    for i in range(3):
        conn.execute(
            "INSERT INTO resumes (job_id, content, preferences) VALUES (?, ?, '{}')",
            (1, f"Resume content v{i}"),
        )
    conn.commit()
    return conn


@pytest.fixture
def repo(db):
    return ResumeRepository(db)


class TestSaveResumeExplicit:
    def test_save_marks_is_saved(self, repo):
        repo.save_resume_explicit(1, "resume_26_v1")
        saved = repo.list_saved_resumes()
        assert len(saved) == 1
        assert saved[0]["save_name"] == "resume_26_v1"
        assert saved[0]["is_saved"] == 1

    def test_save_with_job_info(self, repo):
        repo.save_resume_explicit(1, "resume_26_v1")
        saved = repo.list_saved_resumes()
        assert saved[0]["job_title"] == "SWE"
        assert saved[0]["job_company"] == "Google"

    def test_unsaved_not_in_list(self, repo):
        """Ephemeral resumes (is_saved=0) should not appear in saved list."""
        saved = repo.list_saved_resumes()
        assert len(saved) == 0  # 3 resumes exist but none saved


class TestMaxFiveSaved:
    def test_max_5_enforced(self, db, repo):
        # Create 5 more resumes and save them
        for i in range(5):
            db.execute("INSERT INTO resumes (job_id, content, preferences) VALUES (1, ?, '{}')", (f"content {i}",))
        db.commit()
        for i in range(4, 9):  # IDs 4-8
            repo.save_resume_explicit(i, f"resume_26_v{i - 3}")

        assert repo.count_saved() == 5

        # 6th should raise
        db.execute("INSERT INTO resumes (job_id, content, preferences) VALUES (1, 'extra', '{}')")
        db.commit()
        with pytest.raises(ValueError, match="maximum"):
            repo.save_resume_explicit(9, "resume_26_v6")

    def test_unsave_frees_slot(self, db, repo):
        # Save 5
        for i in range(5):
            db.execute("INSERT INTO resumes (job_id, content, preferences) VALUES (1, ?, '{}')", (f"content {i}",))
        db.commit()
        for i in range(4, 9):
            repo.save_resume_explicit(i, f"resume_26_v{i - 3}")
        assert repo.count_saved() == 5

        # Unsave one
        repo.unsave_resume(4)
        assert repo.count_saved() == 4

        # Now can save again
        db.execute("INSERT INTO resumes (job_id, content, preferences) VALUES (1, 'new', '{}')")
        db.commit()
        repo.save_resume_explicit(9, "resume_26_v6")
        assert repo.count_saved() == 5


class TestAutoNameGeneration:
    def test_next_version_number(self, repo):
        year = datetime.now().year % 100
        name = repo.generate_save_name()
        assert name == f"resume_{year}_v1"

    def test_increments_version(self, repo):
        year = datetime.now().year % 100
        repo.save_resume_explicit(1, f"resume_{year}_v1")
        name = repo.generate_save_name()
        assert name == f"resume_{year}_v2"

    def test_fills_gaps(self, repo):
        """If v1 and v3 exist, next should be v4 (not v2 — simple increment)."""
        year = datetime.now().year % 100
        repo.save_resume_explicit(1, f"resume_{year}_v1")
        repo.save_resume_explicit(2, f"resume_{year}_v3")
        name = repo.generate_save_name()
        assert name == f"resume_{year}_v4"


class TestCleanupOldUnsaved:
    def test_cleanup_removes_old_unsaved(self, db, repo):
        # Insert an old unsaved resume (48 hours ago)
        old_time = (datetime.now() - timedelta(hours=48)).isoformat()
        db.execute(
            "INSERT INTO resumes (job_id, content, preferences, created_at, is_saved) VALUES (1, 'old', '{}', ?, 0)",
            (old_time,),
        )
        db.commit()

        total_before = db.execute("SELECT COUNT(*) FROM resumes").fetchone()[0]
        repo.cleanup_old_unsaved(max_age_hours=24)
        total_after = db.execute("SELECT COUNT(*) FROM resumes").fetchone()[0]

        assert total_after < total_before

    def test_cleanup_preserves_saved(self, db, repo):
        old_time = (datetime.now() - timedelta(hours=48)).isoformat()
        db.execute(
            "INSERT INTO resumes (job_id, content, preferences, created_at, is_saved) VALUES (1, 'old saved', '{}', ?, 1)",
            (old_time,),
        )
        db.commit()

        repo.cleanup_old_unsaved(max_age_hours=24)
        row = db.execute("SELECT content FROM resumes WHERE content = 'old saved'").fetchone()
        assert row is not None  # saved resume preserved

    def test_cleanup_preserves_recent_unsaved(self, db, repo):
        """Unsaved resumes less than 24h old should not be cleaned."""
        count_before = db.execute("SELECT COUNT(*) FROM resumes WHERE is_saved = 0").fetchone()[0]
        repo.cleanup_old_unsaved(max_age_hours=24)
        count_after = db.execute("SELECT COUNT(*) FROM resumes WHERE is_saved = 0").fetchone()[0]
        assert count_after == count_before  # all recent, none cleaned
