import type {
  Application, AnalysisData, AppStats, Experience, Education,
  GeneratedCoverLetter, GeneratedResume, Job, JobSource, ModelInfo,
  Project, ResumeTemplate, SavedResume, Skill, StatusEntry,
} from "@/types"

import { getAuthToken } from "@/hooks/useAuth"

// In Tauri (tauri:// protocol) or desktop, use full URL to backend server.
// In web dev mode, Vite proxy handles /api → localhost:8040.
const IS_TAURI = typeof window !== "undefined" && "__TAURI_INTERNALS__" in window
const BASE_URL = IS_TAURI ? "http://localhost:8040/api" : "/api"

// ── Frontend-side defaults so Settings is never empty ──────
const DEFAULT_PROVIDERS = ["claude", "openai", "deepseek", "grok", "gemini", "openrouter", "ollama", "custom"]

const DEFAULT_MODELS: Record<string, ModelInfo[]> = {
  claude: [
    { id: "claude-sonnet-4-20250514", name: "Claude Sonnet 4", speed: "Fast", quality: "Great", input_per_1m: 3.0, output_per_1m: 15.0, est_per_resume: "$0.017", default: true },
    { id: "claude-haiku-4-5-20251001", name: "Claude Haiku 4.5", speed: "Fastest", quality: "Good", input_per_1m: 1.0, output_per_1m: 5.0, est_per_resume: "$0.006" },
    { id: "claude-opus-4-20250514", name: "Claude Opus 4", speed: "Slower", quality: "Best", input_per_1m: 15.0, output_per_1m: 75.0, est_per_resume: "$0.083" },
  ],
  openai: [
    { id: "gpt-4o", name: "GPT-4o", speed: "Fast", quality: "Great", input_per_1m: 2.5, output_per_1m: 10.0, est_per_resume: "$0.013", default: true },
    { id: "gpt-4o-mini", name: "GPT-4o Mini", speed: "Fastest", quality: "Good", input_per_1m: 0.15, output_per_1m: 0.60, est_per_resume: "$0.001" },
    { id: "gpt-4.1", name: "GPT-4.1", speed: "Fast", quality: "Newest", input_per_1m: 2.0, output_per_1m: 8.0, est_per_resume: "$0.010" },
  ],
  deepseek: [
    { id: "deepseek-chat", name: "DeepSeek V3", speed: "Fast", quality: "Great", input_per_1m: 0.27, output_per_1m: 1.10, est_per_resume: "$0.001", default: true },
    { id: "deepseek-reasoner", name: "DeepSeek R1", speed: "Slower", quality: "Best", input_per_1m: 0.55, output_per_1m: 2.19, est_per_resume: "$0.003" },
  ],
  grok: [
    { id: "grok-2", name: "Grok 2", speed: "Fast", quality: "Great", input_per_1m: 2.0, output_per_1m: 10.0, est_per_resume: "$0.011", default: true },
  ],
  gemini: [
    { id: "gemini-2.0-flash", name: "Gemini 2.0 Flash", speed: "Fastest", quality: "Good", input_per_1m: 0.10, output_per_1m: 0.40, est_per_resume: "$0.001", default: true },
    { id: "gemini-2.5-pro", name: "Gemini 2.5 Pro", speed: "Fast", quality: "Great", input_per_1m: 1.25, output_per_1m: 10.0, est_per_resume: "$0.010" },
  ],
  openrouter: [
    { id: "anthropic/claude-sonnet-4", name: "Claude Sonnet 4 (via OR)", speed: "Fast", quality: "Great", input_per_1m: 3.0, output_per_1m: 15.0, est_per_resume: "$0.017", default: true },
    { id: "openai/gpt-4o", name: "GPT-4o (via OR)", speed: "Fast", quality: "Great", input_per_1m: 2.5, output_per_1m: 10.0, est_per_resume: "$0.013" },
    { id: "google/gemini-2.0-flash-001", name: "Gemini Flash (via OR)", speed: "Fastest", quality: "Good", input_per_1m: 0.10, output_per_1m: 0.40, est_per_resume: "$0.001" },
    { id: "deepseek/deepseek-chat-v3-0324", name: "DeepSeek V3 (via OR)", speed: "Fast", quality: "Great", input_per_1m: 0.27, output_per_1m: 1.10, est_per_resume: "$0.001" },
  ],
  ollama: [
    { id: "llama3.1", name: "Llama 3.1 (local)", speed: "Varies", quality: "Good", input_per_1m: 0, output_per_1m: 0, est_per_resume: "Free", default: true },
    { id: "mistral", name: "Mistral (local)", speed: "Fast", quality: "Good", input_per_1m: 0, output_per_1m: 0, est_per_resume: "Free" },
  ],
  custom: [
    { id: "default", name: "Custom model", speed: "Varies", quality: "Varies", input_per_1m: 0, output_per_1m: 0, est_per_resume: "Varies", default: true },
  ],
}

