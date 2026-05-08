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
import { BrowserRouter } from "react-router-dom"
import GlobalSettings from "@/pages/GlobalSettings"
import { api } from "@/api/client"

vi.mock("@/api/client")

function mockSettingsLoad() {
  vi.mocked(api.getAllCredentials).mockResolvedValue([
    { service_name: "remoteok", category: "shared_source", display_name: "RemoteOK", signup_url: null, description: null, is_configured: 1, is_enabled: 1 },
  ])
  vi.mocked(api.getBudget).mockResolvedValue({})
}

describe("Custom Job Sources in Settings", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSettingsLoad()
  })

  it("renders an Add Source button", async () => {
    render(<BrowserRouter><GlobalSettings /></BrowserRouter>)
    await waitFor(() => expect(screen.getByText("RemoteOK")).toBeInTheDocument())
    expect(screen.getAllByRole("button", { name: /\+ Add Source/i }).length).toBeGreaterThanOrEqual(1)
  })

  it("clicking Add Source shows name and display name inputs", async () => {
    render(<BrowserRouter><GlobalSettings /></BrowserRouter>)
    await waitFor(() => expect(screen.getByText("RemoteOK")).toBeInTheDocument())

    await userEvent.click(screen.getAllByRole("button", { name: /\+ Add Source/i })[0])
    expect(screen.getByPlaceholderText(/Service ID/i)).toBeInTheDocument()
    expect(screen.getByPlaceholderText(/Display name/i)).toBeInTheDocument()
  })

  it("submitting calls saveCredential with service ID and key", async () => {
    vi.mocked(api.saveCredential).mockResolvedValue({ service: "test_source", is_configured: true })

    render(<BrowserRouter><GlobalSettings /></BrowserRouter>)
    await waitFor(() => expect(screen.getByText("RemoteOK")).toBeInTheDocument())

    await userEvent.click(screen.getAllByRole("button", { name: /\+ Add Source/i })[0])
    await userEvent.type(screen.getByPlaceholderText(/Service ID/i), "myboard")
    await userEvent.type(screen.getByPlaceholderText(/Display name/i), "MyBoard")
    await userEvent.type(screen.getByPlaceholderText(/API key/i), "sk-test")
    await userEvent.click(screen.getByRole("button", { name: /^Add Source$/i }))

    await waitFor(() => expect(api.saveCredential).toHaveBeenCalledWith("myboard", "sk-test", "shared_source", "MyBoard"))
  })

  it("configured sources show a Remove link", async () => {
    vi.mocked(api.getAllCredentials).mockResolvedValue([
      { service_name: "remoteok", category: "shared_source", display_name: "RemoteOK", signup_url: null, description: null, is_configured: 1, is_enabled: 1 },
      { service_name: "custom_abc", category: "shared_source", display_name: "MyBoard", signup_url: null, description: null, is_configured: 1, is_enabled: 1 },
    ])

    render(<BrowserRouter><GlobalSettings /></BrowserRouter>)
    await waitFor(() => expect(screen.getByText("MyBoard")).toBeInTheDocument())
    expect(screen.getAllByText("Remove").length).toBeGreaterThanOrEqual(1)
  })

  it("shows Connected badge for configured sources", async () => {
    render(<BrowserRouter><GlobalSettings /></BrowserRouter>)
    await waitFor(() => expect(screen.getByText("RemoteOK")).toBeInTheDocument())
    expect(screen.getByText("Connected")).toBeInTheDocument()
  })
})
