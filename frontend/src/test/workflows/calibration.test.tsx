/**
 * Workflow 20: Match calibration — Recalculate button calls the API and renders new weights.
 *
 * Backend already covers /api/calibration/judge, so the frontend slice covers
 * only the recalculate-and-render UI loop on the Settings page.
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
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
  vi.mocked(api.getSearchSources).mockResolvedValue([])
  vi.mocked(api.getBudget).mockResolvedValue({})
})

describe("Workflow: Match calibration", () => {
  it("renders default weights and updates after Recalculate", async () => {
    vi.mocked(api.getCalibrationWeights).mockResolvedValue({
      skills_overlap: 0.3, semantic_sim: 0.3, tfidf: 0.2, experience_years: 0.2,
    })
    vi.mocked(api.recalibrate).mockResolvedValue({
      skills_overlap: 0.5, semantic_sim: 0.2, tfidf: 0.2, experience_years: 0.1,
    })

    render(<Settings />)
    await screen.findByText(/Match Calibration/)
    expect(screen.getAllByText("30%").length).toBeGreaterThanOrEqual(1)

    await userEvent.click(screen.getByRole("button", { name: /Recalculate/ }))
    await waitFor(() => expect(api.recalibrate).toHaveBeenCalled())
    await screen.findByText("50%")
    await screen.findByText(/Weights recalculated/)
  })

  it("shows a friendly message when there are no judgements yet", async () => {
    vi.mocked(api.getCalibrationWeights).mockResolvedValue({
      skills_overlap: 0.3, semantic_sim: 0.3, tfidf: 0.2, experience_years: 0.2,
    })
    vi.mocked(api.recalibrate).mockRejectedValue(new Error("no data"))

    render(<Settings />)
    await screen.findByText(/Match Calibration/)
    await userEvent.click(screen.getByRole("button", { name: /Recalculate/ }))
    await screen.findByText(/No judgements yet/)
  })
})