const DEFAULT_SOURCES: JobSource[] = [
  { id: "jsearch", name: "JSearch (LinkedIn, Indeed, Glassdoor via RapidAPI)", signup: "https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch", free_tier: "500 requests/month", is_available: false, requires_api_key: true, enabled: true },
  { id: "adzuna", name: "Adzuna", signup: "https://developer.adzuna.com", free_tier: "250 requests/day", is_available: false, requires_api_key: true, enabled: true },
  { id: "remoteok", name: "RemoteOK (remote jobs only)", signup: null, free_tier: "Unlimited (no key needed)", is_available: true, requires_api_key: false, enabled: true },
]

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { ...options?.headers as Record<string, string> }
  if (options?.body) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json"
  }
  // Attach JWT token if available (multi-user mode)
  const token = getAuthToken()
  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }
  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    const detail = error?.detail

    // Budget exceeded — throw special error the UI can detect
    if (response.status === 429 && detail?.error === "budget_exceeded") {
      const err = new Error(`Daily budget limit reached: $${detail.spent?.toFixed(4)} of $${detail.limit?.toFixed(2)}`)
      ;(err as BudgetError).budgetExceeded = true
      ;(err as BudgetError).spent = detail.spent
      ;(err as BudgetError).limit = detail.limit
      throw err
    }

    const message = error?.error?.message
      || (typeof detail === "string" ? detail : detail?.error?.message || detail?.message)
      || `Request failed: ${response.status}`
    throw new Error(message)
  }
  return response.json()
}

export interface BudgetError extends Error {
  budgetExceeded: true
  spent: number
  limit: number
}

export function isBudgetError(err: unknown): err is BudgetError {
  return err instanceof Error && (err as BudgetError).budgetExceeded === true
}

async function fetchChecked(url: string): Promise<Response> {
  const response = await fetch(url)
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    const detail = error?.detail
    const message = error?.error?.message
      || (typeof detail === "string" ? detail : detail?.error?.message || detail?.message)
      || `Request failed: ${response.status}`
    throw new Error(message)
  }
  return response
}

/** Safe fetch — returns fallback on failure instead of throwing. */
async function safeFetch<T>(url: string, fallback: T): Promise<T> {
  try {
    const fullUrl = IS_TAURI && url.startsWith("/api")
      ? `http://localhost:8040${url}`
      : url
    const response = await fetch(fullUrl)
    return response.ok ? await response.json() : fallback
  } catch {
    return fallback
  }
}

