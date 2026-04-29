"""Dashboard reset — clears jobs, applications, ephemeral resumes.

Preserves: knowledge bank, settings, templates, saved resumes, feedback.
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
