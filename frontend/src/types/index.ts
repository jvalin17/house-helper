/**
 * Shared TypeScript types for the Panini frontend.
 *
 * All domain models and API response types live here.
 * Components import from @/types instead of defining their own.
 */

// ── Knowledge Bank ─────────────────────────────

export interface Experience {
  id: number
  title: string
  company: string
  start_date: string
  end_date: string
  description: string
}

export interface Skill {
  id: number
  name: string
  category: string
}

export interface Education {
  id: number
  institution: string
  degree: string
  field: string
  end_date: string
}

export interface Project {
  id: number
  name: string
  description: string
  tech_stack: string
  url: string
}

// ── Jobs ────────────────────────────────────────

export interface Job {
  id: number
  title: string
  company: string
  match_score: number | null
  status?: string
  created_at?: string
  source_url?: string | null
  url?: string | null
  parsed_data: string
  match_breakdown: string | null
}

// ── Applications ────────────────────────────────

export interface Application {
  id: number
  job_id: number
  status: string
  resume_id: number | null
  cover_letter_id: number | null
  notes: string | null
  created_at: string
}

export interface StatusEntry {
  status: string
  changed_at: string
}

// ── Resume Analysis & Generation ────────────────

export interface Suggestion {
  type: string
  description: string
  impact: string
  source: string
}

export interface AnalysisData {
  current_resume_match: number
  knowledge_bank_match: number
  match_gap: string
  strengths: string[]
  gaps: string[]
  suggested_improvements: Suggestion[]
  summary: string
  error?: string
}

export interface GeneratedResume {
  id: number
  content: string
  analysis?: Record<string, unknown>
}

export interface SavedResume {
  id: number
  job_id: number
  job_title: string
  job_company: string
  save_name: string
  has_docx: boolean
  is_saved: number
  feedback: number | null
  created_at: string
}

export interface GeneratedCoverLetter {
  id: number
  content: string
}

// ── Templates ───────────────────────────────────

export interface ResumeTemplate {
  id: number
  name: string
  filename: string
  format: string
  is_default: number
  has_docx_format: number
  created_at: string
}

// ── Settings ────────────────────────────────────

export interface JobSource {
  id: string
  name: string
  signup: string | null
  free_tier: string
  is_available: boolean
  requires_api_key: boolean
  enabled: boolean
}

export interface ModelInfo {
  id: string
  name: string
  speed: string
  quality: string
  input_per_1m: number
  output_per_1m: number
  est_per_resume: string
  default?: boolean
}

// ── Pipeline ────────────────────────────────────

export type StageStatus = "waiting" | "active" | "done"

export interface PipelineJob {
  id: number
  title: string
  company: string
  matchScore: number
  url?: string
}

export interface PipelineStage {
  id: string
  label: string
  detail: string
  status: StageStatus
}

// ── Stats ───────────────────────────────────────

export interface AppStats {
  jobs: number
  applications: number
  skills: number
  budget_remaining?: string
}