export const api = {
  // ── Knowledge Bank ────────────────────────────
  extractSkills: (text: string) =>
    request<{ extracted_skills: string[]; raw_text: string; source: string; method: string }>(
      "/knowledge/extract", { method: "POST", body: JSON.stringify({ text }) },
    ),
  extractBullets: (url: string) =>
    request<{
      experiences: Array<{ company: string; title: string; bullets: string[] }>
      projects: Array<{ name: string; description: string; tech_stack: string }>
      source_url: string
      raw_text_length: number
    }>("/knowledge/extract-bullets", { method: "POST", body: JSON.stringify({ text: url }) }),
  listEntries: () =>
    request<{ experiences: Experience[]; skills: Skill[]; education: Education[]; projects: Project[] }>(
      "/knowledge/entries",
    ),
  createEntry: (entry: Record<string, unknown>) =>
    request("/knowledge/entries", { method: "POST", body: JSON.stringify(entry) }),
  updateEntry: (id: number, entry: Record<string, unknown>) =>
    request(`/knowledge/entries/${id}`, { method: "PUT", body: JSON.stringify(entry) }),
  deleteEntry: (id: number) =>
    request(`/knowledge/entries/${id}`, { method: "DELETE" }),
  deleteEducation: (id: number) =>
    request(`/knowledge/education/${id}`, { method: "DELETE" }),
  updateEducation: (id: number, data: Record<string, string>) =>
    request(`/knowledge/education/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteProject: (id: number) =>
    request(`/knowledge/projects/${id}`, { method: "DELETE" }),
  listSkills: () => request<Skill[]>("/knowledge/skills"),
  createSkill: (skill: { name: string; category: string; proficiency?: string }) =>
    request("/knowledge/skills", { method: "POST", body: JSON.stringify(skill) }),
  deleteSkill: (skillId: number) =>
    request(`/knowledge/skills/${skillId}`, { method: "DELETE" }),
  updateSkill: (skillId: number, data: Record<string, string>) =>
    request(`/knowledge/skills/${skillId}`, { method: "PUT", body: JSON.stringify(data) }),
  updateProject: (id: number, data: Record<string, string>) =>
    request(`/knowledge/projects/${id}`, { method: "PUT", body: JSON.stringify(data) }),
  deleteSkillsByCategory: (category: string) =>
    request<{ category: string; deleted_count: number }>(`/knowledge/skills/category/${category}`, { method: "DELETE" }),
  getStoredResume: () =>
    request<{ has_resume: boolean; text?: string; has_docx?: boolean; structure?: Record<string, unknown> }>(
      "/knowledge/resume",
    ),
  importResume: async (file: File) => {
    const formData = new FormData()
    formData.append("file", file)
    const response = await fetch(`${BASE_URL}/knowledge/import`, { method: "POST", body: formData })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error?.detail?.error?.message || error?.detail || `Upload failed: ${response.status}`)
    }
    return response.json() as Promise<Record<string, number>>
  },

  // ── Resume Templates ──────────────────────────
  listTemplates: () => request<ResumeTemplate[]>("/resume-templates"),
  uploadTemplate: async (file: File) => {
    const formData = new FormData()
    formData.append("file", file)
    const response = await fetch(`${BASE_URL}/resume-templates`, { method: "POST", body: formData })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      const detail = error?.detail
      throw new Error(typeof detail === "string" ? detail : detail?.error?.message || `Upload failed: ${response.status}`)
    }
    return response.json()
  },
  deleteTemplate: (id: number) => request(`/resume-templates/${id}`, { method: "DELETE" }),
  setDefaultTemplate: (id: number) => request(`/resume-templates/${id}/default`, { method: "PUT" }),
  previewTemplate: (id: number) => fetchChecked(`${BASE_URL}/resume-templates/${id}/preview`),

  // ── Suggestion Feedback ───────────────────────
  rejectSuggestion: (data: { suggestion_text: string; reason?: string; original_bullet?: string }) =>
    request("/feedback/suggestions", { method: "POST", body: JSON.stringify(data) }),

  // ── Jobs ──────────────────────────────────────
  parseJobs: (inputs: string[]) =>
    request<{ jobs: Job[] }>("/jobs/parse", { method: "POST", body: JSON.stringify({ inputs }) }),
  listJobs: () => request<Job[]>("/jobs"),
  getJob: (id: number) => request<Job>(`/jobs/${id}`),
  deleteJob: (id: number) => request(`/jobs/${id}`, { method: "DELETE" }),

  // ── Matching ──────────────────────────────────
  matchJob: (jobId: number, resumeId?: number) =>
    request(`/jobs/${jobId}/match`, {
      method: "POST", body: JSON.stringify(resumeId ? { resume_id: resumeId } : {}),
    }),
  matchBatch: (jobIds: number[], resumeId?: number) =>
    request("/jobs/match-batch", {
      method: "POST", body: JSON.stringify({ job_ids: jobIds, ...(resumeId ? { resume_id: resumeId } : {}) }),
    }),

  // ── Resumes ───────────────────────────────────
  analyzeResumeFit: (jobId: number) =>
    request<AnalysisData>("/resumes/analyze", {
      method: "POST", body: JSON.stringify({ job_id: jobId }),
    }),
  generateResume: (jobId: number, preferences: Record<string, unknown> = {}) =>
    request<GeneratedResume>("/resumes/generate", {
      method: "POST", body: JSON.stringify({ job_id: jobId, preferences }),
    }),
  listSavedResumes: () => request<SavedResume[]>("/resumes/saved"),
  saveResumeExplicit: (id: number, name?: string) =>
    request<{ saved: number; name: string }>(`/resumes/${id}/save`, {
      method: "POST", body: JSON.stringify(name ? { name } : {}),
    }),
  unsaveResume: (id: number) =>
    request(`/resumes/${id}/unsave`, { method: "POST" }),
  getSavedCount: () => request<{ count: number; max: number }>("/resumes/saved/count"),
  deleteResume: (id: number) => request(`/resumes/${id}`, { method: "DELETE" }),
  exportResume: (id: number, format: string) =>
    fetchChecked(`${BASE_URL}/resumes/${id}/export?format=${format}`),
  resumeFeedback: (id: number, rating: number) =>
    request(`/resumes/${id}/feedback`, { method: "POST", body: JSON.stringify({ rating }) }),

  // ── Cover Letters ─────────────────────────────
  generateCoverLetter: (jobId: number, preferences: Record<string, unknown> = {}) =>
    request<GeneratedCoverLetter>("/cover-letters/generate", {
      method: "POST", body: JSON.stringify({ job_id: jobId, preferences }),
    }),
  exportCoverLetter: (id: number, format: string) =>
    fetchChecked(`${BASE_URL}/cover-letters/${id}/export?format=${format}`),

  // ── Applications ──────────────────────────────
  createApplication: (jobId: number, resumeId?: number, coverLetterId?: number) =>
    request("/applications", {
      method: "POST", body: JSON.stringify({ job_id: jobId, resume_id: resumeId, cover_letter_id: coverLetterId }),
    }),
  listApplications: () => request<Application[]>("/applications"),
  updateApplicationStatus: (id: number, status: string) =>
    request(`/applications/${id}`, { method: "PUT", body: JSON.stringify({ status }) }),
  getApplicationHistory: (id: number) => request<StatusEntry[]>(`/applications/${id}/history`),

  // ── Settings (previously direct fetches) ──────
  getLLMConfig: () => safeFetch<Record<string, string>>("/api/settings/llm", {}),
  getLLMProviders: async () => {
    const result = await safeFetch<{ providers: string[] }>("/api/settings/llm/providers", { providers: [] })
    return result.providers?.length ? result : { providers: DEFAULT_PROVIDERS }
  },
  getLLMModels: async () => {
    const result = await safeFetch<Record<string, ModelInfo[]>>("/api/settings/llm/models", {})
    return Object.keys(result).length ? result : DEFAULT_MODELS
  },
  getLLMStatus: () => safeFetch<{ active: boolean; provider: string | null; model: string | null }>(
    "/api/settings/llm/status", { active: false, provider: null, model: null },
  ),
  saveLLM: (config: Record<string, string>) =>
    request("/settings/llm", { method: "PUT", body: JSON.stringify(config) }),
  getBudget: () => safeFetch<Record<string, unknown>>("/api/budget", {}),
  saveBudget: (data: Record<string, unknown>) =>
    request("/budget", { method: "PUT", body: JSON.stringify(data) }),
  getCalibrationWeights: () => safeFetch<Record<string, number>>("/api/calibration/weights", {}),
  recalibrate: () => request<Record<string, number>>("/calibration/recalculate", { method: "POST" }),
  getSearchSources: async () => {
    const result = await safeFetch<JobSource[]>("/api/search/sources", [])
    return result.length ? result : DEFAULT_SOURCES
  },
  addCustomSource: (data: { name: string; api_url: string; api_key?: string }) =>
    request("/search/sources/custom", { method: "POST", body: JSON.stringify(data) }),
  deleteCustomSource: (sourceId: string) =>
    request(`/search/sources/custom/${sourceId}`, { method: "DELETE" }),
  updateCustomSource: (sourceId: string, data: Record<string, string>) =>
    request(`/search/sources/custom/${sourceId}`, { method: "PUT", body: JSON.stringify(data) }),
  toggleSource: (sourceId: string, enabled: boolean) =>
    request(`/search/sources/${sourceId}/toggle`, {
      method: "PUT", body: JSON.stringify({ enabled }),
    }),

  // ── Profile / Search Defaults ──────────────────
  getActiveProfile: () => request<Record<string, unknown>>("/profiles/active"),
  updateProfile: (id: number, data: Record<string, unknown>) =>
    request(`/profiles/${id}`, { method: "PUT", body: JSON.stringify(data) }),

  // ── Dashboard ─────────────────────────────────
  resetDashboard: () =>
    request<{ jobs_deleted: number; applications_deleted: number; resumes_deleted: number }>(
      "/dashboard/reset", { method: "POST" },
    ),
  resetKnowledgeBank: () =>
    request<{ experiences_deleted: number; skills_deleted: number; education_deleted: number; projects_deleted: number }>(
      "/knowledge/reset", { method: "POST" },
    ),

  // ── Search ────────────────────────────────────
  searchJobs: (filters: Record<string, unknown>) =>
    request<{ jobs: Job[] }>("/search/run", { method: "POST", body: JSON.stringify(filters) }),

  // ── Stats (for Home/Dashboard) ────────────────
  getStats: async (): Promise<AppStats> => {
    const [jobs, apps, skills] = await Promise.all([
      safeFetch<unknown[]>("/api/jobs", []),
      safeFetch<unknown[]>("/api/applications", []),
      safeFetch<unknown[]>("/api/knowledge/skills", []),
    ])
    return {
      jobs: Array.isArray(jobs) ? jobs.length : 0,
      applications: Array.isArray(apps) ? apps.length : 0,
      skills: Array.isArray(skills) ? skills.length : 0,
    }
  },

  // ── Calibration ───────────────────────────────
  submitRating: (jobId: number, rating: string) =>
    request("/calibration/judge", { method: "POST", body: JSON.stringify({ job_id: jobId, rating }) }),

  // ── NestScout (Apartment Agent) ─────────────
  listApartments: (savedOnly: boolean = false) =>
    request<Array<{
      id: number; title: string; address: string | null; price: number | null;
      bedrooms: number | null; bathrooms: number | null; sqft: number | null;
      amenities: string[]; source_url: string | null; is_saved: number;
    }>>(`/apartments/listings${savedOnly ? "?saved_only=true" : ""}`),
  getApartment: (listingId: number) =>
    request<Record<string, unknown>>(`/apartments/listings/${listingId}`),
  searchApartments: (filters: Record<string, unknown>) =>
    request<{
      results: Array<Record<string, unknown>>;
      count?: number;
      message?: string;
      sources?: string[];
      sources_failed?: string[];
    }>("/apartments/search", { method: "POST", body: JSON.stringify(filters) }),
  createApartmentFromUrl: (url: string) =>
    request<Record<string, unknown>>("/apartments/listings/from-url", {
      method: "POST", body: JSON.stringify({ url }),
    }),
  createApartment: (data: Record<string, unknown>) =>
    request<Record<string, unknown>>("/apartments/listings", {
      method: "POST", body: JSON.stringify(data),
    }),
  saveApartmentToShortlist: (listingId: number) =>
    request(`/apartments/listings/${listingId}/save`, { method: "POST" }),
  unsaveApartment: (listingId: number) =>
    request(`/apartments/listings/${listingId}/unsave`, { method: "POST" }),
  deleteApartment: (listingId: number) =>
    request(`/apartments/listings/${listingId}`, { method: "DELETE" }),
  getApartmentHealth: () =>
    safeFetch<{ agent: string; status: string }>("/api/apartments/health", { agent: "nestscout", status: "unknown" }),

  // NestScout Settings
  getApartmentPreferences: () =>
    safeFetch<Record<string, unknown>>("/api/apartments/preferences", {}),
  saveApartmentPreferences: (data: Record<string, unknown>) =>
    request("/apartments/preferences", { method: "PUT", body: JSON.stringify(data) }),
  listApartmentSources: () =>
    safeFetch<Array<{
      id: string; name: string; is_custom: boolean; enabled: boolean;
      signup?: string; free_tier?: string; requires_api_key?: boolean;
      api_url?: string; has_api_key?: boolean;
    }>>("/api/apartments/sources", []),
  addApartmentSource: (data: { name: string; api_url: string; api_key?: string }) =>
    request("/apartments/sources/custom", { method: "POST", body: JSON.stringify(data) }),
  deleteApartmentSource: (sourceId: string) =>
    request(`/apartments/sources/custom/${sourceId}`, { method: "DELETE" }),
  toggleApartmentSource: (sourceId: string, enabled: boolean) =>
    request(`/apartments/sources/custom/${sourceId}/toggle`, { method: "PUT", body: JSON.stringify({ enabled }) }),
  saveApartmentSourceApiKey: (sourceId: string, apiKey: string) =>
    request(`/apartments/sources/${sourceId}/api-key`, { method: "PUT", body: JSON.stringify({ api_key: apiKey }) }),

  // NestScout Lab
  getLabData: (listingId: number, runAnalysis: boolean = false) =>
    request<{
      listing: Record<string, unknown>;
      analyses: Record<string, unknown>;
      feature_preferences: Array<{ feature_name: string; category: string; preference: string }>;
      must_haves: string[];
      deal_breakers: string[];
      comparable_count: number;
      pipeline_steps: string[];
    }>(`/apartments/lab/${listingId}${runAnalysis ? "?run_analysis=true" : ""}`),
  getAnalyzedListingIds: () =>
    safeFetch<number[]>("/api/apartments/lab/analyzed-ids", []),
  getLabStreamUrl: (listingId: number) =>
    `${window.location.protocol}//${window.location.host}/api/apartments/lab/${listingId}/stream`,
  getLabNeighborhood: (listingId: number, refresh: boolean = false) =>
    request<Record<string, unknown>>(`/apartments/lab/${listingId}/neighborhood${refresh ? "?refresh=true" : ""}`),
  getFeaturePreferences: () =>
    safeFetch<Array<{ feature_name: string; category: string; preference: string }>>(
      "/api/apartments/preferences/features", [],
    ),
  setFeaturePreference: (featureName: string, category: string, preference: string) =>
    request(`/apartments/preferences/features/${encodeURIComponent(featureName)}`, {
      method: "PUT", body: JSON.stringify({ category, preference }),
    }),
  resetFeaturePreference: (featureName: string) =>
    request(`/apartments/preferences/features/${encodeURIComponent(featureName)}`, { method: "DELETE" }),

  // Global Credentials
  getAllCredentials: () =>
    safeFetch<Array<{
      service_name: string; category: string; display_name: string;
      signup_url: string | null; description: string | null;
      is_configured: number; is_enabled: number;
    }>>("/api/settings/credentials", []),
  saveCredential: (serviceName: string, apiKey: string) =>
    request<{ service: string; is_configured: boolean }>(`/settings/credentials/${serviceName}`, {
      method: "PUT", body: JSON.stringify({ api_key: apiKey }),
    }),
  deleteCredential: (serviceName: string) =>
    request(`/settings/credentials/${serviceName}`, { method: "DELETE" }),
  getCredentialsStatus: () =>
    safeFetch<Record<string, boolean>>("/api/settings/credentials/status", {}),

  // NestScout Cost + Price
  getListingCost: (listingId: number) =>
    request<Record<string, unknown>>(`/apartments/cost/${listingId}`),
  saveListingCost: (listingId: number, data: Record<string, unknown>) =>
    request<Record<string, unknown>>(`/apartments/cost/${listingId}`, {
      method: "PUT", body: JSON.stringify(data),
    }),
  askAboutListing: (listingId: number, question: string) =>
    request<{ question: string; answer: string }>(`/apartments/lab/${listingId}/ask`, {
      method: "POST", body: JSON.stringify({ question }),
    }),
  getQaHistory: (listingId: number) =>
    safeFetch<Array<{ id: number; question: string; answer: string; created_at: string }>>(
      `/api/apartments/lab/${listingId}/qa-history`, [],
    ),
  compareListings: (listingIds: number[]) =>
    request<{
      listings: Array<{
        listing: Record<string, unknown>; score: number;
        matched_must_haves: string[]; matched_deal_breakers: string[];
        analysis_summary: string | null; price_verdict: string | null;
      }>;
      must_haves: string[]; deal_breakers: string[];
    }>("/apartments/compare", { method: "POST", body: JSON.stringify({ listing_ids: listingIds }) }),
  getPriceContext: (listingId: number) =>
    request<{
      listing_price: number; area_median: number | null;
      percentile: number | null; comparable_count: number;
      price_vs_median: number | null;
      comparables: Array<{ id: number; title: string; price: number; bedrooms: number | null }>;
    }>(`/apartments/price-context/${listingId}`),
}
