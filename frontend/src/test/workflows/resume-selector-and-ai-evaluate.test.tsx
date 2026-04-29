/**
 * Workflow 11: Resume selector for matching — selectedResumeId is forwarded to matchBatch.
 * Workflow 12: Evaluate selected (AI) — selected jobs trigger LLM evaluation.
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { BrowserRouter } from "react-router-dom"
import JobSearchTab from "@/components/tabs/JobSearchTab"
import { api } from "@/api/client"
import type { Job } from "@/types"

vi.mock("@/api/client")

const job = (id: number, title: string): Job => ({
  id, title, company: "Co", match_score: 0.4,
  parsed_data: "{}", match_breakdown: null,
})

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.getActiveProfile).mockResolvedValue({ id: 1 })
})

describe("Workflow: Resume selector for matching", () => {
  it("matchBatch is called with the selected saved resume id", async () => {
    vi.mocked(api.listSavedResumes).mockResolvedValue([
      { id: 7, save_name: "TailoredA", is_saved: true, content: "", job_id: 1, created_at: "" },
      { id: 8, save_name: "TailoredB", is_saved: true, content: "", job_id: 2, created_at: "" },
    ])
    vi.mocked(api.searchJobs).mockResolvedValue({ jobs: [job(101, "Backend")] })
    vi.mocked(api.matchBatch).mockResolvedValue({ results: [] })
    vi.mocked(api.listJobs).mockResolvedValue([job(101, "Backend")])

    render(<BrowserRouter><JobSearchTab onApplied={vi.fn()} /></BrowserRouter>)
    await waitFor(() => expect(api.listSavedResumes).toHaveBeenCalled())

    const select = await screen.findByLabelText(/Resume for matching/)
    await userEvent.selectOptions(select, "8")

    await userEvent.click(screen.getByRole("button", { name: /Scout Jobs/ }))
    await screen.findByText("Backend")

    await userEvent.click(screen.getByRole("button", { name: /Match All/ }))
    await waitFor(() => expect(api.matchBatch).toHaveBeenCalled())
    expect(api.matchBatch).toHaveBeenCalledWith([101], 8)
  })

  it("falls back to KB matching when no resume is selected", async () => {
    vi.mocked(api.listSavedResumes).mockResolvedValue([])
    vi.mocked(api.searchJobs).mockResolvedValue({ jobs: [job(202, "ML Eng")] })
    vi.mocked(api.matchBatch).mockResolvedValue({ results: [] })
    vi.mocked(api.listJobs).mockResolvedValue([job(202, "ML Eng")])

    render(<BrowserRouter><JobSearchTab onApplied={vi.fn()} /></BrowserRouter>)
    await userEvent.click(screen.getByRole("button", { name: /Scout Jobs/ }))
    await screen.findByText("ML Eng")
    await userEvent.click(screen.getByRole("button", { name: /Match All/ }))

    await waitFor(() => expect(api.matchBatch).toHaveBeenCalledWith([202], undefined))
  })
})

describe("Workflow: Evaluate selected (AI)", () => {
  it("clicking Evaluate Selected fires use_llm match per selected job", async () => {
    vi.mocked(api.listSavedResumes).mockResolvedValue([])
    vi.mocked(api.searchJobs).mockResolvedValue({
      jobs: [job(1, "A"), job(2, "B")],
    })

    const fetchMock = vi.fn(async (url: string, init?: RequestInit) => {
      const body = init?.body ? JSON.parse(String(init.body)) : {}
      return new Response(JSON.stringify({ score: body.use_llm ? 0.9 : 0.5 }), {
        status: 200, headers: { "Content-Type": "application/json" },
      })
    })
    vi.stubGlobal("fetch", fetchMock)

    render(<BrowserRouter><JobSearchTab onApplied={vi.fn()} /></BrowserRouter>)
    await userEvent.click(screen.getByRole("button", { name: /Scout Jobs/ }))
    await screen.findByText("A")

    await userEvent.click(screen.getByLabelText(/Select A/))
    await userEvent.click(screen.getByRole("button", { name: /Evaluate 1 Selected \(AI\)/ }))

    await waitFor(() => {
      const aiCalls = fetchMock.mock.calls.filter(([url, init]) =>
        String(url).includes("/match") && String(init?.body || "").includes("use_llm"))
      expect(aiCalls.length).toBeGreaterThanOrEqual(1)
    })

    vi.unstubAllGlobals()
  })
})
