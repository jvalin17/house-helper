/**
 * Workflow 15: Apply & Track — clicking Apply & Track creates an application
 * tied to the generated resume + cover letter and shows the success state.
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
    experiences: [{ id: 1, title: "Eng", company: "Acme",
      start_date: "2020", end_date: "", description: "Built things" }],
    skills: [], education: [], projects: [],
  })
  vi.mocked(api.getJob).mockResolvedValue({
    id: 100, title: "Backend Engineer", company: "Acme",
    match_score: 0.6, parsed_data: "{}", match_breakdown: null,
  })
  vi.mocked(api.analyzeResumeFit).mockResolvedValue({
    current_resume_match: 60, knowledge_bank_match: 80, match_gap: "moderate",
    strengths: [], gaps: [], summary: "ok", suggested_improvements: [],
  })
  vi.mocked(api.generateResume).mockResolvedValue({ id: 11, content: "resume", job_id: 100 })
  vi.mocked(api.generateCoverLetter).mockResolvedValue({ id: 22, content: "cover", job_id: 100 })
})

describe("Workflow: Apply & Track", () => {
  it("creates an application with both document ids on click", async () => {
    vi.mocked(api.createApplication).mockResolvedValue({ id: 1, job_id: 100, status: "applied" })

    render(<PreviewModal jobId={100} jobTitle="Backend" company="Acme" onClose={vi.fn()} />)
    await screen.findByRole("button", { name: /Generate without changes/ })
    await userEvent.click(screen.getByRole("button", { name: /Generate without changes/ }))
    await screen.findByRole("button", { name: /Apply & Track/ })

    await userEvent.click(screen.getByRole("button", { name: /Apply & Track/ }))

    await waitFor(() => expect(api.createApplication).toHaveBeenCalledWith(100, 11, 22))
    await screen.findByRole("dialog", { name: /Application tracked/ })
  })

  it("surfaces an error message when tracking fails", async () => {
    vi.mocked(api.createApplication).mockRejectedValue(new Error("DB_FAIL"))

    render(<PreviewModal jobId={100} jobTitle="Backend" company="Acme" onClose={vi.fn()} />)
    await screen.findByRole("button", { name: /Generate without changes/ })
    await userEvent.click(screen.getByRole("button", { name: /Generate without changes/ }))
    await screen.findByRole("button", { name: /Apply & Track/ })

    await userEvent.click(screen.getByRole("button", { name: /Apply & Track/ }))

    await screen.findByText(/DB_FAIL/)
  })
})
