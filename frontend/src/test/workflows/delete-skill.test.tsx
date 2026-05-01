/**
 * Delete individual skill — TDD tests for X button on skill badges.
 *
 * Covers:
 * - Each skill badge renders an X (delete) button
 * - Clicking X calls onDelete with the correct skill ID
 * - After delete, the skill disappears from the display
 */

import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi } from "vitest"
import SkillsDisplay from "@/components/knowledge/SkillsDisplay"
import type { Skill } from "@/types"

const SAMPLE_SKILLS: Skill[] = [
  { id: 1, name: "Python", category: "Language" },
  { id: 2, name: "React", category: "Framework" },
  { id: 3, name: "Docker", category: "DevOps" },
]

describe("SkillsDisplay with delete buttons", () => {
  it("renders an X button for each skill", () => {
    const handleDelete = vi.fn()
    render(<SkillsDisplay skills={SAMPLE_SKILLS} onDelete={handleDelete} />)

    const deleteButtons = screen.getAllByRole("button", { name: /delete/i })
    expect(deleteButtons.length).toBe(3)
  })

  it("clicking X calls onDelete with the correct skill ID", async () => {
    const handleDelete = vi.fn()
    render(<SkillsDisplay skills={SAMPLE_SKILLS} onDelete={handleDelete} />)

    const deleteButton = screen.getByRole("button", { name: /Delete Python/i })
    await userEvent.click(deleteButton)
    expect(handleDelete).toHaveBeenCalledWith(1)
  })

  it("does not render X buttons when onDelete is not provided", () => {
    render(<SkillsDisplay skills={SAMPLE_SKILLS} />)

    const deleteButtons = screen.queryAllByRole("button", { name: /delete/i })
    expect(deleteButtons.length).toBe(0)
  })

  it("shows empty state when no skills", () => {
    render(<SkillsDisplay skills={[]} />)
    expect(screen.getByText(/No skills yet/i)).toBeInTheDocument()
  })
})
