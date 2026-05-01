/**
 * Clear Knowledge Bank — tests that the clear button calls the API
 * and the skills/experiences disappear from the UI after clearing.
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import KnowledgeBank from "@/components/KnowledgeBank"
import { api } from "@/api/client"

vi.mock("@/api/client")

const MOCK_ENTRIES = {
  experiences: [{ id: 1, title: "Engineer", company: "Acme", start_date: "2020", end_date: "", description: "Built things" }],
  skills: [{ id: 1, name: "Python", category: "Language" }, { id: 2, name: "React", category: "Framework" }],
  education: [{ id: 1, institution: "MIT", degree: "BS", field: "CS", end_date: "2020" }],
  projects: [{ id: 1, name: "App", description: "A cool app", tech_stack: "Python", url: "" }],
}

describe("Clear Knowledge Bank", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.listEntries).mockResolvedValue(MOCK_ENTRIES)
    vi.mocked(api.listSkills).mockResolvedValue(MOCK_ENTRIES.skills)
    vi.mocked(api.getStoredResume).mockResolvedValue({ has_resume: false })
    vi.mocked(api.listTemplates).mockResolvedValue([])
  })

  it("renders a Clear Knowledge Bank button", async () => {
    render(<KnowledgeBank />)
    await waitFor(() => expect(screen.getByText("Python")).toBeInTheDocument())
    expect(screen.getByRole("button", { name: /Clear Knowledge Bank/i })).toBeInTheDocument()
  })

  it("calls resetKnowledgeBank API when confirmed", async () => {
    vi.mocked(api.resetKnowledgeBank).mockResolvedValue({
      experiences_deleted: 1, skills_deleted: 2, education_deleted: 1, projects_deleted: 1,
    })

    // Mock window.confirm to return true
    vi.spyOn(window, "confirm").mockReturnValue(true)

    render(<KnowledgeBank />)
    await waitFor(() => expect(screen.getByText("Python")).toBeInTheDocument())

    await userEvent.click(screen.getByRole("button", { name: /Clear Knowledge Bank/i }))

    await waitFor(() => expect(api.resetKnowledgeBank).toHaveBeenCalled())
  })

  it("does NOT call API when confirm is cancelled", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false)

    render(<KnowledgeBank />)
    await waitFor(() => expect(screen.getByText("Python")).toBeInTheDocument())

    await userEvent.click(screen.getByRole("button", { name: /Clear Knowledge Bank/i }))

    expect(api.resetKnowledgeBank).not.toHaveBeenCalled()
  })

  it("refreshes the display after clearing — skills disappear", async () => {
    vi.mocked(api.resetKnowledgeBank).mockResolvedValue({
      experiences_deleted: 1, skills_deleted: 2, education_deleted: 1, projects_deleted: 1,
    })
    vi.spyOn(window, "confirm").mockReturnValue(true)

    render(<KnowledgeBank />)
    await waitFor(() => expect(screen.getByText("Python")).toBeInTheDocument())

    // After clear, the next listEntries/listSkills call should return empty
    vi.mocked(api.listEntries).mockResolvedValue({ experiences: [], skills: [], education: [], projects: [] })
    vi.mocked(api.listSkills).mockResolvedValue([])

    await userEvent.click(screen.getByRole("button", { name: /Clear Knowledge Bank/i }))

    await waitFor(() => expect(screen.queryByText("Python")).not.toBeInTheDocument())
    await waitFor(() => expect(screen.getByText(/No skills yet/i)).toBeInTheDocument())
  })
})
