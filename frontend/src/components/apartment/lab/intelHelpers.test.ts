import { describe, it, expect } from "vitest"
import {
  hasUsefulConcessionData,
  hasUsefulReviewData,
  hasUsefulPolicyData,
  hasUsefulNearbyData,
} from "./intelHelpers"

describe("hasUsefulConcessionData", () => {
  it("returns true when concessions list has entries", () => {
    expect(hasUsefulConcessionData({
      concessions: [{ description: "2 months free" }],
    })).toBe(true)
  })

  it("returns true when fee fields are present", () => {
    expect(hasUsefulConcessionData({ application_fee: 50, parking_monthly: 150 })).toBe(true)
  })

  it("returns false when no concessions and no fees", () => {
    expect(hasUsefulConcessionData({ concessions: [], application_fee: null })).toBe(false)
  })

  it("returns false for completely empty data", () => {
    expect(hasUsefulConcessionData({})).toBe(false)
  })
})

describe("hasUsefulReviewData", () => {
  it("returns true when google rating exists", () => {
    expect(hasUsefulReviewData({ google_rating: 4.2, total_ratings: 156 })).toBe(true)
  })

  it("returns true when reviews array has entries", () => {
    expect(hasUsefulReviewData({
      reviews: [{ author_name: "Sarah", text: "Great place!" }],
    })).toBe(true)
  })

  it("returns true when sentiment analysis exists", () => {
    expect(hasUsefulReviewData({
      sentiment: { themes: [{ topic: "Maintenance" }] },
    })).toBe(true)
  })

  it("returns false when place_not_found is true", () => {
    expect(hasUsefulReviewData({ place_not_found: true, google_rating: 4.0 })).toBe(false)
  })

  it("returns false when no_reviews is true", () => {
    expect(hasUsefulReviewData({ no_reviews: true })).toBe(false)
  })

  it("returns false for empty data", () => {
    expect(hasUsefulReviewData({})).toBe(false)
  })
})

describe("hasUsefulPolicyData", () => {
  it("returns true when pet policy has data", () => {
    expect(hasUsefulPolicyData({
      pet_policy: { allowed: true, weight_limit_lbs: 75 },
    })).toBe(true)
  })

  it("returns true when lease terms exist", () => {
    expect(hasUsefulPolicyData({
      lease_terms: { minimum_months: 12 },
    })).toBe(true)
  })

  it("returns false when all policy fields are null", () => {
    expect(hasUsefulPolicyData({
      pet_policy: { allowed: null, weight_limit_lbs: null },
      lease_terms: { minimum_months: null },
    })).toBe(false)
  })

  it("returns false for empty data", () => {
    expect(hasUsefulPolicyData({})).toBe(false)
  })
})

describe("hasUsefulNearbyData", () => {
  it("returns true when places were found", () => {
    expect(hasUsefulNearbyData({ total_places: 45 })).toBe(true)
  })

  it("returns false when zero places", () => {
    expect(hasUsefulNearbyData({ total_places: 0 })).toBe(false)
  })

  it("returns false for empty data", () => {
    expect(hasUsefulNearbyData({})).toBe(false)
  })
})
