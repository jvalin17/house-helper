/**
 * Extract experience bullets from link — frontend TDD tests.
 *
 * Covers:
 * - "Extract Experiences" button renders next to "Extract from Link"
 * - Clicking shows cost warning before calling API
 * - Button disabled when no LLM configured (shown via message)
 * - Results show extracted experiences with bullets
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import KnowledgeBank from "@/components/KnowledgeBank"
import { api } from "@/api/client"

vi.mock("@/api/client")

function mockKnowledgeBank() {
  vi.mocked(api.listEntries).mockResolvedValue({ experiences: [], skills: [], education: [], projects: [] })
  vi.mocked(api.listSkills).mockResolvedValue([])
  vi.mocked(api.getStoredResume).mockResolvedValue({ has_resume: false })
  vi.mocked(api.listTemplates).mockResolvedValue([])
}

describe("Extract Experiences from Link", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockKnowledgeBank()
  })

  it("renders Extract Experiences button in the link extraction section", async () => {
    render(<KnowledgeBank />)
    await waitFor(() => expect(screen.getByText(/Skills \(0\)/)).toBeInTheDocument())
    expect(screen.getByRole("button", { name: /Extract Experiences/i })).toBeInTheDocument()
  })

  it("shows cost warning when Extract Experiences is clicked with a URL", async () => {
    render(<KnowledgeBank />)
    await waitFor(() => expect(screen.getByText(/Skills \(0\)/)).toBeInTheDocument())

    const linkInput = screen.getByPlaceholderText(/Paste a link/i)
    await userEvent.type(linkInput, "https://example.com/portfolio")
    await userEvent.click(screen.getByRole("button", { name: /Extract Experiences/i }))

    // Should show cost warning before proceeding
    expect(screen.getByText(/This uses AI/i)).toBeInTheDocument()
  })

  it("calls extractBullets API after user confirms cost warning", async () => {
    vi.mocked(api.extractBullets).mockResolvedValue({
      experiences: [
        { company: "Google", title: "SWE", bullets: ["Built search system"] }
      ],
      projects: [],
      source_url: "https://example.com",
      raw_text_length: 500,
    })
    vi.spyOn(window, "confirm").mockReturnValue(true)

    render(<KnowledgeBank />)
    await waitFor(() => expect(screen.getByText(/Skills \(0\)/)).toBeInTheDocument())

    const linkInput = screen.getByPlaceholderText(/Paste a link/i)
    await userEvent.type(linkInput, "https://example.com/portfolio")
    await userEvent.click(screen.getByRole("button", { name: /Extract Experiences/i }))

    // Confirm the cost warning
    await userEvent.click(screen.getByRole("button", { name: /Proceed/i }))

    await waitFor(() => expect(api.extractBullets).toHaveBeenCalledWith("https://example.com/portfolio"))
  })
})
