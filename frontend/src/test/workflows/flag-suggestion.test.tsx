/**
 * Workflow 13: Flag incorrect suggestion — the Flag button calls rejectSuggestion.
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import ResumeAnalysis from "@/components/ResumeAnalysis"
import { api } from "@/api/client"
import type { AnalysisData } from "@/types"

vi.mock("@/api/client")

const analysis: AnalysisData = {
  current_resume_match: 60,
  knowledge_bank_match: 80,
  match_gap: "moderate",
  strengths: ["Python"],
  gaps: ["Kubernetes"],
  summary: "ok",
  suggested_improvements: [
    { type: "bullet_rewrite", description: "Add LLM sentiment analysis to feedback system",
      impact: "scale", source: "experience" },
    { type: "bullet_rewrite", description: "Quantify Python REST API throughput",
      impact: "scale", source: "experience" },
  ],
}

beforeEach(() => {
  vi.clearAllMocks()
})

describe("Workflow: Flag incorrect suggestion", () => {
  it("clicking Flag incorrect calls rejectSuggestion with the suggestion text", async () => {
    vi.mocked(api.rejectSuggestion).mockResolvedValue({ id: 1 })

    render(
      <ResumeAnalysis
        analysis={analysis}
        jobTitle="Backend Engineer"
        company="Acme"
        onApplyAndGenerate={vi.fn()}
        onSkip={vi.fn()}
        loading={false}
      />
    )

    const flags = screen.getAllByRole("button", { name: /Flag incorrect/ })
    await userEvent.click(flags[0])

    await waitFor(() => expect(api.rejectSuggestion).toHaveBeenCalled())
    const payload = vi.mocked(api.rejectSuggestion).mock.calls[0][0]
    expect(payload.suggestion_text).toContain("LLM sentiment analysis")
  })

  it("does not crash if rejectSuggestion fails", async () => {
    vi.mocked(api.rejectSuggestion).mockRejectedValue(new Error("API_DOWN"))

    render(
      <ResumeAnalysis
        analysis={analysis}
        jobTitle="Backend Engineer"
        company="Acme"
        onApplyAndGenerate={vi.fn()}
        onSkip={vi.fn()}
        loading={false}
      />
    )

    const flags = screen.getAllByRole("button", { name: /Flag incorrect/ })
    await userEvent.click(flags[0])

    await waitFor(() => expect(api.rejectSuggestion).toHaveBeenCalled())
    expect(screen.getByText(/Add LLM sentiment analysis/)).toBeInTheDocument()
  })
})
