/**
 * JobSearchTab — extra branches beyond scout-jobs.test.tsx.
 *
 * Covers job selection + AI evaluation, the Tailor Resume button,
 * opening JobDetail and rating a job, the Clear button, malformed
 * resume_preferences in the loaded profile, and the Save-as-Defaults
 * error path.
 */

import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { BrowserRouter } from "react-router-dom"
import { Toaster } from "sonner"
import JobSearchTab from "@/components/tabs/JobSearchTab"
import { api } from "@/api/client"
import type { Job } from "@/types"

vi.mock("@/api/client")

const baseJobs: Job[] = [
  { id: 1, title: "Backend Engineer", company: "BigTech", match_score: 0.4,
    parsed_data: JSON.stringify({ description: "Python services", required_skills: ["Python"] }),
    match_breakdown: null, url: "https://example.com/jobs/1" },
  { id: 2, title: "Frontend Engineer", company: "Startup", match_score: 0.3,
    parsed_data: "{}", match_breakdown: null },
]

function renderTab(profile: Record<string, unknown> | null = {}) {
  vi.mocked(api.getActiveProfile).mockResolvedValue(profile as never)
  vi.mocked(api.listSavedResumes).mockResolvedValue([])
  return render(
    <BrowserRouter>
      <Toaster />
      <JobSearchTab onApplied={vi.fn()} />
    </BrowserRouter>
  )
}

async function performSearch(jobs: Job[] = baseJobs) {
  vi.mocked(api.searchJobs).mockResolvedValue({ jobs })
  await userEvent.click(screen.getByText(/Scout Jobs/))
  await waitFor(() =>
    expect(screen.getByText(jobs[0]?.title || "Backend Engineer")).toBeInTheDocument()
  )
}

describe("JobSearchTab — selection + AI evaluate", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("selecting a job swaps the AI prompt for the Evaluate button", async () => {
    renderTab()
    await performSearch()

    expect(screen.getByText(/Select jobs to evaluate with AI/)).toBeInTheDocument()
    await userEvent.click(screen.getByLabelText("Select Backend Engineer"))
    expect(screen.getByText(/Evaluate 1 Selected \(AI\)/)).toBeInTheDocument()
  })

  it("AI evaluate calls /api/jobs/:id/match with use_llm and updates the score", async () => {
    renderTab()
    await performSearch()
    await userEvent.click(screen.getByLabelText("Select Backend Engineer"))

    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ score: 0.92 }),
    } as Response)

    try {
      await userEvent.click(screen.getByText(/Evaluate 1 Selected \(AI\)/))
      await waitFor(() => expect(fetchSpy).toHaveBeenCalled())
      const [url, init] = fetchSpy.mock.calls[0]
      expect(url).toBe("/api/jobs/1/match")
      expect((init as RequestInit).method).toBe("POST")
      expect((init as RequestInit).body).toContain("\"use_llm\":true")
      await waitFor(() => expect(screen.getByText("92%")).toBeInTheDocument())
      await waitFor(() => expect(screen.getByText(/jobs evaluated with AI/)).toBeInTheDocument())
    } finally {
      fetchSpy.mockRestore()
    }
  })

  it("shows an error status when AI evaluation throws", async () => {
    renderTab()
    await performSearch()
    await userEvent.click(screen.getByLabelText("Select Backend Engineer"))

    const fetchSpy = vi.spyOn(global, "fetch").mockRejectedValue(new Error("boom"))
    try {
      await userEvent.click(screen.getByText(/Evaluate 1 Selected \(AI\)/))
      await waitFor(() => expect(screen.getByText(/AI matching failed/)).toBeInTheDocument())
    } finally {
      fetchSpy.mockRestore()
    }
  })

  it("Clear button removes results and the controls disappear", async () => {
    renderTab()
    await performSearch()
    expect(screen.getByText(/2 Results/)).toBeInTheDocument()

    await userEvent.click(screen.getByRole("button", { name: "Clear" }))
    expect(screen.queryByText(/2 Results/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Match All/)).not.toBeInTheDocument()
  })
})

