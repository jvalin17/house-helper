/**
 * Workflow 3: Tailor resume → analyze → generate.
 *
 * Drives PreviewModal end-to-end:
 *   1. Mounts → checks KB / job → calls analyzeResumeFit
 *   2. Renders ResumeAnalysis with suggestions
 *   3. Clicking the apply button triggers generateResume + generateCoverLetter
 *   4. Result step displays the returned content
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import PreviewModal from "@/components/PreviewModal"
import { api } from "@/api/client"
import type { AnalysisData } from "@/types"

vi.mock("@/api/client")

const ANALYSIS: AnalysisData = {
  current_resume_match: 62,
  knowledge_bank_match: 81,
  match_gap: "moderate",
  strengths: ["Python", "REST APIs"],
  gaps: ["Kubernetes"],
  suggested_improvements: [
    { type: "bullet_rewrite", description: "Quantify Acme API impact",
      impact: "+5%", source: "experience" },
    { type: "swap_skill", description: "Lead with FastAPI over Flask",
      impact: "+3%", source: "skills" },
  ],
  summary: "Solid match — quantify impact for stronger fit.",
}

describe("Workflow: Tailor resume", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.listEntries).mockResolvedValue({
      experiences: [{
        id: 1, title: "Senior Engineer", company: "Acme", start_date: "2020-01",
        end_date: "", description: "Built APIs",
      }],
      skills: [], education: [], projects: [],
    })
    vi.mocked(api.getJob).mockResolvedValue({
      id: 1, title: "Backend Engineer", company: "BigTech",
      match_score: 0.62, parsed_data: "{}", match_breakdown: null,
    })
    vi.mocked(api.analyzeResumeFit).mockResolvedValue(ANALYSIS)
  })

  it("analyzes fit, generates resume + cover letter, shows result content", async () => {
    vi.mocked(api.generateResume).mockResolvedValue({
      id: 42, content: "# Tailored Resume\nQuantified impact...",
      analysis: { strengths: [], gaps: [] },
    })
    vi.mocked(api.generateCoverLetter).mockResolvedValue({
      id: 43, content: "Dear Hiring Manager,...",
    })

    render(<PreviewModal jobId={1} jobTitle="Backend Engineer" company="BigTech" onClose={vi.fn()} />)

    await waitFor(() => expect(api.analyzeResumeFit).toHaveBeenCalledWith(1))
    await waitFor(() => expect(screen.getByText(/Suggested Improvements/)).toBeInTheDocument())

    const applyBtn = await screen.findByRole("button", { name: /Apply.*Generate Resume/ })
    await userEvent.click(applyBtn)

    await waitFor(() => expect(api.generateResume).toHaveBeenCalledWith(1, expect.any(Object)))
    await waitFor(() => expect(api.generateCoverLetter).toHaveBeenCalledWith(1, expect.any(Object)))
    await waitFor(() => expect(screen.getByText(/Tailored Resume/)).toBeInTheDocument())
    expect(screen.getByText(/Dear Hiring Manager/)).toBeInTheDocument()
  })

  it("shows empty-KB state when listEntries returns no experiences", async () => {
    vi.mocked(api.listEntries).mockResolvedValue({
      experiences: [], skills: [], education: [], projects: [],
    })

    render(<PreviewModal jobId={1} jobTitle="Backend Engineer" company="BigTech" onClose={vi.fn()} />)

    await waitFor(() => expect(screen.getByText(/Knowledge Bank is Empty/)).toBeInTheDocument())
    expect(api.analyzeResumeFit).not.toHaveBeenCalled()
  })

  it("surfaces analysis errors with a Try Again button", async () => {
    vi.mocked(api.analyzeResumeFit).mockRejectedValue(new Error("LLM_REQUIRED"))

    render(<PreviewModal jobId={1} jobTitle="Backend Engineer" company="BigTech" onClose={vi.fn()} />)

    await waitFor(() => expect(screen.getByText(/LLM_REQUIRED/)).toBeInTheDocument())
    expect(screen.getByRole("button", { name: /Try Again/ })).toBeInTheDocument()
  })
})
