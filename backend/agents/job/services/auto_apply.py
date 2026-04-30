"""Auto apply service — manages the apply queue and execution.

Supports two flows:
1. Manual: user selects jobs → queue → generate → confirm → apply
2. Auto: agent searches → picks top N by match → generates docs → user confirms
"""

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
        self._cover_letter_service = cover_letter_svc

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
            preferences = preferences or {}
            resume = self._resume_svc.generate(job_id=entry["job_id"], preferences=preferences)
            cover_letter = self._cover_letter_service.generate(job_id=entry["job_id"], preferences=preferences)

            self._queue.set_resume(entry_id, resume["id"], cover_letter["id"])
            self._queue.update_status(entry_id, "ready")

            return {
                "entry_id": entry_id,
                "status": "ready",
                "resume": resume,
                "cover_letter": cover_letter,
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

    def auto_run(self, search_svc, filters: dict, max_jobs: int = 5) -> dict:
        """Full auto pipeline: search → match → pick top N → generate docs → queue for review.

        Returns the queue with generated docs ready for user confirmation.
        """
        # Step 1: Search
        search_results = search_svc.search(filters)

        if not search_results:
            return {"jobs_found": 0, "queue": [], "message": "No jobs found matching your criteria"}

        # Step 2: Pick top N by match score
        top_jobs = search_results[:max_jobs]
        job_ids = [j["id"] for j in top_jobs]

        # Step 3: Queue them
        entries = self.queue_batch(job_ids)

        # Step 4: Generate docs for each
        generated = []
        for entry in entries:
            try:
                result = self.generate_docs(entry["id"])
                generated.append(result)
            except Exception as e:
                generated.append({"entry_id": entry["id"], "status": "failed", "error": str(e)})

        return {
            "jobs_found": len(search_results),
            "queued": len(entries),
            "queue": self.get_queue(),
            "message": f"Found {len(search_results)} jobs, queued top {len(entries)} with docs generated. Ready for your review.",
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
