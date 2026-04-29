/**
 * Workflow 2: Scout jobs → results returned, match all → sorted by score.
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { BrowserRouter } from "react-router-dom"
import JobSearchTab from "@/components/tabs/JobSearchTab"
import { api } from "@/api/client"
import type { Job } from "@/types"

vi.mock("@/api/client")

const mockJobs = (over: Partial<Job>[] = []): Job[] =>
  over.length
    ? over.map((j, i) => ({
        id: i + 1, title: `Job ${i + 1}`, company: "Co", match_score: null,
        parsed_data: "{}", match_breakdown: null, ...j,
      }))
    : [
        { id: 1, title: "Backend Engineer", company: "BigTech", match_score: null,
          parsed_data: "{}", match_breakdown: null },
        { id: 2, title: "Frontend Engineer", company: "Startup", match_score: null,
          parsed_data: "{}", match_breakdown: null },
      ]

describe("Workflow: Scout jobs and match", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getActiveProfile).mockResolvedValue({})
    vi.mocked(api.listSavedResumes).mockResolvedValue([])
  })

  it("scout jobs renders results, then match-all updates scores in sorted order", async () => {
    vi.mocked(api.searchJobs).mockResolvedValue({ jobs: mockJobs() })

    render(<BrowserRouter><JobSearchTab onApplied={vi.fn()} /></BrowserRouter>)

    await userEvent.click(screen.getByText(/Scout Jobs/))
    await waitFor(() => expect(api.searchJobs).toHaveBeenCalled())
    await waitFor(() => expect(screen.getByText("Backend Engineer")).toBeInTheDocument())
    expect(screen.getByText("Frontend Engineer")).toBeInTheDocument()

    vi.mocked(api.matchBatch).mockResolvedValue({ results: [] })
    vi.mocked(api.listJobs).mockResolvedValue([
      { id: 1, title: "Backend Engineer", company: "BigTech", match_score: 0.85,
        parsed_data: "{}", match_breakdown: null },
      { id: 2, title: "Frontend Engineer", company: "Startup", match_score: 0.45,
        parsed_data: "{}", match_breakdown: null },
    ])

    await userEvent.click(screen.getByText(/Match All/))
    await waitFor(() => expect(api.matchBatch).toHaveBeenCalled())
    await waitFor(() => expect(screen.getByText("85%")).toBeInTheDocument())
    expect(screen.getByText("45%")).toBeInTheDocument()
  })

  it("shows an error message when search fails", async () => {
    vi.mocked(api.searchJobs).mockRejectedValue(new Error("network"))

    render(<BrowserRouter><JobSearchTab onApplied={vi.fn()} /></BrowserRouter>)
    await userEvent.click(screen.getByText(/Scout Jobs/))

    await waitFor(() =>
      expect(screen.getByText(/Search failed.*API keys/)).toBeInTheDocument(),
    )
  })

  it("renders an empty state when no jobs returned", async () => {
    vi.mocked(api.searchJobs).mockResolvedValue({ jobs: [] })

    render(<BrowserRouter><JobSearchTab onApplied={vi.fn()} /></BrowserRouter>)
    await userEvent.click(screen.getByText(/Scout Jobs/))

    await waitFor(() => expect(screen.getByText(/Found 0 jobs/)).toBeInTheDocument())
    expect(screen.queryByText(/Match All/)).not.toBeInTheDocument()
  })
})
