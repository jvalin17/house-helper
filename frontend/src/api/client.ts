const BASE_URL = "/api"

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { ...options?.headers as Record<string, string> }
  // Only set Content-Type for requests with a body
  if (options?.body) {
    headers["Content-Type"] = headers["Content-Type"] || "application/json"
  }
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  })
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

async function fetchChecked(url: string, options?: RequestInit): Promise<Response> {
  const response = await fetch(url, options)
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

export const api = {
  // Knowledge Bank
  extractSkills: (text: string) =>
    request("/knowledge/extract", { method: "POST", body: JSON.stringify({ text }) }),
  listEntries: () => request("/knowledge/entries"),
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
  getStoredResume: () => request<Record<string, unknown>>("/knowledge/resume"),

  // Resume Templates
  listTemplates: () => request<Array<Record<string, unknown>>>("/resume-templates"),
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

  // Suggestion Feedback
  rejectSuggestion: (data: { suggestion_text: string; reason?: string; original_bullet?: string }) =>
    request("/feedback/suggestions", { method: "POST", body: JSON.stringify(data) }),
  listRejections: () => request<Array<Record<string, unknown>>>("/feedback/suggestions"),
  deleteRejection: (id: number) => request(`/feedback/suggestions/${id}`, { method: "DELETE" }),
  listSkills: () => request("/knowledge/skills"),
  createSkill: (skill: Record<string, unknown>) =>
    request("/knowledge/skills", { method: "POST", body: JSON.stringify(skill) }),
  importResume: async (file: File) => {
    const formData = new FormData()
    formData.append("file", file)
    const response = await fetch(`${BASE_URL}/knowledge/import`, {
      method: "POST",
      body: formData,
    })
    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error?.detail?.error?.message || error?.detail || `Upload failed: ${response.status}`)
    }
    return response.json()
  },

  // Jobs
  parseJobs: (inputs: string[]) =>
    request<{ jobs: Array<Record<string, unknown>> }>("/jobs/parse", {
      method: "POST", body: JSON.stringify({ inputs }),
    }),
  listJobs: () => request<Array<Record<string, unknown>>>("/jobs"),
  getJob: (id: number) => request(`/jobs/${id}`),
  deleteJob: (id: number) => request(`/jobs/${id}`, { method: "DELETE" }),

  // Matching
  matchJob: (jobId: number) =>
    request(`/jobs/${jobId}/match`, { method: "POST" }),
  matchBatch: (jobIds: number[]) =>
    request("/jobs/match-batch", { method: "POST", body: JSON.stringify({ job_ids: jobIds }) }),

  // Resumes
  analyzeResumeFit: (jobId: number) =>
    request<Record<string, unknown>>("/resumes/analyze", {
      method: "POST", body: JSON.stringify({ job_id: jobId }),
    }),
  generateResume: (jobId: number, preferences: Record<string, unknown> = {}) =>
    request<{ id: number; content: string; analysis?: Record<string, unknown> }>("/resumes/generate", {
      method: "POST", body: JSON.stringify({ job_id: jobId, preferences }),
    }),
  listResumes: () => request<Array<Record<string, unknown>>>("/resumes"),
  getResume: (id: number) => request(`/resumes/${id}`),
  exportResume: (id: number, format: string) =>
    fetchChecked(`${BASE_URL}/resumes/${id}/export?format=${format}`),
  resumeFeedback: (id: number, rating: number) =>
    request(`/resumes/${id}/feedback`, {
      method: "POST", body: JSON.stringify({ rating }),
    }),

  // Cover Letters
  generateCoverLetter: (jobId: number, preferences: Record<string, unknown> = {}) =>
    request<{ id: number; content: string }>("/cover-letters/generate", {
      method: "POST", body: JSON.stringify({ job_id: jobId, preferences }),
    }),
  listCoverLetters: () => request<Array<Record<string, unknown>>>("/cover-letters"),
  getCoverLetter: (id: number) => request(`/cover-letters/${id}`),
  updateCoverLetter: (id: number, content: string) =>
    request(`/cover-letters/${id}`, {
      method: "PUT", body: JSON.stringify({ content }),
    }),
  exportCoverLetter: (id: number, format: string) =>
    fetchChecked(`${BASE_URL}/cover-letters/${id}/export?format=${format}`),

  // Applications
  createApplication: (jobId: number, resumeId?: number, coverLetterId?: number) =>
    request("/applications", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId, resume_id: resumeId, cover_letter_id: coverLetterId }),
    }),
  listApplications: (status?: string) =>
    request<Array<Record<string, unknown>>>(`/applications${status ? `?status=${status}` : ""}`),
  updateApplicationStatus: (id: number, status: string) =>
    request(`/applications/${id}`, {
      method: "PUT", body: JSON.stringify({ status }),
    }),
  getApplicationHistory: (id: number) => request(`/applications/${id}/history`),

  // Preferences
  getPreferences: () => request("/preferences"),
  updatePreferences: (prefs: Record<string, unknown>) =>
    request("/preferences", { method: "PUT", body: JSON.stringify(prefs) }),
}
