"""TDD tests for dashboard reset.

Clears: jobs, applications, status_history, auto_apply_queue, ephemeral resumes
Preserves: experiences, skills, education, projects, resume_templates,
           settings, saved resumes (is_saved=1), suggestion_feedback
"""

from pathlib import Path

import pytest

from shared.db import connect_sync


@pytest.fixture
def db():
    conn = connect_sync(db_path=Path(":memory:"))
    # Populate all tables
    conn.execute("INSERT INTO jobs (id, title, company, parsed_data) VALUES (1, 'SWE', 'Google', '{}')")
    conn.execute("INSERT INTO applications (id, job_id, status) VALUES (1, 1, 'applied')")
    conn.execute("INSERT INTO application_status_history (application_id, status) VALUES (1, 'applied')")
    conn.execute("INSERT INTO resumes (id, job_id, content, preferences, is_saved) VALUES (1, 1, 'ephemeral', '{}', 0)")
    conn.execute("INSERT INTO resumes (id, job_id, content, preferences, is_saved, save_name) VALUES (2, 1, 'saved', '{}', 1, 'resume_26_v1')")
    conn.execute("INSERT INTO experiences (type, title, company) VALUES ('job', 'SWE', 'Google')")
    conn.execute("INSERT INTO skills (name, category) VALUES ('Python', 'languages')")
    conn.execute("INSERT INTO education (institution) VALUES ('MIT')")
    conn.execute("INSERT INTO projects (name) VALUES ('TestProj')")
    conn.execute("INSERT INTO suggestion_feedback (suggestion_text) VALUES ('test')")
    conn.commit()
    return conn


class TestDashboardReset:
    def test_clears_jobs(self, db):
        from agents.job.services.reset import reset_dashboard
        reset_dashboard(db)
        assert db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0

    def test_clears_applications(self, db):
        from agents.job.services.reset import reset_dashboard
        reset_dashboard(db)
        assert db.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 0

    def test_clears_status_history(self, db):
        from agents.job.services.reset import reset_dashboard
        reset_dashboard(db)
        assert db.execute("SELECT COUNT(*) FROM application_status_history").fetchone()[0] == 0

    def test_clears_ephemeral_resumes(self, db):
        from agents.job.services.reset import reset_dashboard
        reset_dashboard(db)
        ephemeral = db.execute("SELECT COUNT(*) FROM resumes WHERE is_saved = 0").fetchone()[0]
        assert ephemeral == 0

    def test_preserves_saved_resumes(self, db):
        from agents.job.services.reset import reset_dashboard
        reset_dashboard(db)
        saved = db.execute("SELECT COUNT(*) FROM resumes WHERE is_saved = 1").fetchone()[0]
        assert saved == 1

    def test_preserves_experiences(self, db):
        from agents.job.services.reset import reset_dashboard
        reset_dashboard(db)
        assert db.execute("SELECT COUNT(*) FROM experiences").fetchone()[0] == 1

    def test_preserves_skills(self, db):
        from agents.job.services.reset import reset_dashboard
        reset_dashboard(db)
        assert db.execute("SELECT COUNT(*) FROM skills").fetchone()[0] == 1

    def test_preserves_education(self, db):
        from agents.job.services.reset import reset_dashboard
        reset_dashboard(db)
        assert db.execute("SELECT COUNT(*) FROM education").fetchone()[0] == 1

    def test_preserves_projects(self, db):
        from agents.job.services.reset import reset_dashboard
        reset_dashboard(db)
        assert db.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 1

    def test_preserves_suggestion_feedback(self, db):
        from agents.job.services.reset import reset_dashboard
        reset_dashboard(db)
        assert db.execute("SELECT COUNT(*) FROM suggestion_feedback").fetchone()[0] == 1

    def test_returns_counts(self, db):
        from agents.job.services.reset import reset_dashboard
        result = reset_dashboard(db)
        assert result["jobs_deleted"] == 1
        assert result["applications_deleted"] == 1
        assert result["resumes_deleted"] == 1  # only ephemeral
