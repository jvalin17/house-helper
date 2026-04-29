/**
 * Workflow 17: View AI usage — Settings page reads /budget and renders cost.
 */

import { render, screen, waitFor } from "@testing-library/react"
import { describe, it, expect, vi, beforeEach } from "vitest"
import Settings from "@/components/Settings"
import { api } from "@/api/client"

vi.mock("@/api/client")

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.getLLMConfig).mockResolvedValue({})
  vi.mocked(api.getLLMProviders).mockResolvedValue({ providers: [] })
  vi.mocked(api.getLLMModels).mockResolvedValue({})
  vi.mocked(api.getLLMStatus).mockResolvedValue({ active: false, provider: null, model: null })
  vi.mocked(api.getCalibrationWeights).mockResolvedValue({})
  vi.mocked(api.getSearchSources).mockResolvedValue([])
})

describe("Workflow: View AI usage", () => {
  it("renders today + alltime cost from /budget", async () => {
    vi.mocked(api.getBudget).mockResolvedValue({
      usage: {
        total_cost: 0.0123,
        total_tokens: 4200,
        breakdown: {
          resume_gen: { tokens: 3000, cost: 0.009 },
          resume_analyze: { tokens: 1200, cost: 0.0033 },
        },
      },
      alltime: { total_cost: 5.4321, total_tokens: 1234567 },
    })

    render(<Settings />)
    await waitFor(() => expect(api.getBudget).toHaveBeenCalled())

    await screen.findByText("$0.0123")
    expect(screen.getByText("$5.4321")).toBeInTheDocument()
    expect(screen.getByText(/resume gen/)).toBeInTheDocument()
    expect(screen.getByText(/3000 tokens/)).toBeInTheDocument()
  })

  it("renders zero cost gracefully when budget is empty", async () => {
    vi.mocked(api.getBudget).mockResolvedValue({})

    render(<Settings />)
    await screen.findByText(/AI Usage/)
    expect(screen.getAllByText("$0.0000").length).toBeGreaterThanOrEqual(2)
  })
})
