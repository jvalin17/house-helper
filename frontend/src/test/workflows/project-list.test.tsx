/**
 * ProjectList — knowledge bank section for projects.
 *
 * Covers empty state, basic rendering, the URL guard (only http/https
 * links should render), and the delete callback.
 */

import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi } from "vitest"
import ProjectList from "@/components/knowledge/ProjectList"
import type { Project } from "@/types"

const proj = (over: Partial<Project> = {}): Project => ({
  id: 1, name: "Sample", description: "A sample project",
  tech_stack: "React", url: "https://example.com", ...over,
})

describe("ProjectList", () => {
  it("renders the empty state when no projects exist", () => {
    render(<ProjectList projects={[]} onDelete={vi.fn()} />)
    expect(screen.getByText(/Projects \(0\)/)).toBeInTheDocument()
    expect(screen.getByText(/No projects/)).toBeInTheDocument()
  })

  it("renders name, description, and a safe URL", () => {
    render(<ProjectList projects={[proj()]} onDelete={vi.fn()} />)
    expect(screen.getByText("Sample")).toBeInTheDocument()
    expect(screen.getByText("A sample project")).toBeInTheDocument()
    const link = screen.getByRole("link", { name: /example\.com/ })
    expect(link).toHaveAttribute("href", "https://example.com")
    expect(link).toHaveAttribute("target", "_blank")
  })

  it("does not render unsafe (non-http) URLs", () => {
    render(
      <ProjectList
        projects={[proj({ id: 7, url: "javascript:alert('x')" })]}
        onDelete={vi.fn()}
      />
    )
    expect(screen.queryByRole("link")).not.toBeInTheDocument()
  })

  it("hides description and URL when not provided", () => {
    render(
      <ProjectList
        projects={[proj({ id: 8, name: "Bare", description: "", url: "" })]}
        onDelete={vi.fn()}
      />
    )
    expect(screen.getByText("Bare")).toBeInTheDocument()
    expect(screen.queryByRole("link")).not.toBeInTheDocument()
  })

  it("calls onDelete with the project id", async () => {
    const onDelete = vi.fn()
    render(<ProjectList projects={[proj({ id: 13 })]} onDelete={onDelete} />)
    await userEvent.click(screen.getByRole("button", { name: /Delete/ }))
    expect(onDelete).toHaveBeenCalledWith(13)
  })
})
