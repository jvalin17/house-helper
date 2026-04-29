/**
 * Workflow 4: Save resume → appears in saved list, max 5 enforced (UI side).
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import SavedResumes from "@/components/SavedResumes"
import { api } from "@/api/client"
import type { SavedResume } from "@/types"

vi.mock("@/api/client")

const sampleResume = (over: Partial<SavedResume> = {}): SavedResume => ({
  id: 1, job_id: 10, save_name: "resume_26_v1",
  job_title: "Backend Engineer", job_company: "BigTech",
  has_docx: true, is_saved: 1, feedback: null,
  created_at: "2026-01-01T00:00:00Z",
  ...over,
})

describe("Workflow: Saved resumes", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("loads saved resumes and renders names + counts", async () => {
    vi.mocked(api.listSavedResumes).mockResolvedValue([
      sampleResume({ id: 1, save_name: "resume_26_v1" }),
      sampleResume({ id: 2, save_name: "resume_26_v2", has_docx: false }),
    ])

    render(<SavedResumes />)

    await waitFor(() => expect(screen.getByText(/Saved Resumes \(2\/5\)/)).toBeInTheDocument())
    expect(screen.getByText("resume_26_v1")).toBeInTheDocument()
    expect(screen.getByText("resume_26_v2")).toBeInTheDocument()
  })

  it("removing a saved resume calls unsave and reloads the list", async () => {
    vi.mocked(api.listSavedResumes).mockResolvedValueOnce([sampleResume({ id: 7 })])
    vi.mocked(api.unsaveResume).mockResolvedValue({ unsaved: 7 })
    vi.mocked(api.listSavedResumes).mockResolvedValueOnce([])

    render(<SavedResumes />)
    await waitFor(() => expect(screen.getByText("resume_26_v1")).toBeInTheDocument())

    await userEvent.click(screen.getByText("Remove"))

    await waitFor(() => expect(api.unsaveResume).toHaveBeenCalledWith(7))
    await waitFor(() => expect(screen.getByText(/Saved Resumes \(0\/5\)/)).toBeInTheDocument())
  })

  it("shows the empty state when no resumes are saved", async () => {
    vi.mocked(api.listSavedResumes).mockResolvedValue([])

    render(<SavedResumes />)

    await waitFor(() => expect(screen.getByText(/No saved resumes yet/)).toBeInTheDocument())
  })

  it("triggers PDF export via the API when clicking PDF", async () => {
    vi.mocked(api.listSavedResumes).mockResolvedValue([sampleResume({ id: 9 })])
    const fakeBlob = new Blob(["%PDF-fake"], { type: "application/pdf" })
    vi.mocked(api.exportResume).mockResolvedValue(
      new Response(fakeBlob, { headers: { "Content-Type": "application/pdf" } }),
    )
    URL.createObjectURL = vi.fn().mockReturnValue("blob:fake")
    URL.revokeObjectURL = vi.fn()
    HTMLAnchorElement.prototype.click = vi.fn()

    render(<SavedResumes />)
    await waitFor(() => expect(screen.getByText("resume_26_v1")).toBeInTheDocument())

    await userEvent.click(screen.getByRole("button", { name: "PDF" }))

    await waitFor(() => expect(api.exportResume).toHaveBeenCalledWith(9, "pdf"))
  })
})
