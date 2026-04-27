"""FastAPI routes for the job agent — all REST endpoints."""

from __future__ import annotations

import json
import sqlite3
from typing import TYPE_CHECKING

from fastapi import APIRouter, HTTPException, Query, UploadFile, File

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
from agents.job.services.knowledge import KnowledgeService
from agents.job.services.tracker import TrackerService
from agents.job.services.auto_search import AutoSearchService
from agents.job.services.auto_apply import AutoApplyService
from agents.job.repositories.search_repo import SearchRepository
from agents.job.repositories.apply_queue_repo import ApplyQueueRepository
from agents.job.repositories.token_repo import TokenRepository
from agents.job.repositories.evidence_repo import EvidenceRepository
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
    knowledge_svc = KnowledgeService(knowledge_repo=knowledge_repo)
    tracker_svc = TrackerService(application_repo=app_repo)
    search_repo = SearchRepository(conn)
    queue_repo = ApplyQueueRepository(conn)
    token_repo = TokenRepository(conn)
    evidence_repo = EvidenceRepository(conn)
    search_svc = AutoSearchService(
        job_repo=job_repo, knowledge_repo=knowledge_repo, matcher=matcher_svc
    )
    apply_svc = AutoApplyService(
        queue_repo=queue_repo, job_repo=job_repo, app_repo=app_repo,
        resume_svc=resume_svc, cover_letter_svc=cl_svc,
    )

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

    @router.post("/knowledge/import")
    def import_resume(file: UploadFile = File(...)):
        import tempfile
        from pathlib import Path

        suffix = Path(file.filename or "resume.docx").suffix.lower()
        if suffix not in (".docx", ".pdf", ".txt"):
            raise HTTPException(
                400,
                detail=_error("VALIDATION_ERROR", f"Unsupported format: {suffix}. Use .docx, .pdf, or .txt"),
            )

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            content = file.file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            result = knowledge_svc.import_resume(tmp_path)
        except ValueError as e:
            raise HTTPException(400, detail=_error("PARSE_FAILED", str(e)))
        finally:
            tmp_path.unlink(missing_ok=True)

        return result

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
    def match_single_job(job_id: int, data: dict = {}):
        """Match a single job. Pass {"use_llm": true} for deep AI analysis."""
        try:
            use_llm = data.get("use_llm", False)
            return matcher_svc.match_job(job_id, use_llm=use_llm)
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
        # Compute weights on-the-fly from judgements (no separate weights table)
        rows = conn.execute("SELECT match_features, user_rating FROM calibration_judgements").fetchall()
        if not rows:
            return DEFAULT_WEIGHTS
        judgements = [
            {"match_features": json.loads(r["match_features"]), "user_rating": r["user_rating"]}
            for r in rows
        ]
        return recalculate_weights(judgements)

    @router.post("/calibration/recalculate")
    def recalculate_calibration():
        rows = conn.execute("SELECT match_features, user_rating FROM calibration_judgements").fetchall()
        judgements = [
            {"match_features": json.loads(r["match_features"]), "user_rating": r["user_rating"]}
            for r in rows
        ]
        return recalculate_weights(judgements)

    # ==================== Preferences ====================

    @router.get("/preferences")
    def get_preferences():
        row = conn.execute("SELECT value FROM settings WHERE key = 'preferences'").fetchone()
        if row:
            return json.loads(row["value"])
        return {}

    @router.put("/preferences")
    def update_preferences(prefs: dict):
        conn.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('preferences', ?, datetime('now'))",
            (json.dumps(prefs),),
        )
        conn.commit()
        return prefs

    # ==================== Auto Search ====================

    @router.post("/search/run")
    def run_search(filters: dict):
        results = search_svc.search(filters)
        return {"jobs": results, "count": len(results)}

    @router.get("/search/sources")
    def list_job_sources():
        from shared.job_boards.factory import get_board_info
        return get_board_info()

    @router.get("/search/filters")
    def list_search_filters():
        return search_repo.list_filters()

    @router.post("/search/filters")
    def save_search_filter(data: dict):
        name = data.get("name", "Untitled Search")
        filters = {k: v for k, v in data.items() if k != "name"}
        filter_id = search_repo.save_filter(name, filters)
        return {"id": filter_id, "name": name}

    @router.delete("/search/filters/{filter_id}")
    def delete_search_filter(filter_id: int):
        search_repo.delete_filter(filter_id)
        return {"deleted": filter_id}

    @router.get("/search/schedule")
    def get_search_schedule():
        return search_repo.get_schedule() or {}

    @router.put("/search/schedule")
    def set_search_schedule(data: dict):
        schedule_id = search_repo.save_schedule(
            filter_id=data["filter_id"],
            frequency_hours=data.get("frequency_hours", 6),
        )
        return {"id": schedule_id}

    # ==================== Auto Apply ====================

    @router.post("/apply/auto")
    def auto_apply_pipeline(data: dict):
        """Full auto pipeline: search → match → generate docs → queue for review."""
        filters = data.get("filters", {})
        max_jobs = min(data.get("max_jobs", 5), 5)
        result = apply_svc.auto_run(search_svc, filters, max_jobs)
        return result

    @router.post("/apply/batch")
    def queue_batch_apply(data: dict):
        job_ids = data.get("job_ids", [])
        if len(job_ids) > 5:
            raise HTTPException(400, detail=_error("VALIDATION_ERROR", "Max 5 jobs per batch"))
        entries = apply_svc.queue_batch(job_ids)
        return {"queue": entries}

    @router.get("/apply/queue")
    def get_apply_queue():
        return apply_svc.get_queue()

    @router.post("/apply/generate/{entry_id}")
    def generate_apply_docs(entry_id: int):
        try:
            return apply_svc.generate_docs(entry_id)
        except ValueError as e:
            raise HTTPException(404, detail=_error("NOT_FOUND", str(e)))

    @router.post("/apply/confirm/{entry_id}")
    def confirm_apply(entry_id: int):
        return apply_svc.confirm(entry_id)

    @router.post("/apply/skip/{entry_id}")
    def skip_apply(entry_id: int):
        return apply_svc.skip(entry_id)

    @router.post("/apply/execute/{entry_id}")
    def execute_apply(entry_id: int):
        try:
            return apply_svc.execute_apply(entry_id)
        except ValueError as e:
            raise HTTPException(400, detail=_error("APPLY_FAILED", str(e)))

    # ==================== Token Budget ====================

    @router.get("/budget")
    def get_budget():
        return token_repo.get_remaining_today()

    @router.put("/budget")
    def set_budget(data: dict):
        token_repo.set_budget(
            daily_limit_cost=data.get("daily_limit_cost"),
            daily_limit_tokens=data.get("daily_limit_tokens"),
            ask_threshold=data.get("ask_threshold", "over_budget"),
        )
        return token_repo.get_budget()

    @router.get("/budget/usage")
    def get_usage():
        return token_repo.get_today_usage()

    # ==================== Evidence ====================

    @router.get("/evidence/{entity_type}/{entity_id}")
    def get_evidence(entity_type: str, entity_id: int):
        return evidence_repo.get_evidence(entity_type, entity_id)

    # ==================== ATS Optimization ====================

    @router.post("/ats/validate/{resume_id}")
    def validate_resume_ats(resume_id: int, data: dict = {}):
        from shared.ats_optimizer import validate_resume
        resume = resume_repo.get_resume(resume_id)
        if not resume:
            raise HTTPException(404, detail=_error("NOT_FOUND", f"Resume {resume_id} not found"))
        seniority = data.get("seniority", "mid")
        return validate_resume(resume["content"], seniority)

    @router.get("/ats/rules")
    def get_ats_rules():
        from shared.ats_optimizer import load_rules, get_formatting_tips
        rules = load_rules()
        return {
            "version": rules.get("_version"),
            "updated": rules.get("_updated"),
            "formatting": get_formatting_tips(),
            "section_order": rules.get("section_order"),
            "length_guidelines": rules.get("length_guidelines"),
        }

    # ==================== Local ML ====================

    @router.get("/ml/status")
    def get_local_model_status():
        """Check if local ML model has enough data to reduce LLM costs."""
        from shared.algorithms.local_matcher import get_local_model_stats
        return get_local_model_stats(conn)

    # ==================== Profiles ====================

    from agents.job.repositories.profile_repo import ProfileRepository
    profile_repo = ProfileRepository(conn)

    @router.get("/profiles")
    def list_profiles():
        return profile_repo.list_profiles()

    @router.get("/profiles/active")
    def get_active_profile():
        return profile_repo.get_active_profile() or {}

    @router.post("/profiles")
    def create_profile(data: dict):
        profile_id = profile_repo.create_profile(
            name=data.get("name", "Untitled"),
            type=data.get("type", "focus"),
            description=data.get("description"),
            search_title=data.get("search_title"),
            search_keywords=data.get("search_keywords"),
            search_location=data.get("search_location"),
            search_remote=data.get("search_remote", False),
        )
        return profile_repo.get_profile(profile_id)

    @router.put("/profiles/{profile_id}/activate")
    def activate_profile(profile_id: int):
        profile_repo.set_active(profile_id)
        return profile_repo.get_profile(profile_id)

    @router.delete("/profiles/{profile_id}")
    def delete_profile(profile_id: int):
        profile_repo.delete_profile(profile_id)
        return {"deleted": profile_id}

    return router


def _error(code: str, message: str, details: dict | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details}}
