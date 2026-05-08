import { render, screen, fireEvent } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import HuntFunnel from "../HuntFunnel"

const SAMPLE_STAGES = {
  interested: { count: 5 },
  visited: { count: 3 },
  applied: { count: 2 },
  approved: { count: 1 },
  moved_in: { count: 0 },
}

describe("HuntFunnel", () => {
  it("renders all 5 stage bands", () => {
    render(
      <HuntFunnel
        stages={SAMPLE_STAGES}
        selectedStage="interested"
        onSelectStage={() => {}}
      />,
    )
    expect(screen.getByText("Interested (5)")).toBeInTheDocument()
    expect(screen.getByText("Visited (3)")).toBeInTheDocument()
    expect(screen.getByText("Applied (2)")).toBeInTheDocument()
    expect(screen.getByText("Approved (1)")).toBeInTheDocument()
    expect(screen.getByText("Moved In (0)")).toBeInTheDocument()
  })

  it("shows correct counts in labels", () => {
    const customStages = {
      interested: { count: 10 },
      visited: { count: 7 },
      applied: { count: 4 },
      approved: { count: 2 },
      moved_in: { count: 1 },
    }
    render(
      <HuntFunnel
        stages={customStages}
        selectedStage="interested"
        onSelectStage={() => {}}
      />,
    )
    expect(screen.getByText("Interested (10)")).toBeInTheDocument()
    expect(screen.getByText("Visited (7)")).toBeInTheDocument()
    expect(screen.getByText("Applied (4)")).toBeInTheDocument()
    expect(screen.getByText("Approved (2)")).toBeInTheDocument()
    expect(screen.getByText("Moved In (1)")).toBeInTheDocument()
  })

  it("calls onSelectStage when a band is clicked", () => {
    const handleSelectStage = vi.fn()
    render(
      <HuntFunnel
        stages={SAMPLE_STAGES}
        selectedStage="interested"
        onSelectStage={handleSelectStage}
      />,
    )
    fireEvent.click(screen.getByText("Visited (3)"))
    expect(handleSelectStage).toHaveBeenCalledWith("visited")
  })

  it("selected band has aria-pressed true", () => {
    render(
      <HuntFunnel
        stages={SAMPLE_STAGES}
        selectedStage="applied"
        onSelectStage={() => {}}
      />,
    )
    const appliedButton = screen.getByLabelText("Applied: 2 listings")
    expect(appliedButton).toHaveAttribute("aria-pressed", "true")

    const interestedButton = screen.getByLabelText("Interested: 5 listings")
    expect(interestedButton).toHaveAttribute("aria-pressed", "false")
  })

  it("renders heading text", () => {
    render(
      <HuntFunnel
        stages={SAMPLE_STAGES}
        selectedStage="interested"
        onSelectStage={() => {}}
      />,
    )
    expect(screen.getByText("Hunt Progress")).toBeInTheDocument()
  })

  it("handles all-zero counts without errors", () => {
    const emptyStages = {
      interested: { count: 0 },
      visited: { count: 0 },
      applied: { count: 0 },
      approved: { count: 0 },
      moved_in: { count: 0 },
    }
    render(
      <HuntFunnel
        stages={emptyStages}
        selectedStage="interested"
        onSelectStage={() => {}}
      />,
    )
    expect(screen.getByText("Interested (0)")).toBeInTheDocument()
    expect(screen.getByText("Moved In (0)")).toBeInTheDocument()
  })
})
