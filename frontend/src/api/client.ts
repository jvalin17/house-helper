import type {
  Application, AnalysisData, AppStats, Experience, Education,
  GeneratedCoverLetter, GeneratedResume, Job, JobSource, ModelInfo,
  Project, ResumeTemplate, SavedResume, Skill, StatusEntry,
} from "@/types"

const BASE_URL = "/api"

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { ...options?.headers as Record<string, string> }
  if (options?.body) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json"
  }
  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    const detail = error?.detail
    const message = error?.error?.message
      || (typeof detail === "string" ? detail : detail?.error?.message || detail?.message)
      || `Request failed: ${response.status}`
    throw new Error(message)
  }
  return response.json()
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
    const r = await fetch(url)
    return r.ok ? await r.json() : fallback
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
  deleteProject: (id: number) =>
    request(`/knowledge/projects/${id}`, { method: "DELETE" }),
  listSkills: () => request<Skill[]>("/knowledge/skills"),
  createSkill: (skill: { name: string; category: string; proficiency?: string }) =>
    request("/knowledge/skills", { method: "POST", body: JSON.stringify(skill) }),
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
  matchJob: (jobId: number) =>
    request(`/jobs/${jobId}/match`, { method: "POST" }),
  matchBatch: (jobIds: number[]) =>
    request("/jobs/match-batch", { method: "POST", body: JSON.stringify({ job_ids: jobIds }) }),

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
  getLLMProviders: () => safeFetch<{ providers: string[] }>("/api/settings/llm/providers", { providers: [] }),
  getLLMModels: () => safeFetch<Record<string, ModelInfo[]>>("/api/settings/llm/models", {}),
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
  getSearchSources: () => safeFetch<JobSource[]>("/api/search/sources", []),

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
}
