/**
 * Category picker save — TDD tests for the "Save as" dropdown
 * on extracted knowledge items.
 *
 * Covers:
 * - Renders a "Save as" button for each extracted item
 * - Clicking shows category options (Experience, Project, Volunteering, etc.)
 * - Selecting a category calls onSave with the item data + chosen category
 * - All categories from KNOWLEDGE_CATEGORIES are shown
 */

import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi } from "vitest"
import CategorySaveButton from "@/components/knowledge/CategorySaveButton"
import { KNOWLEDGE_CATEGORIES } from "@/components/knowledge/CategorySaveButton"

describe("CategorySaveButton", () => {
  const sampleData = {
    title: "Judgement Card Game",
    description: "A trick-taking card game",
    tech_stack: "React, Python",
  }

  it("renders a Save as button", () => {
    render(<CategorySaveButton data={sampleData} onSave={vi.fn()} />)
    expect(screen.getByRole("button", { name: /Save as/i })).toBeInTheDocument()
  })

  it("clicking Save as shows all category options", async () => {
    render(<CategorySaveButton data={sampleData} onSave={vi.fn()} />)
    await userEvent.click(screen.getByRole("button", { name: /Save as/i }))

    for (const category of KNOWLEDGE_CATEGORIES) {
      expect(screen.getByRole("button", { name: category.label })).toBeInTheDocument()
    }
  })

  it("selecting Experience calls onSave with type='job'", async () => {
    const handleSave = vi.fn()
    render(<CategorySaveButton data={sampleData} onSave={handleSave} />)

    await userEvent.click(screen.getByRole("button", { name: /Save as/i }))
    await userEvent.click(screen.getByRole("button", { name: "Experience" }))

    expect(handleSave).toHaveBeenCalledTimes(1)
    expect(handleSave).toHaveBeenCalledWith("job", sampleData)
  })

  it("selecting Project calls onSave with type='project'", async () => {
    const handleSave = vi.fn()
    render(<CategorySaveButton data={sampleData} onSave={handleSave} />)

    await userEvent.click(screen.getByRole("button", { name: /Save as/i }))
    await userEvent.click(screen.getByRole("button", { name: "Project" }))

    expect(handleSave).toHaveBeenCalledTimes(1)
    expect(handleSave).toHaveBeenCalledWith("project", sampleData)
  })

  it("selecting Volunteering calls onSave with type='volunteering'", async () => {
    const handleSave = vi.fn()
    render(<CategorySaveButton data={sampleData} onSave={handleSave} />)

    await userEvent.click(screen.getByRole("button", { name: /Save as/i }))
    await userEvent.click(screen.getByRole("button", { name: "Volunteering" }))

    expect(handleSave).toHaveBeenCalledTimes(1)
    expect(handleSave).toHaveBeenCalledWith("volunteering", sampleData)
  })

  it("KNOWLEDGE_CATEGORIES includes at least Experience, Project, Volunteering, Education", () => {
    const categoryTypes = KNOWLEDGE_CATEGORIES.map(category => category.type)
    expect(categoryTypes).toContain("job")
    expect(categoryTypes).toContain("project")
    expect(categoryTypes).toContain("volunteering")
    expect(categoryTypes).toContain("education")
  })

  it("menu closes after selecting a category", async () => {
    render(<CategorySaveButton data={sampleData} onSave={vi.fn()} />)
    await userEvent.click(screen.getByRole("button", { name: /Save as/i }))
    await userEvent.click(screen.getByRole("button", { name: "Project" }))

    // Menu should be closed — category buttons gone
    expect(screen.queryByRole("button", { name: "Experience" })).toBeNull()
  })
})
