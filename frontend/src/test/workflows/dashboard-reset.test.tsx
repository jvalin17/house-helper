/**
 * Workflow 5: Dashboard reset — UI side.
 *
 * The reset button lives on DashboardTab and gates on confirm() before calling
 * api.resetDashboard. Tests verify confirm/cancel branches.
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import DashboardTab from "@/components/tabs/DashboardTab"
import { api } from "@/api/client"

vi.mock("@/api/client")

describe("Workflow: Dashboard reset", () => {
  let confirmSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getStats).mockResolvedValue({ jobs: 4, applications: 2, skills: 8 })
    vi.mocked(api.getBudget).mockResolvedValue({ remaining_cost: 0.42 })
    vi.mocked(api.listSavedResumes).mockResolvedValue([])
    vi.mocked(api.listApplications).mockResolvedValue([])
  })

  afterEach(() => {
    confirmSpy?.mockRestore()
  })

  it("invokes resetDashboard when the user confirms the prompt", async () => {
    confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true)
    vi.mocked(api.resetDashboard).mockResolvedValue({
      jobs_deleted: 4, applications_deleted: 2, resumes_deleted: 1,
    })

    render(<DashboardTab />)
    await waitFor(() => expect(screen.getByText(/Application Tracker/)).toBeInTheDocument())

    await userEvent.click(screen.getByText(/Reset Dashboard/))

    await waitFor(() => expect(api.resetDashboard).toHaveBeenCalled())
    expect(confirmSpy).toHaveBeenCalled()
  })

  it("does NOT call resetDashboard if the user cancels the confirm prompt", async () => {
    confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false)
    vi.mocked(api.resetDashboard).mockResolvedValue({
      jobs_deleted: 0, applications_deleted: 0, resumes_deleted: 0,
    })

    render(<DashboardTab />)
    await waitFor(() => expect(screen.getByText(/Reset Dashboard/)).toBeInTheDocument())

    await userEvent.click(screen.getByText(/Reset Dashboard/))

    expect(api.resetDashboard).not.toHaveBeenCalled()
  })

  it("refreshes application tracker after reset — re-fetches data", async () => {
    confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true)
    vi.mocked(api.listApplications).mockResolvedValue([])
    vi.mocked(api.resetDashboard).mockResolvedValue({
      jobs_deleted: 1, applications_deleted: 1, resumes_deleted: 0,
    })

    render(<DashboardTab />)
    await waitFor(() => expect(screen.getByText(/Application Tracker/)).toBeInTheDocument())

    // Record how many times listApplications was called before reset
    const callCountBefore = vi.mocked(api.listApplications).mock.calls.length

    await userEvent.click(screen.getByText(/Reset Dashboard/))
    await waitFor(() => expect(api.resetDashboard).toHaveBeenCalled())

    // After reset, ApplicationTracker should remount and call listApplications again
    await waitFor(() => {
      const callCountAfter = vi.mocked(api.listApplications).mock.calls.length
      expect(callCountAfter).toBeGreaterThan(callCountBefore)
    })
    // Stats should also refresh
    await waitFor(() => {
      expect(vi.mocked(api.getStats).mock.calls.length).toBeGreaterThanOrEqual(2)
    })
  })

  it("renders stats from getStats", async () => {
    render(<DashboardTab />)
    await waitFor(() => expect(screen.getByText("4")).toBeInTheDocument())
    expect(screen.getByText("Jobs Found")).toBeInTheDocument()
    expect(screen.getByText("2")).toBeInTheDocument()
    expect(screen.getByText("Applications")).toBeInTheDocument()
  })
})