describe("JobSearchTab — opening detail and rating", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("clicking a row opens JobDetail and Yes triggers submitRating", async () => {
    renderTab()
    await performSearch()
    vi.mocked(api.submitRating).mockResolvedValue({ ok: true })

    await userEvent.click(screen.getByText("Backend Engineer"))
    const dialog = await screen.findByRole("dialog", { name: /Job details: Backend Engineer/ })
    await userEvent.click(within(dialog).getByRole("button", { name: "Yes" }))
    await waitFor(() => expect(api.submitRating).toHaveBeenCalledWith(1, "good"))
  })

  it("Generate from JobDetail opens the PreviewModal", async () => {
    renderTab()
    await performSearch()
    vi.mocked(api.analyzeResumeFit).mockResolvedValue({
      current_resume_match: 0, knowledge_bank_match: 0, match_gap: "",
      strengths: [], gaps: [], suggested_improvements: [], summary: "",
    })

    await userEvent.click(screen.getByText("Backend Engineer"))
    const dialog = await screen.findByRole("dialog")
    await userEvent.click(within(dialog).getByRole("button", { name: /Generate Resume & Cover Letter/ }))

    await waitFor(() =>
      expect(screen.queryByRole("dialog", { name: /Job details/ })).not.toBeInTheDocument()
    )
    expect(
      await screen.findByRole("dialog", { name: /Resume preview: Backend Engineer/ })
    ).toBeInTheDocument()
  })

  it("Tailor Resume button opens PreviewModal directly", async () => {
    renderTab()
    await performSearch()
    vi.mocked(api.analyzeResumeFit).mockResolvedValue({
      current_resume_match: 0, knowledge_bank_match: 0, match_gap: "",
      strengths: [], gaps: [], suggested_improvements: [], summary: "",
    })

    const buttons = screen.getAllByRole("button", { name: /Tailor Resume/ })
    await userEvent.click(buttons[0])
    expect(
      await screen.findByRole("dialog", { name: /Resume preview: Backend Engineer/ })
    ).toBeInTheDocument()
  })
})

describe("JobSearchTab — profile defaults", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("malformed resume_preferences JSON doesn't throw and leaves toggles off", async () => {
    renderTab({
      id: 1,
      search_title: "SRE",
      resume_preferences: "{not json",
    })
    await waitFor(() => expect(api.getActiveProfile).toHaveBeenCalled())
    expect(screen.getByPlaceholderText(/Job Title/i)).toHaveValue("SRE")
    const sponsorship = screen.getByLabelText(/Need sponsorship/) as HTMLInputElement
    expect(sponsorship.checked).toBe(false)
  })

  it("Save-as-Defaults shows the api error in a toast", async () => {
    renderTab({ id: 7 })
    await waitFor(() => expect(api.getActiveProfile).toHaveBeenCalled())

    vi.mocked(api.updateProfile).mockRejectedValue(new Error("DB locked"))
    await userEvent.click(screen.getByRole("button", { name: /Save as Defaults/ }))
    await waitFor(() => expect(screen.getByText("DB locked")).toBeInTheDocument())
  })

  it("Save-as-Defaults is a no-op without an active profile", async () => {
    renderTab(null)
    await waitFor(() => expect(api.getActiveProfile).toHaveBeenCalled())
    await userEvent.click(screen.getByRole("button", { name: /Save as Defaults/ }))
    expect(api.updateProfile).not.toHaveBeenCalled()
  })
})

describe("JobSearchTab — match-all error path", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("shows local matching failure message", async () => {
    renderTab()
    await performSearch()
    vi.mocked(api.matchBatch).mockRejectedValue(new Error("oops"))
    await userEvent.click(screen.getByText(/Match All/))
    await waitFor(() => expect(screen.getByText(/Local matching failed/)).toBeInTheDocument())
  })
})
