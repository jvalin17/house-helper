/**
 * Workflow 9: Save search defaults — pre-fill from active profile, persist on save.
 * Workflow 10: Job filters — exclusion checkboxes are wired and saved into resume_preferences.
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { BrowserRouter } from "react-router-dom"
import JobSearchTab from "@/components/tabs/JobSearchTab"
import { api } from "@/api/client"

vi.mock("@/api/client")

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.listSavedResumes).mockResolvedValue([])
})

describe("Workflow: Save search defaults + filters", () => {
  it("pre-fills filter inputs from the active profile", async () => {
    vi.mocked(api.getActiveProfile).mockResolvedValue({
      id: 1, search_title: "SRE", search_location: "Seattle, WA",
      search_keywords: "Kubernetes", search_remote: 1,
      resume_preferences: JSON.stringify({ exclude_internship: true }),
    })

    render(<BrowserRouter><JobSearchTab onApplied={vi.fn()} /></BrowserRouter>)

    await waitFor(() => expect(api.getActiveProfile).toHaveBeenCalled())
    await waitFor(() => expect(screen.getByDisplayValue("SRE")).toBeInTheDocument())
    expect(screen.getByDisplayValue("Seattle, WA")).toBeInTheDocument()
    expect(screen.getByDisplayValue("Kubernetes")).toBeInTheDocument()

    const internCheckbox = screen.getByLabelText(/Skip internships/) as HTMLInputElement
    expect(internCheckbox.checked).toBe(true)
  })

  it("persists filters and resume_preferences on Save as Defaults", async () => {
    vi.mocked(api.getActiveProfile).mockResolvedValue({ id: 42 })
    vi.mocked(api.updateProfile).mockResolvedValue({})

    render(<BrowserRouter><JobSearchTab onApplied={vi.fn()} /></BrowserRouter>)
    await waitFor(() => expect(api.getActiveProfile).toHaveBeenCalled())

    await userEvent.type(screen.getByPlaceholderText(/Job Title/i), "Backend")
    await userEvent.click(screen.getByLabelText(/Need sponsorship/))
    await userEvent.click(screen.getByLabelText(/I lack clearance/))

    await userEvent.click(screen.getByRole("button", { name: /Save as Defaults/ }))

    await waitFor(() => expect(api.updateProfile).toHaveBeenCalled())
    const [profileId, payload] = vi.mocked(api.updateProfile).mock.calls[0]
    expect(profileId).toBe(42)
    expect(payload.search_title).toBe("Backend")
    const prefs = JSON.parse(String(payload.resume_preferences))
    expect(prefs.exclude_sponsorship).toBe(true)
    expect(prefs.exclude_clearance).toBe(true)
    expect(prefs.exclude_internship).toBe(false)
  })

  it("Save as Defaults is a no-op without an active profile", async () => {
    vi.mocked(api.getActiveProfile).mockResolvedValue(null as unknown as Record<string, unknown>)

    render(<BrowserRouter><JobSearchTab onApplied={vi.fn()} /></BrowserRouter>)
    await userEvent.click(screen.getByRole("button", { name: /Save as Defaults/ }))
    expect(api.updateProfile).not.toHaveBeenCalled()
  })
})
