/**
 * ErrorBoundary — catches render failures and offers recovery.
 *
 * Not tied to a single workflow but underpins every page; it should
 * render the fallback UI on throw and let the user reset or navigate home.
 */

import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import ErrorBoundary from "@/components/ErrorBoundary"

function Boom({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error("kaboom")
  }
  return <div>safe child</div>
}

let consoleSpy: ReturnType<typeof vi.spyOn>

beforeEach(() => {
  consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {})
})

afterEach(() => {
  consoleSpy.mockRestore()
})

describe("ErrorBoundary", () => {
  it("renders children when no error is thrown", () => {
    render(
      <ErrorBoundary>
        <Boom shouldThrow={false} />
      </ErrorBoundary>
    )
    expect(screen.getByText("safe child")).toBeInTheDocument()
  })

  it("renders fallback UI with the thrown error message", () => {
    render(
      <ErrorBoundary>
        <Boom shouldThrow={true} />
      </ErrorBoundary>
    )
    expect(screen.getByText(/Something went wrong/)).toBeInTheDocument()
    expect(screen.getByText("kaboom")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Try Again/ })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /Go Home/ })).toBeInTheDocument()
  })

  it("Try Again clears the error and attempts to re-render children", async () => {
    let throws = true
    function Wrapper() {
      return <Boom shouldThrow={throws} />
    }

    const { rerender } = render(
      <ErrorBoundary>
        <Wrapper />
      </ErrorBoundary>
    )
    expect(screen.getByText(/Something went wrong/)).toBeInTheDocument()

    throws = false
    await userEvent.click(screen.getByRole("button", { name: /Try Again/ }))
    rerender(
      <ErrorBoundary>
        <Wrapper />
      </ErrorBoundary>
    )
    expect(screen.getByText("safe child")).toBeInTheDocument()
  })

  it("Go Home navigates to the root via window.location.assign", async () => {
    const assign = vi.fn()
    Object.defineProperty(window, "location", {
      writable: true,
      value: { ...window.location, assign },
    })

    render(
      <ErrorBoundary>
        <Boom shouldThrow={true} />
      </ErrorBoundary>
    )
    await userEvent.click(screen.getByRole("button", { name: /Go Home/ }))
    expect(assign).toHaveBeenCalledWith("/")
  })

  it("falls back to a default message when error.message is empty", () => {
    function ThrowEmpty() {
      const e = new Error("")
      throw e
    }

    render(
      <ErrorBoundary>
        <ThrowEmpty />
      </ErrorBoundary>
    )
    expect(screen.getByText(/An unexpected error occurred/)).toBeInTheDocument()
  })
})
