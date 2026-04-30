"""Reset services — clear data by scope.

reset_dashboard: clears jobs, applications, ephemeral resumes.
reset_knowledge_bank: clears experiences, skills, education, projects.
reset_all: clears everything except settings.
"""

import sqlite3


def reset_dashboard(conn: sqlite3.Connection) -> dict:
    """Clear all job search data while preserving knowledge bank and settings."""
    # Count before deleting
    jobs_count = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    apps_count = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    resumes_count = conn.execute("SELECT COUNT(*) FROM resumes WHERE is_saved = 0").fetchone()[0]

    # Delete in FK-safe order (children before parents)
    conn.execute("DELETE FROM application_status_history")
    conn.execute("DELETE FROM applications")
    conn.execute("DELETE FROM auto_apply_queue")
    conn.execute("DELETE FROM resumes WHERE is_saved = 0")
    conn.execute("DELETE FROM cover_letters")
    conn.execute("DELETE FROM calibration_judgements")
    conn.execute("DELETE FROM evidence_log")
    # Detach saved resumes from jobs before deleting jobs
    conn.execute("UPDATE resumes SET job_id = NULL WHERE is_saved = 1")
    conn.execute("DELETE FROM jobs")
    conn.commit()

    return {
        "jobs_deleted": jobs_count,
        "applications_deleted": apps_count,
        "resumes_deleted": resumes_count,
    }


def reset_knowledge_bank(conn: sqlite3.Connection) -> dict:
    """Clear all knowledge bank data: experiences, skills, education, projects.

    Preserves: jobs, applications, settings, templates, saved resumes.
    """
    experiences_count = conn.execute("SELECT COUNT(*) FROM experiences").fetchone()[0]
    skills_count = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
    education_count = conn.execute("SELECT COUNT(*) FROM education").fetchone()[0]
    projects_count = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]

    # Delete in FK-safe order (achievements reference experiences)
    conn.execute("DELETE FROM achievements")
    conn.execute("DELETE FROM skills")
    conn.execute("DELETE FROM experiences")
    conn.execute("DELETE FROM education")
    conn.execute("DELETE FROM projects")
    conn.commit()

    return {
        "experiences_deleted": experiences_count,
        "skills_deleted": skills_count,
        "education_deleted": education_count,
        "projects_deleted": projects_count,
    }
