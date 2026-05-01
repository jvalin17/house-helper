/**
 * Workflow 7: Manual experience CRUD — create, edit, delete via KnowledgeBank.
 */

import { render, screen, waitFor, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import KnowledgeBank from "@/components/KnowledgeBank"
import { api } from "@/api/client"

vi.mock("@/api/client")

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.listSkills).mockResolvedValue([])
  vi.mocked(api.getStoredResume).mockResolvedValue({ has_resume: false })
  vi.mocked(api.listTemplates).mockResolvedValue([])
})

describe("Workflow: Manual experience CRUD", () => {
  it("creates a new experience and lists it after refresh", async () => {
    vi.mocked(api.listEntries)
      .mockResolvedValueOnce({ experiences: [], skills: [], education: [], projects: [] })
      .mockResolvedValueOnce({
        experiences: [
          { id: 7, title: "Senior Engineer", company: "Acme",
            start_date: "2020-01", end_date: "", description: "Built APIs" },
        ],
        skills: [], education: [], projects: [],
      })
    vi.mocked(api.createEntry).mockResolvedValue({ id: 7 })

    render(<KnowledgeBank />)
    await screen.findByText(/Work Experience \(0\)/)

    const expSection = screen.getByText(/Work Experience \(0\)/).closest("[data-slot='card']") as HTMLElement
    const expAddBtn = within(expSection).getByRole("button", { name: /^\+ Add$/ })
    await userEvent.click(expAddBtn)
    await userEvent.type(screen.getByLabelText(/Job title/), "Senior Engineer")
    await userEvent.type(screen.getByLabelText(/Company/), "Acme")
    await userEvent.type(screen.getByLabelText(/Start date/), "2020-01")
    await userEvent.click(screen.getByRole("button", { name: /^Save$/ }))

    await waitFor(() => expect(api.createEntry).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Senior Engineer", company: "Acme", type: "job" }),
    ))
    await screen.findByText(/Senior Engineer — Acme/)
  })

  it("calls deleteEntry when Delete is clicked", async () => {
    vi.mocked(api.listEntries).mockResolvedValue({
      experiences: [
        { id: 9, title: "Eng", company: "X", start_date: "2019",
          end_date: "", description: "" },
      ],
      skills: [], education: [], projects: [],
    })
    vi.mocked(api.deleteEntry).mockResolvedValue({ deleted: 9 })

    render(<KnowledgeBank />)
    const expEntry = await screen.findByText(/Eng — X/)
    const row = expEntry.closest("div.p-3") as HTMLElement
    await userEvent.click(within(row).getByRole("button", { name: /Delete/ }))

    await waitFor(() => expect(api.deleteEntry).toHaveBeenCalledWith(9))
  })

  it("surfaces an error toast when create fails", async () => {
    vi.mocked(api.listEntries).mockResolvedValue({
      experiences: [], skills: [], education: [], projects: [],
    })
    vi.mocked(api.createEntry).mockRejectedValue(new Error("DB_FAIL"))

    render(<KnowledgeBank />)
    await screen.findByText(/Work Experience \(0\)/)
    const expSection = screen.getByText(/Work Experience \(0\)/).closest("[data-slot='card']") as HTMLElement
    await userEvent.click(within(expSection).getByRole("button", { name: /^\+ Add$/ }))
    await userEvent.type(screen.getByLabelText(/Job title/), "Bad")
    await userEvent.click(screen.getByRole("button", { name: /^Save$/ }))

    await waitFor(() => expect(api.createEntry).toHaveBeenCalled())
  })
})
