/**
 * Check for Updates — tests the update checker UI in Settings.
 *
 * In test environment (jsdom, no Tauri), the updater shows a fallback message.
 */

import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect } from "vitest"
import UpdateChecker from "@/components/settings/UpdateChecker"

describe("UpdateChecker component", () => {
  it("renders the check for updates button", () => {
    render(<UpdateChecker />)
    expect(screen.getByRole("button", { name: /Check for Updates/i })).toBeInTheDocument()
  })

  it("shows current version", () => {
    render(<UpdateChecker />)
    expect(screen.getByText(/Current version/i)).toBeInTheDocument()
  })

  it("shows fallback message in non-Tauri environment after clicking check", async () => {
    render(<UpdateChecker />)
    await userEvent.click(screen.getByRole("button", { name: /Check for Updates/i }))
    await waitFor(() =>
      expect(screen.getByText(/Updates only available in the desktop app/i)).toBeInTheDocument()
    )
  })

  it("shows try again button after error", async () => {
    render(<UpdateChecker />)
    await userEvent.click(screen.getByRole("button", { name: /Check for Updates/i }))
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /Try again/i })).toBeInTheDocument()
    )
  })
})
