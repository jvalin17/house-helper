/**
 * Workflow 19: Saved resumes — preview opens PDF, DOCX export when supported.
 *
 * Complements save-resume.test.tsx (which covers create + remove + PDF export).
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import SavedResumes from "@/components/SavedResumes"
import { api } from "@/api/client"
import type { SavedResume } from "@/types"

vi.mock("@/api/client")

const make = (over: Partial<SavedResume> = {}): SavedResume => ({
  id: 1, job_id: 10, save_name: "v1",
  job_title: "Backend", job_company: "Acme",
  has_docx: true, is_saved: 1, feedback: null,
  created_at: "2026-01-01T00:00:00Z",
  ...over,
})

beforeEach(() => {
  vi.clearAllMocks()
  URL.createObjectURL = vi.fn().mockReturnValue("blob:fake")
  URL.revokeObjectURL = vi.fn()
  HTMLAnchorElement.prototype.click = vi.fn()
})

describe("Workflow: Saved resume preview/download", () => {
  it("Preview opens a PDF blob in a new window", async () => {
    vi.mocked(api.listSavedResumes).mockResolvedValue([make({ id: 7 })])
    const fakePdf = new Response(new Blob(["%PDF"]), { headers: { "Content-Type": "application/pdf" } })
    vi.mocked(api.exportResume).mockResolvedValue(fakePdf)
    const openSpy = vi.spyOn(window, "open").mockReturnValue(null)

    render(<SavedResumes />)
    await screen.findByText("v1")
    await userEvent.click(screen.getByRole("button", { name: /Preview/ }))

    await waitFor(() => expect(api.exportResume).toHaveBeenCalledWith(7, "pdf"))
    expect(openSpy).toHaveBeenCalled()
    openSpy.mockRestore()
  })

  it("DOCX button only shows when has_docx and triggers docx export", async () => {
    vi.mocked(api.listSavedResumes).mockResolvedValue([make({ id: 5, has_docx: true })])
    const fakeDocx = new Response(new Blob([""]), { headers: { "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document" } })
    vi.mocked(api.exportResume).mockResolvedValue(fakeDocx)

    render(<SavedResumes />)
    await screen.findByText("v1")
    await userEvent.click(screen.getByRole("button", { name: /^DOCX$/ }))
    await waitFor(() => expect(api.exportResume).toHaveBeenCalledWith(5, "docx"))
  })

  it("DOCX button is hidden when has_docx is false", async () => {
    vi.mocked(api.listSavedResumes).mockResolvedValue([make({ id: 5, has_docx: false })])

    render(<SavedResumes />)
    await screen.findByText("v1")
    expect(screen.queryByRole("button", { name: /^DOCX$/ })).not.toBeInTheDocument()
  })
})
