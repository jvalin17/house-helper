/**
 * Shared TypeScript types for the Panini frontend.
 *
 * All domain models and API response types live here.
 * Components import from @/types instead of defining their own.
 */

// ── Knowledge Bank ─────────────────────────────

export interface Experience {
  id: number
  type?: string
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
  ranking_score?: number | null
  ranking_breakdown?: Record<string, unknown>
  is_existing?: boolean
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
  is_custom?: boolean
  api_url?: string
  has_api_key?: boolean
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

export interface HomeStats {
  applications: number
  homes_explored: number
  hours_saved: number
}

export interface AppStats {
  jobs: number
  applications: number
  skills: number
  budget_remaining?: string
}

// ── NestScout Dashboard ────────────────────────

export interface DashboardFunnelStage {
  count: number
  listings: DashboardListing[]
}

export interface DashboardListing {
  id: number
  title: string
  address: string
  source_url: string
  image_url: string | null
  effective_monthly: number | null
  match_score: number | null
  stage: string
  photo_count: number
  has_intel: boolean
}

export interface DashboardStats {
  total_saved: number
  interested_count: number
  visited_count: number
  applied_count: number
  approved_count: number
  moved_in_count: number
  archived_count: number
  hunt_started_at: string | null
  average_rent: number | null
}

export interface Achievement {
  id: string
  title: string
  description: string
  unlocked: boolean
}

export interface DashboardNotes {
  listing_id: number
  notes: string
  structured_data: Record<string, unknown> | null
  status: string
  created_at: string
}

export interface SearchProfilePreference {
  term: string
  weight: number
  achievable: boolean
  average_rent: number
}

export interface SearchProfile {
  ready: boolean
  interaction_count?: number
  preferences?: SearchProfilePreference[]
  budget?: number
  wishlist_average?: number
  summary?: string
}

export interface CompromiseResult {
  matching_count: number
  average_rent: number
  per_preference_impact: Array<{
    term: string
    enabled: boolean
    listings_added: number
    rent_saved: number
  }>
  suggestions: Array<{
    listing_id: number
    title: string
    price: number | null
    match_score: number | null
    matching_preferences: string[]
    missing_preferences: string[]
  }>
  positive_message: string
}

export interface VisitPhoto {
  id: number
  listing_id: number
  file_path: string
  label: string | null
  room_tag: string | null
  display_order: number
  ai_analysis: Record<string, unknown> | null
  created_at: string
}
