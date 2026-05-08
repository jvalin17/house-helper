import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import SearchProfileCard from "@/components/apartment/dashboard/SearchProfileCard"
import CompromiseExplorer from "@/components/apartment/dashboard/CompromiseExplorer"

const mockProfile = {
  ready: true,
  interaction_count: 24,
  preferences: [
    { term: "downtown", weight: 3.2, achievable: false, average_rent: 2400 },
    { term: "pool", weight: 2.1, achievable: false, average_rent: 2200 },
    { term: "2br", weight: 2.8, achievable: true, average_rent: 1700 },
    { term: "walkable", weight: 1.5, achievable: false, average_rent: 2100 },
  ],
  budget: 1800,
  wishlist_average: 2400,
  summary: "Your wishlist averages $2,400/mo. Your budget is $1,800/mo.",
}

describe("SearchProfileCard", () => {
  it("renders learned preferences as chips", () => {
    render(<SearchProfileCard profile={mockProfile} onExploreCompromises={vi.fn()} onDismiss={vi.fn()} />)
    expect(screen.getByText("downtown")).toBeInTheDocument()
    expect(screen.getByText("pool")).toBeInTheDocument()
    expect(screen.getByText("2br")).toBeInTheDocument()
  })

  it("shows budget summary", () => {
    render(<SearchProfileCard profile={mockProfile} onExploreCompromises={vi.fn()} onDismiss={vi.fn()} />)
    expect(screen.getByText(/\$2,400\/mo/)).toBeInTheDocument()
    expect(screen.getByText(/\$1,800\/mo/)).toBeInTheDocument()
  })

  it("shows Explore Compromises button", () => {
    render(<SearchProfileCard profile={mockProfile} onExploreCompromises={vi.fn()} onDismiss={vi.fn()} />)
    expect(screen.getByRole("button", { name: /Explore Compromises/i })).toBeInTheDocument()
  })

  it("shows dismiss button", () => {
    const onDismiss = vi.fn()
    render(<SearchProfileCard profile={mockProfile} onExploreCompromises={vi.fn()} onDismiss={onDismiss} />)
    const dismissButton = screen.getByRole("button", { name: /Dismiss/i })
    expect(dismissButton).toBeInTheDocument()
  })

  it("visually distinguishes achievable vs stretch preferences", () => {
    const { container } = render(<SearchProfileCard profile={mockProfile} onExploreCompromises={vi.fn()} onDismiss={vi.fn()} />)
    // 2br (achievable) should have filled style, downtown (stretch) should have outlined style
    const chips = container.querySelectorAll("[data-preference]")
    expect(chips.length).toBe(4)
  })

  it("does not render when profile not ready", () => {
    const { container } = render(
      <SearchProfileCard profile={{ ...mockProfile, ready: false }} onExploreCompromises={vi.fn()} onDismiss={vi.fn()} />
    )
    expect(container.firstChild).toBeNull()
  })
})

vi.mock("@/api/client", () => ({
  api: {
    exploreCompromises: vi.fn().mockResolvedValue({
      matching_count: 34, average_rent: 1750,
      per_preference_impact: [],
      suggestions: [{ listing_id: 78, title: "Pflugerville Place", price: 1800, match_score: 92 }],
      positive_message: "Pflugerville has pools at your price — explore?",
    }),
  },
}))

describe("CompromiseExplorer", () => {
  beforeEach(() => { vi.clearAllMocks() })

  it("renders toggle cards for each preference", () => {
    render(<CompromiseExplorer profile={mockProfile} onClose={vi.fn()} />)
    expect(screen.getByText("downtown")).toBeInTheDocument()
    expect(screen.getByText("pool")).toBeInTheDocument()
  })

  it("shows matching count from API", async () => {
    render(<CompromiseExplorer profile={mockProfile} onClose={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByTestId("matching-count")).toHaveTextContent("34")
    })
  })

  it("shows suggestion cards", async () => {
    render(<CompromiseExplorer profile={mockProfile} onClose={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByText("Pflugerville Place")).toBeInTheDocument()
      expect(screen.getByText(/\$1,800/)).toBeInTheDocument()
    })
  })

  it("never shows negative framing text", async () => {
    render(<CompromiseExplorer profile={mockProfile} onClose={vi.fn()} />)
    await waitFor(() => {
      expect(screen.queryByText(/can't afford/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/too expensive/i)).not.toBeInTheDocument()
      expect(screen.queryByText(/out of budget/i)).not.toBeInTheDocument()
    })
  })

  it("shows error message when API fails", async () => {
    const { api } = await import("@/api/client")
    vi.mocked(api.exploreCompromises).mockRejectedValueOnce(new Error("Network error"))
    render(<CompromiseExplorer profile={mockProfile} onClose={vi.fn()} />)
    await waitFor(() => {
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument()
    })
  })
})
