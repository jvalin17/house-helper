/**
 * Intel section visibility helpers — determine if a section has useful data.
 * Extracted from IntelSection.tsx for testability.
 */

export function hasUsefulConcessionData(data: Record<string, unknown>): boolean {
  const concessionsList = data.concessions as unknown[] | undefined
  const hasConcessions = concessionsList && concessionsList.length > 0
  const hasFees = ["application_fee", "admin_fee", "pet_deposit", "pet_monthly", "parking_monthly"]
    .some(feeKey => data[feeKey] != null)
  return Boolean(hasConcessions || hasFees)
}

export function hasUsefulReviewData(data: Record<string, unknown>): boolean {
  if (data.place_not_found || data.no_reviews) return false
  const reviews = data.reviews as unknown[] | undefined
  const sentiment = data.sentiment as Record<string, unknown> | undefined
  const googleRating = data.google_rating as number | null
  return Boolean((reviews && reviews.length > 0) || sentiment || googleRating != null)
}

export function hasUsefulPolicyData(data: Record<string, unknown>): boolean {
  const policyFields = ["pet_policy", "lease_terms", "subletting", "guest_policy", "parking", "utilities", "move_in_requirements"]
  return policyFields.some(field => {
    const section = data[field] as Record<string, unknown> | undefined
    return section && Object.values(section).some(value => value != null)
  })
}

export function hasUsefulNearbyData(data: Record<string, unknown>): boolean {
  const totalPlaces = data.total_places as number | undefined
  return Boolean(totalPlaces && totalPlaces > 0)
}
