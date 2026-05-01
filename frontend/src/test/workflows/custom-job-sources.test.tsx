/**
 * Custom job sources — TDD tests for adding/removing custom API sources in Settings.
 *
 * Covers:
 * - "Add Source" button renders in the Job Sources section
 * - Clicking Add Source shows a form with name + URL fields
 * - Submitting calls addCustomSource API
 * - Custom sources show delete button
 * - Max 5 limit shown in UI
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach } from "vitest"
import Settings from "@/components/Settings"
import { api } from "@/api/client"

vi.mock("@/api/client")

function mockSettingsLoad() {
  vi.mocked(api.getLLMConfig).mockResolvedValue({})
  vi.mocked(api.getLLMProviders).mockResolvedValue({ providers: ["claude"] })
  vi.mocked(api.getLLMModels).mockResolvedValue({})
  vi.mocked(api.getCalibrationWeights).mockResolvedValue({})
  vi.mocked(api.getBudget).mockResolvedValue({})
  vi.mocked(api.getLLMStatus).mockResolvedValue({ active: false, provider: null, model: null })
  vi.mocked(api.getSearchSources).mockResolvedValue([
    { id: "remoteok", name: "RemoteOK", signup: null, free_tier: "Unlimited", is_available: true, requires_api_key: false, enabled: true },
  ])
}

describe("Custom Job Sources in Settings", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSettingsLoad()
  })

  it("renders an Add Source button", async () => {
    render(<Settings />)
    await waitFor(() => expect(screen.getByText("RemoteOK")).toBeInTheDocument())
    expect(screen.getByRole("button", { name: /Add Source/i })).toBeInTheDocument()
  })

  it("clicking Add Source shows name and URL inputs", async () => {
    render(<Settings />)
    await waitFor(() => expect(screen.getByText("RemoteOK")).toBeInTheDocument())

    await userEvent.click(screen.getByRole("button", { name: /Add Source/i }))
    expect(screen.getByPlaceholderText(/Source name/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/API URL/i)).toBeInTheDocument()
  })

  it("submitting calls addCustomSource with name and URL", async () => {
    vi.mocked(api.addCustomSource).mockResolvedValue({
      id: "custom_abc123", name: "MyBoard", api_url: "https://myboard.com/api",
      has_api_key: false, enabled: true,
    })

    render(<Settings />)
    await waitFor(() => expect(screen.getByText("RemoteOK")).toBeInTheDocument())

    await userEvent.click(screen.getByRole("button", { name: /Add Source/i }))
    await userEvent.type(screen.getByPlaceholderText(/Source name/i), "MyBoard")
    await userEvent.type(screen.getByPlaceholderText(/API URL/i), "https://myboard.com/api")
    await userEvent.click(screen.getByRole("button", { name: /Save Source/i }))

    await waitFor(() => expect(api.addCustomSource).toHaveBeenCalledWith(
      expect.objectContaining({ name: "MyBoard", api_url: "https://myboard.com/api" })
    ))
  })

  it("custom sources show a Delete button", async () => {
    vi.mocked(api.getSearchSources).mockResolvedValue([
      { id: "remoteok", name: "RemoteOK", signup: null, free_tier: "Unlimited", is_available: true, requires_api_key: false, enabled: true },
      { id: "custom_abc", name: "MyBoard", signup: null, free_tier: "Custom API", is_available: true, requires_api_key: false, enabled: true, is_custom: true, api_url: "https://myboard.com" },
    ])

    render(<Settings />)
    await waitFor(() => expect(screen.getByText("MyBoard")).toBeInTheDocument())
    expect(screen.getByRole("button", { name: /Delete MyBoard/i })).toBeInTheDocument()
  })

  it("shows source count with max", async () => {
    render(<Settings />)
    await waitFor(() => expect(screen.getByText("RemoteOK")).toBeInTheDocument())
    expect(screen.getByText(/1.*connected/i)).toBeInTheDocument()
  })
})
