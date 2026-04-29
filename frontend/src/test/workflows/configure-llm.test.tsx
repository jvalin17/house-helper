/**
 * Workflow 16: Configure LLM provider — pick provider + model, save, see status.
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import Settings from "@/components/Settings"
import { api } from "@/api/client"

vi.mock("@/api/client")

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(api.getLLMProviders).mockResolvedValue({ providers: ["openai", "anthropic"] })
  vi.mocked(api.getLLMModels).mockResolvedValue({
    openai: [{
      id: "gpt-4o-mini", name: "GPT-4o mini", speed: "fast", quality: "good",
      input_per_1m: 0.15, output_per_1m: 0.60, est_per_resume: "$0.001",
    }],
    anthropic: [],
  })
  vi.mocked(api.getCalibrationWeights).mockResolvedValue({})
  vi.mocked(api.getSearchSources).mockResolvedValue([])
  vi.mocked(api.getBudget).mockResolvedValue({})
})

describe("Workflow: Configure LLM provider", () => {
  it("shows active provider badge when status.active is true", async () => {
    vi.mocked(api.getLLMConfig).mockResolvedValue({
      provider: "openai", model: "gpt-4o-mini",
    })
    vi.mocked(api.getLLMStatus).mockResolvedValue({
      active: true, provider: "openai", model: "gpt-4o-mini",
    })

    render(<Settings />)
    await waitFor(() => expect(api.getLLMConfig).toHaveBeenCalled())
    await screen.findByText(/openai — gpt-4o-mini/)
  })

  it("calling Save Provider forwards selected provider/model/api_key to saveLLM", async () => {
    vi.mocked(api.getLLMConfig).mockResolvedValue({})
    vi.mocked(api.getLLMStatus).mockResolvedValue({ active: false, provider: null, model: null })
    vi.mocked(api.saveLLM).mockResolvedValue({})

    render(<Settings />)
    await screen.findByText(/AI Provider/)

    await userEvent.click(screen.getByText("openai"))
    await userEvent.click(await screen.findByText(/GPT-4o mini/))
    const apiKey = screen.getByPlaceholderText(/Pre-loaded from .env/)
    await userEvent.type(apiKey, "sk-test-123")
    await userEvent.click(screen.getByRole("button", { name: /Save Provider/ }))

    await waitFor(() => expect(api.saveLLM).toHaveBeenCalled())
    const payload = vi.mocked(api.saveLLM).mock.calls[0][0]
    expect(payload.provider).toBe("openai")
    expect(payload.model).toBe("gpt-4o-mini")
    expect(payload.api_key).toBe("sk-test-123")
  })

  it("surfaces failure message when saveLLM throws", async () => {
    vi.mocked(api.getLLMConfig).mockResolvedValue({})
    vi.mocked(api.getLLMStatus).mockResolvedValue({ active: false, provider: null, model: null })
    vi.mocked(api.saveLLM).mockRejectedValue(new Error("BAD_KEY"))

    render(<Settings />)
    await screen.findByText(/AI Provider/)
    await userEvent.click(screen.getByText("openai"))
    await userEvent.click(await screen.findByText(/GPT-4o mini/))
    await userEvent.click(screen.getByRole("button", { name: /Save Provider/ }))

    await waitFor(() => expect(screen.getByText(/Failed to save/)).toBeInTheDocument())
  })
})
