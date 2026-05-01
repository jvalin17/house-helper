/**
 * Delete skills — TDD tests for inline X on badges + category delete.
 *
 * Covers:
 * - Each skill badge contains an X button inside the badge
 * - Clicking X calls onDelete with correct skill ID
 * - Each category header has a "Delete all" button
 * - Clicking "Delete all" calls onDeleteCategory with category name
 * - No X buttons when onDelete is not provided
 * - Empty state renders correctly
 */

import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi } from "vitest"
import SkillsDisplay from "@/components/knowledge/SkillsDisplay"
import type { Skill } from "@/types"

const SAMPLE_SKILLS: Skill[] = [
  { id: 1, name: "Python", category: "Language" },
  { id: 2, name: "Java", category: "Language" },
  { id: 3, name: "React", category: "Framework" },
  { id: 4, name: "Docker", category: "DevOps" },
]

describe("SkillsDisplay — individual skill delete", () => {
  it("each skill badge contains a remove button with aria-label", () => {
    const handleDelete = vi.fn()
    render(<SkillsDisplay skills={SAMPLE_SKILLS} onDelete={handleDelete} />)

    expect(screen.getByRole("button", { name: "Remove Python" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Remove Java" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Remove React" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Remove Docker" })).toBeInTheDocument()
  })

  it("clicking remove calls onDelete with the correct skill ID", async () => {
    const handleDelete = vi.fn()
    render(<SkillsDisplay skills={SAMPLE_SKILLS} onDelete={handleDelete} />)

    await userEvent.click(screen.getByRole("button", { name: "Remove Python" }))
    expect(handleDelete).toHaveBeenCalledTimes(1)
    expect(handleDelete).toHaveBeenCalledWith(1)
  })

  it("does NOT render remove buttons when onDelete is not provided", () => {
    render(<SkillsDisplay skills={SAMPLE_SKILLS} />)

    expect(screen.queryByRole("button", { name: "Remove Python" })).toBeNull()
    expect(screen.queryByRole("button", { name: "Remove React" })).toBeNull()
  })
})

describe("SkillsDisplay — category delete", () => {
  it("each category has a Delete all button when onDeleteCategory is provided", () => {
    render(
      <SkillsDisplay
        skills={SAMPLE_SKILLS}
        onDelete={vi.fn()}
        onDeleteCategory={vi.fn()}
      />
    )

    expect(screen.getByRole("button", { name: "Delete all Language" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Delete all Framework" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Delete all DevOps" })).toBeInTheDocument()
  })

  it("clicking Delete all calls onDeleteCategory with category name", async () => {
    const handleDeleteCategory = vi.fn()
    render(
      <SkillsDisplay
        skills={SAMPLE_SKILLS}
        onDelete={vi.fn()}
        onDeleteCategory={handleDeleteCategory}
      />
    )

    await userEvent.click(screen.getByRole("button", { name: "Delete all Language" }))
    expect(handleDeleteCategory).toHaveBeenCalledTimes(1)
    expect(handleDeleteCategory).toHaveBeenCalledWith("Language")
  })

  it("does NOT render Delete all buttons when onDeleteCategory is not provided", () => {
    render(<SkillsDisplay skills={SAMPLE_SKILLS} onDelete={vi.fn()} />)

    expect(screen.queryByRole("button", { name: "Delete all Language" })).toBeNull()
  })
})

describe("SkillsDisplay — inline edit", () => {
  it("each skill badge has an Edit button when onEdit is provided", () => {
    render(
      <SkillsDisplay skills={SAMPLE_SKILLS} onDelete={vi.fn()} onEdit={vi.fn()} />
    )
    expect(screen.getByRole("button", { name: "Edit Python" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Edit React" })).toBeInTheDocument()
  })

  it("clicking Edit shows input with current skill name", async () => {
    render(
      <SkillsDisplay skills={SAMPLE_SKILLS} onDelete={vi.fn()} onEdit={vi.fn()} />
    )
    await userEvent.click(screen.getByRole("button", { name: "Edit Python" }))
    expect(screen.getByDisplayValue("Python")).toBeInTheDocument()
  })

  it("saving edited skill calls onEdit with skill ID and new data", async () => {
    const handleEdit = vi.fn()
    render(
      <SkillsDisplay skills={SAMPLE_SKILLS} onDelete={vi.fn()} onEdit={handleEdit} />
    )
    await userEvent.click(screen.getByRole("button", { name: "Edit Python" }))

    const nameInput = screen.getByDisplayValue("Python")
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, "Python 3")

    await userEvent.click(screen.getByRole("button", { name: /Save/i }))
    expect(handleEdit).toHaveBeenCalledWith(1, expect.objectContaining({ name: "Python 3" }))
  })

  it("does NOT show Edit buttons when onEdit is not provided", () => {
    render(<SkillsDisplay skills={SAMPLE_SKILLS} onDelete={vi.fn()} />)
    expect(screen.queryByRole("button", { name: "Edit Python" })).toBeNull()
  })
})

describe("SkillsDisplay — empty state", () => {
  it("shows 'No skills yet' when skills array is empty", () => {
    render(<SkillsDisplay skills={[]} />)
    expect(screen.getByText(/No skills yet/i)).toBeInTheDocument()
  })
})
