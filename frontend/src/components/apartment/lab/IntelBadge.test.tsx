import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import IntelBadge from "./IntelBadge"

describe("IntelBadge", () => {
  it("returns null when no intel data", () => {
    const { container } = render(<IntelBadge intelData={null} />)
    expect(container.innerHTML).toBe("")
  })

  it("shows Walk score when available", () => {
    render(<IntelBadge intelData={{
      verified_scores: { result: { walk_score: 72 } },
    }} />)
    expect(screen.getByText(/Walk 72/)).toBeInTheDocument()
  })

  it("shows Google rating when available", () => {
    render(<IntelBadge intelData={{
      reviews: { result: { google_rating: 4.2 } },
    }} />)
    expect(screen.getByText(/⭐4.2/)).toBeInTheDocument()
  })

  it("shows combined metrics", () => {
    render(<IntelBadge intelData={{
      verified_scores: { result: { walk_score: 72 } },
      reviews: { result: { google_rating: 4.2 } },
    }} />)
    expect(screen.getByText(/Walk 72 • ⭐4.2/)).toBeInTheDocument()
  })

  it("falls back to Intel when no key metrics", () => {
    render(<IntelBadge intelData={{
      concessions: { result: { application_fee: 50 } },
    }} />)
    expect(screen.getByText(/Intel/)).toBeInTheDocument()
  })

  it("shows unit count", () => {
    render(<IntelBadge intelData={{
      unit_details: { result: { total_available: 25 } },
    }} />)
    expect(screen.getByText(/25 units/)).toBeInTheDocument()
  })
})
