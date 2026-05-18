/**
 * Tests for onboarding components: SetupGuidance (setup + exhausted states).
 */

import { render, screen } from "@testing-library/react"
import { describe, it, expect } from "vitest"
import { BrowserRouter } from "react-router-dom"
import SetupGuidance from "@/components/shared/SetupGuidance"
import type { SourceUsage } from "@/types"

describe("SetupGuidance — setup mode", () => {
  it("renders title and description", () => {
    render(
      <BrowserRouter>
        <SetupGuidance title="Ready to search" description="Connect a source to start." sources={[]} />
      </BrowserRouter>
    )
    expect(screen.getByText("Ready to search")).toBeInTheDocument()
    expect(screen.getByText("Connect a source to start.")).toBeInTheDocument()
  })

  it("renders source cards with free tier and unlock info", () => {
    render(
      <BrowserRouter>
        <SetupGuidance
          title="Setup"
          description="Connect sources."
          sources={[
            { displayName: "RealtyAPI", freeTier: "250 req/mo", unlocks: "Apartment search with photos", signupUrl: "https://www.realtyapi.io" },
            { displayName: "RentCast", freeTier: "50 req/mo", unlocks: "Market data", signupUrl: null },
          ]}
        />
      </BrowserRouter>
    )
    expect(screen.getByText("RealtyAPI")).toBeInTheDocument()
    expect(screen.getByText("250 req/mo")).toBeInTheDocument()
    expect(screen.getByText("Apartment search with photos")).toBeInTheDocument()
    expect(screen.getByText("RentCast")).toBeInTheDocument()
  })

  it("renders signup links for sources that have them", () => {
    render(
      <BrowserRouter>
        <SetupGuidance
          title="Setup"
          description="Connect."
          sources={[
            { displayName: "RealtyAPI", freeTier: "250 req/mo", unlocks: "Search", signupUrl: "https://www.realtyapi.io" },
            { displayName: "RentCast", freeTier: "50 req/mo", unlocks: "Data", signupUrl: null },
          ]}
        />
      </BrowserRouter>
    )
    const links = screen.getAllByText("Get free key")
    expect(links).toHaveLength(1)
    expect(links[0].closest("a")).toHaveAttribute("href", "https://www.realtyapi.io")
  })

  it("renders Go to Settings button", () => {
    render(
      <BrowserRouter>
        <SetupGuidance title="Setup" description="Connect." sources={[]} />
      </BrowserRouter>
    )
    expect(screen.getByText("Go to Settings")).toBeInTheDocument()
  })
})

describe("SetupGuidance — exhausted mode", () => {
  const exhaustedSources: SourceUsage[] = [
    {
      service_name: "realtyapi",
      display_name: "RealtyAPI",
      used: 250,
      limit: 250,
      period: "month",
      remaining: 0,
      exhausted: true,
      percent_used: 100,
      resets_at: "2026-06-01T00:00:00",
    },
  ]

  it("shows exhausted source with usage count", () => {
    render(
      <BrowserRouter>
        <SetupGuidance
          title="Source quota reached"
          description="Your sources hit their limit."
          sources={[]}
          exhaustedSources={exhaustedSources}
        />
      </BrowserRouter>
    )
    expect(screen.getByText("RealtyAPI")).toBeInTheDocument()
    expect(screen.getByText("250/250 used")).toBeInTheDocument()
  })

  it("shows reset date for monthly source", () => {
    render(
      <BrowserRouter>
        <SetupGuidance
          title="Source quota reached"
          description="Limit reached."
          sources={[]}
          exhaustedSources={exhaustedSources}
        />
      </BrowserRouter>
    )
    expect(screen.getByText(/Resets June 1/)).toBeInTheDocument()
  })

  it("shows alternative sources below exhausted ones", () => {
    render(
      <BrowserRouter>
        <SetupGuidance
          title="Quota reached"
          description="Try another."
          sources={[
            { displayName: "RentCast", freeTier: "50 req/mo", unlocks: "Market data", signupUrl: null },
          ]}
          exhaustedSources={exhaustedSources}
        />
      </BrowserRouter>
    )
    expect(screen.getByText("Try another source:")).toBeInTheDocument()
    expect(screen.getByText("RentCast")).toBeInTheDocument()
  })

  it("shows daily reset label for daily sources", () => {
    const dailyExhausted: SourceUsage[] = [{
      service_name: "walkscore",
      display_name: "Walk Score",
      used: 5000,
      limit: 5000,
      period: "day",
      remaining: 0,
      exhausted: true,
      percent_used: 100,
      resets_at: "2026-05-19T00:00:00",
    }]

    render(
      <BrowserRouter>
        <SetupGuidance
          title="Quota reached"
          description="Daily limit."
          sources={[]}
          exhaustedSources={dailyExhausted}
        />
      </BrowserRouter>
    )
    expect(screen.getByText("Resets tomorrow")).toBeInTheDocument()
  })
})
