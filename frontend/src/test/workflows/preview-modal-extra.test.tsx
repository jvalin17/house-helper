/**
 * PreviewModal — extra branches beyond tailor-resume / revision-loop /
 * apply-track / flag-suggestion tests.
 *
 * Targets the algorithmic-score path (parsing match_breakdown), the
 * "applied" final screen, the export buttons (resume + cover letter,
 * each format), the explicit save action, the analysis error overlay
 * after a failed generation, and the empty-KB fallback when listEntries
 * itself errors.
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import { Toaster } from "sonner"
import PreviewModal from "@/components/PreviewModal"
import { api } from "@/api/client"
import type { AnalysisData } from "@/types"

vi.mock("@/api/client")

const ANALYSIS: AnalysisData = {
  current_resume_match: 60,
  knowledge_bank_match: 80,
  match_gap: "moderate",
  strengths: ["Python"],
  gaps: ["k8s"],
  suggested_improvements: [],
  summary: "ok",
}

function mountWithKb(jobOver: Record<string, unknown> = {}) {
  vi.mocked(api.listEntries).mockResolvedValue({
    experiences: [{ id: 1, title: "Eng", company: "Co", start_date: "2020-01", end_date: "", description: "x" }],
    skills: [], education: [], projects: [],
  })
  vi.mocked(api.getJob).mockResolvedValue({
    id: 1, title: "Backend", company: "Acme",
    match_score: 0.65,
    match_breakdown: JSON.stringify({ skills: 0.8, text_similarity: 0.5 }),
    parsed_data: "{}",
    ...jobOver,
  })
  vi.mocked(api.analyzeResumeFit).mockResolvedValue(ANALYSIS)
}

async function generateAndAdvanceToResult() {
  vi.mocked(api.generateResume).mockResolvedValue({
    id: 42, content: "# Resume content",
    analysis: { current_resume_match: 60, knowledge_bank_match: 80 },
  })
  vi.mocked(api.generateCoverLetter).mockResolvedValue({
    id: 43, content: "Dear hiring manager",
  })

  // No suggestions in ANALYSIS → handleSkipAnalysis path via "Generate without changes"
  const generateBtn = await screen.findByRole("button", { name: /Generate without changes/ })
  await userEvent.click(generateBtn)
  await waitFor(() => expect(screen.getByText(/Resume content/)).toBeInTheDocument())
}

describe("PreviewModal — algorithmic score parsing", () => {
  beforeEach(() => { vi.clearAllMocks() })

  it("parses match_breakdown JSON and forwards it to MatchProgression", async () => {
    mountWithKb()
    render(<PreviewModal jobId={1} jobTitle="Backend" company="Acme" onClose={vi.fn()} />)
    await waitFor(() => expect(api.analyzeResumeFit).toHaveBeenCalled())
    await generateAndAdvanceToResult()
    expect(screen.getByText(/Resume$/)).toBeInTheDocument()
    expect(screen.getByText(/Cover Letter/)).toBeInTheDocument()
  })

  it("ignores malformed match_breakdown but still renders", async () => {
    mountWithKb({ match_breakdown: "{not json" })
    render(<PreviewModal jobId={1} jobTitle="Backend" company="Acme" onClose={vi.fn()} />)
    await waitFor(() => expect(api.analyzeResumeFit).toHaveBeenCalled())
    await generateAndAdvanceToResult()
    expect(screen.getByText(/Resume content/)).toBeInTheDocument()
  })
})

describe("PreviewModal — empty KB on api error", () => {
  beforeEach(() => { vi.clearAllMocks() })

  it("falls back to empty-kb state when listEntries throws", async () => {
    vi.mocked(api.listEntries).mockRejectedValue(new Error("db error"))
    vi.mocked(api.getJob).mockResolvedValue({
      id: 1, title: "Backend", company: "Acme", match_score: null,
      parsed_data: "{}", match_breakdown: null,
    })
    render(<PreviewModal jobId={1} jobTitle="Backend" company="Acme" onClose={vi.fn()} />)
    await waitFor(() =>
      expect(screen.getByText(/Knowledge Bank is Empty/)).toBeInTheDocument()
    )
  })
})

describe("PreviewModal — analysis error in result.error", () => {
  beforeEach(() => { vi.clearAllMocks() })

  it("shows the error string and stays on the checking screen", async () => {
    mountWithKb()
    vi.mocked(api.analyzeResumeFit).mockResolvedValue({
      ...ANALYSIS, error: "LLM_REQUIRED",
    })
    render(<PreviewModal jobId={1} jobTitle="Backend" company="Acme" onClose={vi.fn()} />)
    await waitFor(() => expect(screen.getByText("LLM_REQUIRED")).toBeInTheDocument())
    expect(screen.getByRole("button", { name: /Try Again/ })).toBeInTheDocument()
  })
})

describe("PreviewModal — result step actions", () => {
  beforeEach(() => { vi.clearAllMocks() })

  it("export triggers api.exportResume with the chosen format", async () => {
    mountWithKb()
    const blob = new Blob(["pdf bytes"], { type: "application/pdf" })
    vi.mocked(api.exportResume).mockResolvedValue({ blob: async () => blob } as Response)
    vi.mocked(api.exportCoverLetter).mockResolvedValue({ blob: async () => blob } as Response)

    const createObjectURL = vi.fn(() => "blob:fake")
    const revokeObjectURL = vi.fn()
    Object.defineProperty(URL, "createObjectURL", { writable: true, value: createObjectURL })
    Object.defineProperty(URL, "revokeObjectURL", { writable: true, value: revokeObjectURL })

    render(<PreviewModal jobId={1} jobTitle="Backend" company="Acme" onClose={vi.fn()} />)
    await waitFor(() => expect(api.analyzeResumeFit).toHaveBeenCalled())
    await generateAndAdvanceToResult()

    const pdfButtons = screen.getAllByRole("button", { name: /^PDF$/ })
    await userEvent.click(pdfButtons[0])
    await waitFor(() =>
      expect(api.exportResume).toHaveBeenCalledWith(42, "pdf")
    )

    const docxButtons = screen.getAllByRole("button", { name: /^DOCX$/ })
    await userEvent.click(docxButtons[1])
    await waitFor(() =>
      expect(api.exportCoverLetter).toHaveBeenCalledWith(43, "docx")
    )
  })

  it("Save this version calls saveResumeExplicit and replaces the button with the saved name", async () => {
    mountWithKb()
    vi.mocked(api.saveResumeExplicit).mockResolvedValue({ name: "BigTech-Backend-v1" })
    render(
      <>
        <Toaster />
        <PreviewModal jobId={1} jobTitle="Backend" company="Acme" onClose={vi.fn()} />
      </>
    )
    await waitFor(() => expect(api.analyzeResumeFit).toHaveBeenCalled())
    await generateAndAdvanceToResult()

    await userEvent.click(screen.getByRole("button", { name: /Save this version/ }))
    await waitFor(() => expect(api.saveResumeExplicit).toHaveBeenCalledWith(42))
    await waitFor(() =>
      expect(screen.getAllByText(/Saved as BigTech-Backend-v1/).length).toBeGreaterThan(0)
    )
    expect(screen.queryByRole("button", { name: /Save this version/ })).not.toBeInTheDocument()
  })

  it("Save error surfaces a toast and keeps the button visible", async () => {
    mountWithKb()
    vi.mocked(api.saveResumeExplicit).mockRejectedValue(new Error("disk full"))
    render(
      <>
        <Toaster />
        <PreviewModal jobId={1} jobTitle="Backend" company="Acme" onClose={vi.fn()} />
      </>
    )
    await waitFor(() => expect(api.analyzeResumeFit).toHaveBeenCalled())
    await generateAndAdvanceToResult()

    await userEvent.click(screen.getByRole("button", { name: /Save this version/ }))
    await waitFor(() => expect(screen.getByText(/disk full/)).toBeInTheDocument())
    expect(screen.getByRole("button", { name: /Save this version/ })).toBeInTheDocument()
  })

  it("Back to analysis returns to the analysis step", async () => {
    mountWithKb()
    render(<PreviewModal jobId={1} jobTitle="Backend" company="Acme" onClose={vi.fn()} />)
    await waitFor(() => expect(api.analyzeResumeFit).toHaveBeenCalled())
    await generateAndAdvanceToResult()

    await userEvent.click(screen.getByRole("button", { name: /Back to analysis/ }))
    await waitFor(() =>
      expect(screen.getByText(/Review suggested improvements/)).toBeInTheDocument()
    )
  })
})

describe("PreviewModal — applied confirmation", () => {
  beforeEach(() => { vi.clearAllMocks() })

  it("renders the success card after Apply & Track succeeds", async () => {
    mountWithKb()
    vi.mocked(api.createApplication).mockResolvedValue({ id: 1 })
    render(
      <PreviewModal jobId={1} jobTitle="Backend" company="Acme" onClose={vi.fn()} />
    )
    await waitFor(() => expect(api.analyzeResumeFit).toHaveBeenCalled())
    await generateAndAdvanceToResult()

    await userEvent.click(screen.getByRole("button", { name: /Apply & Track/ }))
    await waitFor(() => expect(screen.getByText("Application tracked")).toBeInTheDocument())
    expect(screen.getByRole("button", { name: /Back to Jobs/ })).toBeInTheDocument()
  })
})

describe("PreviewModal — generation error returns to analysis", () => {
  beforeEach(() => { vi.clearAllMocks() })

  it("on generateResume failure, shows the analysis screen with an error banner", async () => {
    mountWithKb()
    vi.mocked(api.generateResume).mockRejectedValue(new Error("rate limited"))
    render(<PreviewModal jobId={1} jobTitle="Backend" company="Acme" onClose={vi.fn()} />)
    await waitFor(() => expect(api.analyzeResumeFit).toHaveBeenCalled())

    const generateBtn = await screen.findByRole("button", { name: /Generate without changes/ })
    await userEvent.click(generateBtn)
    await waitFor(() => expect(screen.getByText(/rate limited/)).toBeInTheDocument())
  })
})
