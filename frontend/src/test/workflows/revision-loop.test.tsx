/**
 * Workflow 14: Revision loop — Regenerate with user instructions changes content.
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import PreviewModal from "@/components/PreviewModal"
import { api } from "@/api/client"

vi.mock("@/api/client")

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.listEntries).mockResolvedValue({
    experiences: [{ id: 1, type: "job", title: "Eng", company: "Acme",
      start_date: "2020", end_date: "", description: "Built things" }],
    skills: [], education: [], projects: [],
  })
  vi.mocked(api.getJob).mockResolvedValue({
    id: 1, title: "Backend Engineer", company: "Acme",
    match_score: 0.6, parsed_data: "{}", match_breakdown: null,
  })
  vi.mocked(api.analyzeResumeFit).mockResolvedValue({
    current_resume_match: 60, knowledge_bank_match: 80, match_gap: "moderate",
    strengths: [], gaps: [], summary: "ok",
    suggested_improvements: [],
  })
})

describe("Workflow: Revision loop", () => {
  it("Regenerate forwards user_instructions and refreshes resume content", async () => {
    vi.mocked(api.generateResume)
      .mockResolvedValueOnce({ id: 1, content: "v1 content", job_id: 1 })
      .mockResolvedValueOnce({ id: 2, content: "v2 shorter content", job_id: 1 })
    vi.mocked(api.generateCoverLetter)
      .mockResolvedValue({ id: 1, content: "Dear..." , job_id: 1 })

    render(<PreviewModal jobId={1} jobTitle="Backend" company="Acme" onClose={vi.fn()} />)

    await screen.findByRole("button", { name: /Generate without changes/ })
    await userEvent.click(screen.getByRole("button", { name: /Generate without changes/ }))

    await screen.findByText(/v1 content/)

    const note = screen.getByPlaceholderText(/Show 6 years only/)
    await userEvent.type(note, "Make it shorter")
    await userEvent.click(screen.getByRole("button", { name: /Regenerate/ }))

    await waitFor(() => expect(api.generateResume).toHaveBeenCalledTimes(2))
    const lastCall = vi.mocked(api.generateResume).mock.calls[1]
    expect(lastCall[1]).toMatchObject({ user_instructions: "Make it shorter" })
    await screen.findByText(/v2 shorter content/)
  })

  it("Regenerate is disabled with empty note", async () => {
    vi.mocked(api.generateResume).mockResolvedValue({ id: 1, content: "v1", job_id: 1 })
    vi.mocked(api.generateCoverLetter).mockResolvedValue({ id: 1, content: "...", job_id: 1 })

    render(<PreviewModal jobId={1} jobTitle="Backend" company="Acme" onClose={vi.fn()} />)
    await screen.findByRole("button", { name: /Generate without changes/ })
    await userEvent.click(screen.getByRole("button", { name: /Generate without changes/ }))
    await screen.findByText("v1")

    const regenBtn = screen.getByRole("button", { name: /Regenerate/ })
    expect(regenBtn).toBeDisabled()
  })
})
