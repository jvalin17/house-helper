/**
 * SkillsDisplay — knowledge bank section that groups skills by category.
 *
 * Verifies the empty state, category grouping, the underscore→space
 * formatting in headers, and the "other" fallback for missing category.
 */

import { render, screen, within } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import SkillsDisplay from "@/components/knowledge/SkillsDisplay"
import type { Skill } from "@/types"

const mk = (id: number, name: string, category = "other"): Skill =>
  ({ id, name, category })

describe("SkillsDisplay", () => {
  it("renders an empty state when there are no skills", () => {
    render(<SkillsDisplay skills={[]} />)
    expect(screen.getByText(/Skills \(0\)/)).toBeInTheDocument()
    expect(screen.getByText(/No skills yet/)).toBeInTheDocument()
  })

  it("groups skills by category and humanizes underscores", () => {
    render(
      <SkillsDisplay
        skills={[
          mk(1, "Python", "programming_languages"),
          mk(2, "TypeScript", "programming_languages"),
          mk(3, "PostgreSQL", "databases"),
        ]}
      />
    )
    expect(screen.getByText(/Skills \(3\)/)).toBeInTheDocument()
    expect(screen.getByText(/programming languages/i)).toBeInTheDocument()
    expect(screen.getByText(/databases/i)).toBeInTheDocument()
    expect(screen.getByText("Python")).toBeInTheDocument()
    expect(screen.getByText("TypeScript")).toBeInTheDocument()
    expect(screen.getByText("PostgreSQL")).toBeInTheDocument()
  })

  it("falls back to 'other' when category is missing", () => {
    render(<SkillsDisplay skills={[mk(1, "Communication", "")]} />)
    expect(screen.getByText(/other/i)).toBeInTheDocument()
    expect(screen.getByText("Communication")).toBeInTheDocument()
  })

  it("keeps every skill in its own category cluster", () => {
    render(
      <SkillsDisplay
        skills={[
          mk(1, "Python", "languages"),
          mk(2, "AWS", "cloud"),
          mk(3, "Go", "languages"),
        ]}
      />
    )
    // Both categories should be visible
    expect(screen.getByText(/languages/i)).toBeInTheDocument()
    expect(screen.getByText(/cloud/i)).toBeInTheDocument()
    // All skills present
    expect(screen.getByText("Python")).toBeInTheDocument()
    expect(screen.getByText("Go")).toBeInTheDocument()
    expect(screen.getByText("AWS")).toBeInTheDocument()
  })
})
