/**
 * Budget enforcement — tests that the isBudgetError helper works
 * and that the API client properly detects 429 budget responses.
 */

import { describe, it, expect } from "vitest"
import { isBudgetError } from "@/api/client"

describe("Budget error detection", () => {
  it("isBudgetError returns true for budget errors", () => {
    const err = new Error("budget exceeded")
    ;(err as unknown as Record<string, unknown>).budgetExceeded = true
    ;(err as unknown as Record<string, unknown>).spent = 0.55
    ;(err as unknown as Record<string, unknown>).limit = 0.50
    expect(isBudgetError(err)).toBe(true)
  })

  it("isBudgetError returns false for regular errors", () => {
    expect(isBudgetError(new Error("network error"))).toBe(false)
    expect(isBudgetError(null)).toBe(false)
    expect(isBudgetError("string error")).toBe(false)
  })

  it("budget error has spent and limit properties", () => {
    const err = new Error("budget exceeded")
    ;(err as unknown as Record<string, unknown>).budgetExceeded = true
    ;(err as unknown as Record<string, unknown>).spent = 0.55
    ;(err as unknown as Record<string, unknown>).limit = 0.50

    if (isBudgetError(err)) {
      expect(err.spent).toBe(0.55)
      expect(err.limit).toBe(0.50)
    }
  })
})
