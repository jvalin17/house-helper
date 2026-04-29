/**
 * Workflow 8: Upload resume template — store, set default, delete.
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import KnowledgeBank from "@/components/KnowledgeBank"
import { api } from "@/api/client"
import type { ResumeTemplate } from "@/types"

vi.mock("@/api/client")

const tmpl = (over: Partial<ResumeTemplate> = {}): ResumeTemplate => ({
  id: 1, name: "Default", filename: "resume.docx", is_default: 1,
  format: "docx", created_at: "2026-01-01", ...over,
})

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.listEntries).mockResolvedValue({
    experiences: [], skills: [], education: [], projects: [],
  })
  vi.mocked(api.listSkills).mockResolvedValue([])
  vi.mocked(api.getStoredResume).mockResolvedValue({ has_resume: false })
})

describe("Workflow: Upload resume template", () => {
  it("uploads a docx and refreshes the list", async () => {
    vi.mocked(api.listTemplates)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([tmpl({ id: 5, name: "MyResume", filename: "myresume.docx" })])
    vi.mocked(api.uploadTemplate).mockResolvedValue({ id: 5, name: "MyResume" })

    render(<KnowledgeBank />)
    await screen.findByText(/Resume Templates \(0\/5\)/)

    const file = new File(["fake"], "myresume.docx", {
      type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    })
    const input = document.getElementById("template-upload") as HTMLInputElement
    await userEvent.upload(input, file)

    await waitFor(() => expect(api.uploadTemplate).toHaveBeenCalledWith(file))
    await screen.findByText(/MyResume/)
  })

  it("calls setDefaultTemplate when a non-default template is promoted", async () => {
    vi.mocked(api.listTemplates).mockResolvedValue([
      tmpl({ id: 1, name: "Old", is_default: 1 }),
      tmpl({ id: 2, name: "New", is_default: 0 }),
    ])
    vi.mocked(api.setDefaultTemplate).mockResolvedValue({ default: 2 })

    render(<KnowledgeBank />)
    const setDefault = await screen.findByRole("button", { name: /Set Default/ })
    await userEvent.click(setDefault)

    await waitFor(() => expect(api.setDefaultTemplate).toHaveBeenCalledWith(2))
  })

  it("disables Add Template once 5 templates exist", async () => {
    vi.mocked(api.listTemplates).mockResolvedValue(
      Array.from({ length: 5 }, (_, i) => tmpl({ id: i + 1, name: `T${i+1}` })),
    )

    render(<KnowledgeBank />)
    await screen.findByText(/Resume Templates \(5\/5\)/)
    const button = screen.getByRole("button", { name: /\+ Add Template/ })
    expect(button).toBeDisabled()
  })
})
