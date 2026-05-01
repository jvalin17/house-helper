"""Pydantic request/response models for the job agent API."""

from pydantic import BaseModel


# --- Knowledge Bank ---

class ExtractRequest(BaseModel):
    text: str

class EntryCreate(BaseModel):
    type: str
    title: str
    company: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    source_url: str | None = None

class EntryUpdate(BaseModel):
    title: str | None = None
    company: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None

class SkillCreate(BaseModel):
    name: str
    category: str
    proficiency: str | None = None

class ImportResumeRequest(BaseModel):
    file_path: str
    save: bool = True


# --- Jobs ---

class JobParseRequest(BaseModel):
    inputs: list[str]  # URLs or raw text, auto-detected

class MatchRequest(BaseModel):
    job_ids: list[int]


# --- Resume / Cover Letter ---

class GenerateRequest(BaseModel):
    job_id: int
    preferences: dict = {}

class ExportQuery(BaseModel):
    format: str = "md"

class FeedbackRequest(BaseModel):
    rating: int  # -1, 0, or 1

class CoverLetterUpdate(BaseModel):
    content: str


# --- Applications ---

class ApplicationCreate(BaseModel):
    job_id: int
    resume_id: int | None = None
    cover_letter_id: int | None = None

class StatusUpdate(BaseModel):
    status: str


# --- Calibration ---

class JudgementRequest(BaseModel):
    job_id: int
    rating: str  # 'good', 'partial', 'poor'
    notes: str | None = None


# --- Settings ---

class LLMConfigUpdate(BaseModel):
    provider: str | None = None
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None


# --- Shared Response ---

class ErrorResponse(BaseModel):
    code: str
    message: str
    details: dict | None = None
