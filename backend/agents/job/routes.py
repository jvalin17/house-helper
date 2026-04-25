"""FastAPI routes for the job agent — all REST endpoints."""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Query

from agents.job.models import (
    ApplicationCreate,
    CoverLetterUpdate,
    EntryCreate,
    EntryUpdate,
    ExtractRequest,
    FeedbackRequest,
    GenerateRequest,
    JobParseRequest,
    JudgementRequest,
    MatchRequest,
    SkillCreate,
    StatusUpdate,
)
from agents.job.repositories.application_repo import ApplicationRepository
from agents.job.repositories.cover_letter_repo import CoverLetterRepository
from agents.job.repositories.job_repo import JobRepository
from agents.job.repositories.knowledge_repo import KnowledgeRepository
from agents.job.repositories.resume_repo import ResumeRepository
from agents.job.services.cover_letter import CoverLetterService
from agents.job.services.job_matcher import JobMatcherService
from agents.job.services.job_parser import JobParserService
from agents.job.services.resume import ResumeService
from agents.job.services.tracker import TrackerService
from shared.algorithms.entity_extractor import extract_skills_from_text
from shared.calibration.scorer import compute_weighted_score, recalculate_weights, DEFAULT_WEIGHTS

if TYPE_CHECKING:
    from shared.llm.base import LLMProvider


