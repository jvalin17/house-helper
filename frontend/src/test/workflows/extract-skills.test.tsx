/**
 * Workflow 6: Extract skills from link → fetched, extracted, saved on accept.
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import KnowledgeBank from "@/components/KnowledgeBank"
import { api } from "@/api/client"

vi.mock("@/api/client")

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.listEntries).mockResolvedValue({
    experiences: [], skills: [], education: [], projects: [],
  })
  vi.mocked(api.listSkills).mockResolvedValue([])
  vi.mocked(api.getStoredResume).mockResolvedValue({ has_resume: false })
  vi.mocked(api.listTemplates).mockResolvedValue([])
})

describe("Workflow: Extract skills from link", () => {
  it("fetches a URL, shows extracted skills, saves accepted ones", async () => {
    vi.mocked(api.extractSkills).mockResolvedValue({
      extracted_skills: ["Python", "FastAPI", "React"],
      raw_text: "Senior backend engineer with Python and FastAPI experience.",
      source: "url", method: "scraper",
    })
    vi.mocked(api.createSkill).mockResolvedValue({ id: 1, name: "x", category: "extracted" })

    render(<KnowledgeBank />)
    await screen.findByText(/Add Knowledge/)

    const input = screen.getByPlaceholderText(/Paste a link/)
    await userEvent.type(input, "https://example.com/profile")
    await userEvent.click(screen.getByRole("button", { name: /Extract from Link/ }))

    await waitFor(() => expect(api.extractSkills).toHaveBeenCalledWith("https://example.com/profile"))
    await screen.findByText("Python")
    await screen.findByText("FastAPI")

    await userEvent.click(screen.getByRole("button", { name: /Save 3 Skills/ }))

    await waitFor(() => expect(api.createSkill).toHaveBeenCalledTimes(3))
  })

  it("shows the error description when extraction fails", async () => {
    vi.mocked(api.extractSkills).mockRejectedValue(new Error("FETCH_BLOCKED: SSRF"))

    render(<KnowledgeBank />)
    await screen.findByText(/Add Knowledge/)
    const input = screen.getByPlaceholderText(/Paste a link/)
    await userEvent.type(input, "http://127.0.0.1/")
    await userEvent.click(screen.getByRole("button", { name: /Extract from Link/ }))

    await waitFor(() => expect(screen.getByText(/FETCH_BLOCKED/)).toBeInTheDocument())
    expect(api.createSkill).not.toHaveBeenCalled()
  })
})
