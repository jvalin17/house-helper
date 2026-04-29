/**
 * JobDetail — modal that summarizes a single job and exposes actions.
 *
 * Covers parsed_data shapes (object, malformed JSON, missing fields),
 * match-breakdown rendering, LLM analysis sub-component, the rating
 * row, and the close + generate actions.
 */

import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi } from "vitest"
import JobDetail from "@/components/JobDetail"
import type { Job } from "@/types"

const baseJob: Job = {
  id: 1,
  title: "Backend Engineer",
  company: "Acme",
  match_score: 0.82,
  parsed_data: JSON.stringify({
    description: "Build scalable services for the platform.",
    required_skills: ["Python", "Postgres"],
    preferred_skills: ["Kafka"],
    location: "Remote-USA",
    salary_range: "$150k-$180k",
    remote_status: "Remote",
  }),
  match_breakdown: JSON.stringify({
    skills: 0.9,
    text_similarity: 0.7,
  }),
  url: "https://example.com/jobs/1",
}

function renderDetail(over: Partial<Job> = {}, handlers?: { onClose?: () => void; onGenerate?: () => void; onRate?: (r: string) => void }) {
  const onClose = handlers?.onClose ?? vi.fn()
  const onGenerate = handlers?.onGenerate ?? vi.fn()
  const onRate = handlers?.onRate ?? vi.fn()
  render(
    <JobDetail
      job={{ ...baseJob, ...over }}
      onClose={onClose}
      onGenerate={onGenerate}
      onRate={onRate}
    />
  )
  return { onClose, onGenerate, onRate }
}

describe("JobDetail", () => {
  it("renders title, company, and match score", () => {
    renderDetail()
    expect(screen.getByText("Backend Engineer")).toBeInTheDocument()
    expect(screen.getByText("Acme")).toBeInTheDocument()
    expect(screen.getByText("82%")).toBeInTheDocument()
  })

  it("renders required and preferred skills", () => {
    renderDetail()
    expect(screen.getByText("Required Skills")).toBeInTheDocument()
    expect(screen.getByText("Python")).toBeInTheDocument()
    expect(screen.getByText("Postgres")).toBeInTheDocument()
    expect(screen.getByText("Nice to Have")).toBeInTheDocument()
    expect(screen.getByText("Kafka")).toBeInTheDocument()
  })

  it("renders the original job link with the safe URL", () => {
    renderDetail()
    const link = screen.getByRole("link", { name: /View original job posting/ })
    expect(link).toHaveAttribute("href", "https://example.com/jobs/1")
    expect(link).toHaveAttribute("target", "_blank")
  })

  it("falls back to source_url when url is missing", () => {
    renderDetail({ url: null, source_url: "https://other.example/jobs/x" })
    expect(
      screen.getByRole("link", { name: /View original job posting/ })
    ).toHaveAttribute("href", "https://other.example/jobs/x")
  })

  it("hides match-score block when match_score is null", () => {
    renderDetail({ match_score: null })
    expect(screen.queryByText(/Match Score/)).not.toBeInTheDocument()
  })

  it("renders local match copy when no llm_score is present", () => {
    renderDetail()
    expect(screen.getByText(/Matched locally/)).toBeInTheDocument()
  })

  it("renders AI match copy and LLM analysis sections when llm_analysis is provided", () => {
    renderDetail({
      match_breakdown: JSON.stringify({
        skills: 0.6,
        llm_score: 0.9,
        llm_analysis: {
          strengths: ["Strong Python"],
          gaps: ["No Kafka"],
          recommendations: ["Highlight async work"],
        },
      }),
    })
    expect(screen.getByText(/Matched with AI/)).toBeInTheDocument()
    expect(screen.getByText("Strengths")).toBeInTheDocument()
    expect(screen.getByText("+ Strong Python")).toBeInTheDocument()
    expect(screen.getByText("Gaps")).toBeInTheDocument()
    expect(screen.getByText("- No Kafka")).toBeInTheDocument()
    expect(screen.getByText("Suggestions")).toBeInTheDocument()
    expect(screen.getByText("Highlight async work")).toBeInTheDocument()
  })

  it("renders breakdown rows with humanized keys", () => {
    renderDetail()
    expect(screen.getByText("skills")).toBeInTheDocument()
    expect(screen.getByText("text similarity")).toBeInTheDocument()
    expect(screen.getByText("90%")).toBeInTheDocument()
    expect(screen.getByText("70%")).toBeInTheDocument()
  })

  it("invokes onRate with the chosen rating", async () => {
    const { onRate } = renderDetail()
    await userEvent.click(screen.getByRole("button", { name: "Yes" }))
    await userEvent.click(screen.getByRole("button", { name: "Somewhat" }))
    await userEvent.click(screen.getByRole("button", { name: "No" }))
    expect(onRate).toHaveBeenNthCalledWith(1, "good")
    expect(onRate).toHaveBeenNthCalledWith(2, "partial")
    expect(onRate).toHaveBeenNthCalledWith(3, "poor")
  })

  it("invokes onClose when Close is clicked", async () => {
    const { onClose } = renderDetail()
    const closeButtons = screen.getAllByRole("button", { name: "Close" })
    await userEvent.click(closeButtons[0])
    expect(onClose).toHaveBeenCalled()
  })

  it("invokes onGenerate when the generate button is clicked", async () => {
    const { onGenerate } = renderDetail()
    await userEvent.click(screen.getByRole("button", { name: /Generate Resume & Cover Letter/ }))
    expect(onGenerate).toHaveBeenCalled()
  })

  it("falls back to defaults when title and company are missing", () => {
    renderDetail({ title: "", company: "" })
    expect(screen.getByText("Untitled")).toBeInTheDocument()
    expect(screen.getByText("Unknown company")).toBeInTheDocument()
  })

  it("survives a malformed parsed_data JSON string", () => {
    renderDetail({ parsed_data: "{not json" })
    expect(screen.getByText("Backend Engineer")).toBeInTheDocument()
    expect(screen.queryByText("Required Skills")).not.toBeInTheDocument()
  })

  it("hides description when parsed.description is missing", () => {
    renderDetail({
      parsed_data: JSON.stringify({ required_skills: ["Go"] }),
    })
    expect(screen.queryByText("Description")).not.toBeInTheDocument()
  })

  it("renders location, salary, and remote status when present", () => {
    renderDetail()
    expect(screen.getByText(/Remote-USA/)).toBeInTheDocument()
    expect(screen.getByText(/\$150k-\$180k/)).toBeInTheDocument()
    expect(screen.getByText("Remote")).toBeInTheDocument()
  })
})