def create_router(conn: sqlite3.Connection, llm_provider: LLMProvider | None = None) -> APIRouter:
    """Create a configured APIRouter with all job agent endpoints."""
    router = APIRouter(prefix="/api")

    # --- Repositories ---
    knowledge_repo = KnowledgeRepository(conn)
    job_repo = JobRepository(conn)
    resume_repo = ResumeRepository(conn)
    cl_repo = CoverLetterRepository(conn)
    app_repo = ApplicationRepository(conn)

    # --- Services ---
    parser_svc = JobParserService(job_repo=job_repo, llm_provider=llm_provider)
    matcher_svc = JobMatcherService(
        knowledge_repo=knowledge_repo, job_repo=job_repo, llm_provider=llm_provider
    )
    resume_svc = ResumeService(
        knowledge_repo=knowledge_repo, db_conn=conn, llm_provider=llm_provider
    )
    cl_svc = CoverLetterService(
        knowledge_repo=knowledge_repo,
        cover_letter_repo=cl_repo,
        db_conn=conn,
        llm_provider=llm_provider,
    )
    tracker_svc = TrackerService(application_repo=app_repo)

    # ==================== Knowledge Bank ====================

    @router.post("/knowledge/extract")
    def extract_knowledge(req: ExtractRequest):
        skills = extract_skills_from_text(req.text)
        return {"extracted_skills": skills, "raw_text": req.text}

    @router.get("/knowledge/entries")
    def list_entries():
        return knowledge_repo.get_full_knowledge_bank()

    @router.post("/knowledge/entries")
    def create_entry(entry: EntryCreate):
        exp_id = knowledge_repo.save_experience(
            type=entry.type,
            title=entry.title,
            company=entry.company,
            start_date=entry.start_date,
            end_date=entry.end_date,
            description=entry.description,
        )
        return {"id": exp_id, **entry.model_dump()}

    @router.put("/knowledge/entries/{entry_id}")
    def update_entry(entry_id: int, entry: EntryUpdate):
        fields = {k: v for k, v in entry.model_dump().items() if v is not None}
        if not fields:
            raise HTTPException(400, detail=_error("VALIDATION_ERROR", "No fields to update"))
        knowledge_repo.update_experience(entry_id, **fields)
        return knowledge_repo.get_experience(entry_id)

    @router.delete("/knowledge/entries/{entry_id}")
    def delete_entry(entry_id: int):
        knowledge_repo.delete_experience(entry_id)
        return {"deleted": entry_id}

    @router.get("/knowledge/skills")
    def list_skills():
        return knowledge_repo.list_skills()

    @router.post("/knowledge/skills")
    def create_skill(skill: SkillCreate):
        skill_id = knowledge_repo.save_skill(
            name=skill.name, category=skill.category, proficiency=skill.proficiency
        )
        return {"id": skill_id, **skill.model_dump()}

    # ==================== Jobs ====================

    @router.post("/jobs/parse")
    def parse_jobs(req: JobParseRequest):
        results = parser_svc.parse_batch(req.inputs)
        return {"jobs": results}

    @router.get("/jobs")
    def list_jobs():
        return job_repo.list_jobs()

    @router.get("/jobs/{job_id}")
    def get_job(job_id: int):
        job = job_repo.get_job(job_id)
        if not job:
            raise HTTPException(404, detail=_error("NOT_FOUND", f"Job {job_id} not found"))
        return job

    @router.delete("/jobs/{job_id}")
    def delete_job(job_id: int):
        job_repo.delete_job(job_id)
        return {"deleted": job_id}

    # ==================== Job Matching ====================

    @router.post("/jobs/{job_id}/match")
    def match_single_job(job_id: int):
        try:
            return matcher_svc.match_job(job_id)
        except ValueError as e:
            raise HTTPException(404, detail=_error("NOT_FOUND", str(e)))

    @router.post("/jobs/match-batch")
    def match_batch(req: MatchRequest):
        return {"results": matcher_svc.match_batch(req.job_ids)}

    # ==================== Resumes ====================

    @router.post("/resumes/generate")
    def generate_resume(req: GenerateRequest):
        return resume_svc.generate(job_id=req.job_id, preferences=req.preferences)

    @router.get("/resumes")
    def list_resumes(job_id: int | None = None):
        return resume_repo.list_resumes(job_id=job_id)

    @router.get("/resumes/{resume_id}")
    def get_resume(resume_id: int):
        resume = resume_repo.get_resume(resume_id)
        if not resume:
            raise HTTPException(404, detail=_error("NOT_FOUND", f"Resume {resume_id} not found"))
        return resume

    @router.get("/resumes/{resume_id}/export")
    def export_resume(resume_id: int, format: str = Query(default="md")):
        from fastapi.responses import Response

        try:
            data = resume_svc.export(resume_id, format=format)
        except ValueError as e:
            raise HTTPException(400, detail=_error("EXPORT_FAILED", str(e)))

        content_types = {"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "md": "text/markdown", "txt": "text/plain"}
        return Response(content=data, media_type=content_types.get(format, "application/octet-stream"))

    @router.post("/resumes/{resume_id}/feedback")
    def resume_feedback(resume_id: int, req: FeedbackRequest):
        resume_repo.save_feedback(resume_id, req.rating)
        return {"resume_id": resume_id, "feedback": req.rating}

    # ==================== Cover Letters ====================

    @router.post("/cover-letters/generate")
    def generate_cover_letter(req: GenerateRequest):
        return cl_svc.generate(job_id=req.job_id, preferences=req.preferences)

    @router.get("/cover-letters")
    def list_cover_letters(job_id: int | None = None):
        return cl_repo.list_cover_letters(job_id=job_id)

    @router.get("/cover-letters/{cl_id}")
    def get_cover_letter(cl_id: int):
        cl = cl_repo.get_cover_letter(cl_id)
        if not cl:
            raise HTTPException(404, detail=_error("NOT_FOUND", f"Cover letter {cl_id} not found"))
        return cl

    @router.put("/cover-letters/{cl_id}")
    def update_cover_letter(cl_id: int, req: CoverLetterUpdate):
        return cl_svc.update(cl_id, req.content)

    @router.get("/cover-letters/{cl_id}/export")
    def export_cover_letter(cl_id: int, format: str = Query(default="md")):
        from fastapi.responses import Response

        try:
            data = cl_svc.export(cl_id, format=format)
        except ValueError as e:
            raise HTTPException(400, detail=_error("EXPORT_FAILED", str(e)))

        content_types = {"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "md": "text/markdown", "txt": "text/plain"}
        return Response(content=data, media_type=content_types.get(format, "application/octet-stream"))

    @router.post("/cover-letters/{cl_id}/feedback")
    def cover_letter_feedback(cl_id: int, req: FeedbackRequest):
        cl_repo.save_feedback(cl_id, req.rating)
        return {"cover_letter_id": cl_id, "feedback": req.rating}

    # ==================== Applications ====================

    @router.post("/applications")
    def create_application(req: ApplicationCreate):
        return tracker_svc.create(
            job_id=req.job_id,
            resume_id=req.resume_id,
            cover_letter_id=req.cover_letter_id,
        )

    @router.get("/applications")
    def list_applications(status: str | None = None):
        return tracker_svc.list_applications(status=status)

    @router.get("/applications/{app_id}")
    def get_application(app_id: int):
        app = tracker_svc.get_application(app_id)
        if not app:
            raise HTTPException(404, detail=_error("NOT_FOUND", f"Application {app_id} not found"))
        return app

    @router.put("/applications/{app_id}")
    def update_application_status(app_id: int, req: StatusUpdate):
        return tracker_svc.update_status(app_id, req.status)

    @router.get("/applications/{app_id}/history")
    def get_application_history(app_id: int):
        return tracker_svc.get_status_history(app_id)

    # ==================== Calibration ====================

    @router.post("/calibration/judge")
    def submit_judgement(req: JudgementRequest):
        job = job_repo.get_job(req.job_id)
        if not job:
            raise HTTPException(404, detail=_error("NOT_FOUND", f"Job {req.job_id} not found"))

        match_score = job.get("match_score", 0.0) or 0.0
        match_breakdown = json.loads(job["match_breakdown"]) if job.get("match_breakdown") else {}

        conn.execute(
            """INSERT INTO calibration_judgements (job_id, match_score, match_features, user_rating, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (req.job_id, match_score, json.dumps(match_breakdown), req.rating, req.notes),
        )
        conn.commit()
        return {"job_id": req.job_id, "rating": req.rating}

    @router.get("/calibration/weights")
    def get_calibration_weights():
        row = conn.execute("SELECT weights FROM calibration_weights WHERE id = 1").fetchone()
        if row:
            return json.loads(row["weights"])
        return DEFAULT_WEIGHTS

    @router.post("/calibration/recalculate")
    def recalculate_calibration():
        rows = conn.execute("SELECT match_features, user_rating FROM calibration_judgements").fetchall()
        judgements = [
            {"match_features": json.loads(r["match_features"]), "user_rating": r["user_rating"]}
            for r in rows
        ]
        weights = recalculate_weights(judgements)
        conn.execute(
            """INSERT OR REPLACE INTO calibration_weights (id, weights, updated_at)
               VALUES (1, ?, datetime('now'))""",
            (json.dumps(weights),),
        )
        conn.commit()
        return weights

    # ==================== Preferences ====================

    @router.get("/preferences")
    def get_preferences():
        row = conn.execute("SELECT defaults FROM preferences WHERE id = 1").fetchone()
        if row:
            return json.loads(row["defaults"])
        return {}

    @router.put("/preferences")
    def update_preferences(prefs: dict):
        conn.execute(
            "INSERT OR REPLACE INTO preferences (id, defaults) VALUES (1, ?)",
            (json.dumps(prefs),),
        )
        conn.commit()
        return prefs

    return router


def _error(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}
