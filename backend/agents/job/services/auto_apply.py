"""Auto apply service — manages the apply queue and execution."""

from __future__ import annotations

import webbrowser
from urllib.parse import quote

from agents.job.repositories.apply_queue_repo import ApplyQueueRepository
from agents.job.repositories.job_repo import JobRepository
from agents.job.repositories.application_repo import ApplicationRepository
from agents.job.services.resume import ResumeService
from agents.job.services.cover_letter import CoverLetterService

MAX_BATCH_SIZE = 5


class AutoApplyService:
    def __init__(
        self,
        queue_repo: ApplyQueueRepository,
        job_repo: JobRepository,
        app_repo: ApplicationRepository,
        resume_svc: ResumeService,
        cover_letter_svc: CoverLetterService,
    ):
        self._queue = queue_repo
        self._jobs = job_repo
        self._apps = app_repo
        self._resume_svc = resume_svc
        self._cl_svc = cover_letter_svc

    def queue_batch(self, job_ids: list[int]) -> list[dict]:
        """Add up to 5 jobs to the apply queue."""
        if len(job_ids) > MAX_BATCH_SIZE:
            job_ids = job_ids[:MAX_BATCH_SIZE]

        entries = []
        for job_id in job_ids:
            job = self._jobs.get_job(job_id)
            if not job:
                continue

            # Detect apply method
            url = job.get("source_url") or ""
            apply_method = "browser" if url else "manual"

            entry_id = self._queue.create_entry(job_id, apply_method)
            entries.append(self._queue.get_entry(entry_id))

        return entries

    def generate_docs(self, entry_id: int, preferences: dict | None = None) -> dict:
        """Generate resume + cover letter for a queue entry."""
        entry = self._queue.get_entry(entry_id)
        if not entry:
            raise ValueError(f"Queue entry {entry_id} not found")

        self._queue.update_status(entry_id, "generating")

        try:
            prefs = preferences or {}
            resume = self._resume_svc.generate(job_id=entry["job_id"], preferences=prefs)
            cl = self._cl_svc.generate(job_id=entry["job_id"], preferences=prefs)

            self._queue.set_resume(entry_id, resume["id"], cl["id"])
            self._queue.update_status(entry_id, "ready")

            return {
                "entry_id": entry_id,
                "status": "ready",
                "resume": resume,
                "cover_letter": cl,
            }
        except Exception as e:
            self._queue.update_status(entry_id, "failed")
            raise

    def confirm(self, entry_id: int) -> dict:
        """User confirms they want to apply."""
        self._queue.update_status(entry_id, "confirmed")
        return self._queue.get_entry(entry_id)

    def skip(self, entry_id: int) -> dict:
        """User skips this job."""
        self._queue.update_status(entry_id, "skipped")
        return self._queue.get_entry(entry_id)

    def execute_apply(self, entry_id: int) -> dict:
        """Execute the application — open email/browser."""
        entry = self._queue.get_entry(entry_id)
        if not entry or entry["status"] != "confirmed":
            raise ValueError(f"Entry {entry_id} not confirmed")

        job = self._jobs.get_job(entry["job_id"])
        method = entry.get("apply_method", "manual")
        url = job.get("source_url", "") if job else ""

        if method == "email" and job:
            # Compose mailto link
            subject = quote(f"Application: {job.get('title', '')} at {job.get('company', '')}")
            body = quote("Please find my resume and cover letter attached.\n\nBest regards")
            mailto = f"mailto:?subject={subject}&body={body}"
            webbrowser.open(mailto)
        elif method == "browser" and url:
            webbrowser.open(url)

        self._queue.update_status(entry_id, "applied")

        # Auto-create application record
        app_id = self._apps.create_application(
            job_id=entry["job_id"],
            resume_id=entry.get("resume_id"),
            cover_letter_id=entry.get("cover_letter_id"),
        )

        return {
            "entry_id": entry_id,
            "status": "applied",
            "method": method,
            "application_id": app_id,
            "company": job.get("company") if job else "Unknown",
            "title": job.get("title") if job else "Unknown",
        }

    def get_queue(self) -> list[dict]:
        """Get all queue entries with job details."""
        entries = self._queue.list_queue()
        result = []
        for entry in entries:
            job = self._jobs.get_job(entry["job_id"])
            result.append({
                **entry,
                "job_title": job.get("title") if job else "Unknown",
                "job_company": job.get("company") if job else "Unknown",
                "job_url": job.get("source_url") if job else None,
                "match_score": job.get("match_score") if job else None,
            })
        return result
