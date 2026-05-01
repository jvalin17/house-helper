/**
 * Workflow 18: Application tracker — status change + timeline.
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import ApplicationTracker from "@/components/ApplicationTracker"
import { api } from "@/api/client"
import type { Application, Job, StatusEntry } from "@/types"

vi.mock("@/api/client")

const job = (id: number, title: string): Job => ({
  id, title, company: "Acme", match_score: 0.7,
  parsed_data: "{}", match_breakdown: null,
})

const application = (over: Partial<Application> = {}): Application => ({
  id: 1, job_id: 100, resume_id: 11, cover_letter_id: 22,
  status: "applied", notes: null, created_at: "", ...over,
})

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.getJob).mockImplementation(async (id: number) => job(id, "Backend Engineer"))
})

describe("Workflow: Application tracker", () => {
  it("renders applications grouped by status with totals", async () => {
    vi.mocked(api.listApplications).mockResolvedValue([
      application({ id: 1, status: "applied" }),
      application({ id: 2, status: "interview" }),
      application({ id: 3, status: "offer" }),
    ])

    render(<ApplicationTracker />)
    await waitFor(() => expect(api.listApplications).toHaveBeenCalled())

    await screen.findByText(/Total/)
    expect(screen.getAllByText("Backend Engineer").length).toBe(3)
    const statBoxes = screen.getAllByText(/Total|Interviews|Offers/)
    expect(statBoxes.length).toBeGreaterThanOrEqual(3)
  })

  it("expanding an app loads its history and renders the timeline", async () => {
    vi.mocked(api.listApplications).mockResolvedValue([application({ id: 9 })])
    const history: StatusEntry[] = [
      { status: "applied", changed_at: "2026-01-01" },
      { status: "interview", changed_at: "2026-01-05" },
    ]
    vi.mocked(api.getApplicationHistory).mockResolvedValue(history)

    render(<ApplicationTracker />)
    const appCard = await screen.findByText("Backend Engineer")
    await userEvent.click(appCard)

    await waitFor(() => expect(api.getApplicationHistory).toHaveBeenCalledWith(9))
    await screen.findByText(/Timeline/)
    expect(screen.getAllByText("interview").length).toBeGreaterThanOrEqual(1)
    expect(screen.getAllByText("applied").length).toBeGreaterThanOrEqual(1)
  })

  it("clicking a status transition button calls updateApplicationStatus", async () => {
    vi.mocked(api.listApplications).mockResolvedValue([application({ id: 5, status: "applied" })])
    vi.mocked(api.getApplicationHistory).mockResolvedValue([])
    vi.mocked(api.updateApplicationStatus).mockResolvedValue({})

    render(<ApplicationTracker />)
    const appCard = await screen.findByText("Backend Engineer")
    await userEvent.click(appCard)

    const transition = await screen.findByRole("button", { name: /→ interview/ })
    await userEvent.click(transition)

    await waitFor(() => expect(api.updateApplicationStatus).toHaveBeenCalledWith(5, "interview"))
  })

  it("does NOT show rocket emoji on manually tracked applications", async () => {
    vi.mocked(api.listApplications).mockResolvedValue([
      application({ id: 10, resume_id: 11, cover_letter_id: 22, status: "applied" }),
    ])

    render(<ApplicationTracker />)
    await screen.findByText("Backend Engineer")

    const rocketElement = document.querySelector('[title="Auto-launched"]')
    expect(rocketElement).toBeNull()
  })

  it("renders the empty state when there are no applications", async () => {
    vi.mocked(api.listApplications).mockResolvedValue([])

    render(<ApplicationTracker />)
    await screen.findByText(/No applications yet/)
  })
})
