/**
 * EducationList — knowledge bank section for degrees.
 *
 * Exercises the empty state, rendering of degree/field/institution/year,
 * and the delete callback.
 */

import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi } from "vitest"
import EducationList from "@/components/knowledge/EducationList"
import type { Education } from "@/types"

const edu = (over: Partial<Education> = {}): Education => ({
  id: 1, institution: "State University", degree: "BS",
  field: "Computer Science", end_date: "2018", ...over,
})

describe("EducationList", () => {
  it("renders the empty state when no entries exist", () => {
    render(<EducationList education={[]} onDelete={vi.fn()} />)
    expect(screen.getByText(/Education \(0\)/)).toBeInTheDocument()
    expect(screen.getByText(/No education entries/)).toBeInTheDocument()
  })

  it("renders degree, field, institution, and year", () => {
    render(<EducationList education={[edu()]} onDelete={vi.fn()} />)
    expect(screen.getByText(/BS in Computer Science/)).toBeInTheDocument()
    expect(screen.getByText(/State University \(2018\)/)).toBeInTheDocument()
  })

  it("omits ' in <field>' when field is empty", () => {
    render(
      <EducationList
        education={[edu({ id: 2, degree: "PhD", field: "", end_date: "" })]}
        onDelete={vi.fn()}
      />
    )
    expect(screen.getByText("PhD")).toBeInTheDocument()
    expect(screen.queryByText(/PhD in/)).not.toBeInTheDocument()
    expect(screen.getByText("State University")).toBeInTheDocument()
  })

  it("calls onDelete with the entry id when Delete is clicked", async () => {
    const onDelete = vi.fn()
    render(
      <EducationList education={[edu({ id: 42 }), edu({ id: 99, degree: "MS" })]} onDelete={onDelete} />
    )
    const buttons = screen.getAllByRole("button", { name: /Delete/ })
    await userEvent.click(buttons[1])
    expect(onDelete).toHaveBeenCalledWith(99)
  })
})
