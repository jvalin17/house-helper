/**
 * Edit knowledge entries — TDD tests for inline editing of
 * education, projects, and skills.
 *
 * Covers:
 * - Education: Edit button shows form, save calls onEdit with updated data
 * - Project: Edit button shows form, save calls onEdit with updated data
 * - Experience: Edit passes editingId to onSave (bug fix verification)
 */

import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi } from "vitest"
import EducationList from "@/components/knowledge/EducationList"
import ProjectList from "@/components/knowledge/ProjectList"
import ExperienceList from "@/components/knowledge/ExperienceList"
import type { Education, Experience, Project } from "@/types"

const SAMPLE_EDUCATION: Education[] = [
  { id: 1, institution: "MIT", degree: "BS", field: "Computer Science", end_date: "2020" },
]

const SAMPLE_PROJECTS: Project[] = [
  { id: 1, name: "SearchApp", description: "A search engine", tech_stack: "Python", url: "https://example.com" },
]

describe("EducationList — inline edit", () => {
  it("shows an Edit button for each education entry", () => {
    render(<EducationList education={SAMPLE_EDUCATION} onDelete={vi.fn()} onEdit={vi.fn()} />)
    expect(screen.getByRole("button", { name: /Edit/i })).toBeInTheDocument()
  })

  it("clicking Edit shows editable form fields", async () => {
    render(<EducationList education={SAMPLE_EDUCATION} onDelete={vi.fn()} onEdit={vi.fn()} />)
    await userEvent.click(screen.getByRole("button", { name: /Edit/i }))

    expect(screen.getByDisplayValue("MIT")).toBeInTheDocument()
    expect(screen.getByDisplayValue("BS")).toBeInTheDocument()
    expect(screen.getByDisplayValue("Computer Science")).toBeInTheDocument()
  })

  it("saving edited education calls onEdit with id and updated fields", async () => {
    const handleEdit = vi.fn()
    render(<EducationList education={SAMPLE_EDUCATION} onDelete={vi.fn()} onEdit={handleEdit} />)

    await userEvent.click(screen.getByRole("button", { name: /Edit/i }))

    const institutionInput = screen.getByDisplayValue("MIT")
    await userEvent.clear(institutionInput)
    await userEvent.type(institutionInput, "Stanford")

    await userEvent.click(screen.getByRole("button", { name: /Save/i }))

    expect(handleEdit).toHaveBeenCalledWith(1, expect.objectContaining({ institution: "Stanford" }))
  })

  it("Cancel closes the edit form without calling onEdit", async () => {
    const handleEdit = vi.fn()
    render(<EducationList education={SAMPLE_EDUCATION} onDelete={vi.fn()} onEdit={handleEdit} />)

    await userEvent.click(screen.getByRole("button", { name: /Edit/i }))
    await userEvent.click(screen.getByRole("button", { name: /Cancel/i }))

    expect(handleEdit).not.toHaveBeenCalled()
    expect(screen.queryByDisplayValue("MIT")).not.toBeInTheDocument()
  })
})

describe("ProjectList — inline edit", () => {
  it("shows an Edit button for each project", () => {
    render(<ProjectList projects={SAMPLE_PROJECTS} onDelete={vi.fn()} onEdit={vi.fn()} />)
    expect(screen.getByRole("button", { name: /Edit/i })).toBeInTheDocument()
  })

  it("clicking Edit shows editable form fields", async () => {
    render(<ProjectList projects={SAMPLE_PROJECTS} onDelete={vi.fn()} onEdit={vi.fn()} />)
    await userEvent.click(screen.getByRole("button", { name: /Edit/i }))

    expect(screen.getByDisplayValue("SearchApp")).toBeInTheDocument()
    expect(screen.getByDisplayValue("A search engine")).toBeInTheDocument()
    expect(screen.getByDisplayValue("Python")).toBeInTheDocument()
  })

  it("saving edited project calls onEdit with id and updated fields", async () => {
    const handleEdit = vi.fn()
    render(<ProjectList projects={SAMPLE_PROJECTS} onDelete={vi.fn()} onEdit={handleEdit} />)

    await userEvent.click(screen.getByRole("button", { name: /Edit/i }))

    const nameInput = screen.getByDisplayValue("SearchApp")
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, "NewApp")

    await userEvent.click(screen.getByRole("button", { name: /Save/i }))

    expect(handleEdit).toHaveBeenCalledWith(1, expect.objectContaining({ name: "NewApp" }))
  })
})

describe("ExperienceList — edit passes editingId to onSave", () => {
  const SAMPLE_EXPERIENCE: Experience[] = [
    { id: 42, title: "Engineer", company: "Acme", start_date: "2020", end_date: "2023", description: "Built things" },
  ]

  it("editing an experience passes the editingId to onSave", async () => {
    const handleSave = vi.fn()
    render(
      <ExperienceList
        experiences={SAMPLE_EXPERIENCE}
        onSave={handleSave}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />
    )

    await userEvent.click(screen.getByRole("button", { name: /Edit/i }))
    await userEvent.click(screen.getByRole("button", { name: /Update/i }))

    expect(handleSave).toHaveBeenCalledTimes(1)
    // Second argument should be the editing ID (42)
    expect(handleSave).toHaveBeenCalledWith(
      expect.objectContaining({ title: "Engineer", company: "Acme" }),
      42
    )
  })

  it("creating a new experience passes undefined as editingId", async () => {
    const handleSave = vi.fn()
    render(
      <ExperienceList
        experiences={[]}
        onSave={handleSave}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
      />
    )

    await userEvent.click(screen.getByRole("button", { name: /\+ Add/i }))

    const titleInput = screen.getByPlaceholderText(/Title/i)
    await userEvent.type(titleInput, "New Role")
    const companyInput = screen.getByPlaceholderText(/Company/i)
    await userEvent.type(companyInput, "NewCo")

    await userEvent.click(screen.getByRole("button", { name: /Save/i }))

    expect(handleSave).toHaveBeenCalledTimes(1)
    // Second argument should be undefined (no editingId for new)
    expect(handleSave).toHaveBeenCalledWith(
      expect.objectContaining({ title: "New Role", company: "NewCo" }),
      undefined
    )
  })
})
