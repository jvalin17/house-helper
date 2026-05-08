/**
 * Smart Intel badge — shows key metrics instead of just "Intel".
 *
 * Examples:
 *   Walk 72 • ⭐4.2           (scores + reviews available)
 *   ⭐4.2 • 25 units          (reviews + unit details)
 *   Walk 72                    (only walk score)
 *   Intel                      (data exists but no key metrics)
 */

interface Props {
  intelData?: Record<string, { result: Record<string, unknown> }> | null
  compact?: boolean
}

export default function IntelBadge({ intelData, compact = false }: Props) {
  if (!intelData || Object.keys(intelData).length === 0) return null

  const metrics: string[] = []

  // Walk score
  const walkScore = intelData.verified_scores?.result?.walk_score as number | null
  if (walkScore != null) {
    metrics.push(`Walk ${walkScore}`)
  }

  // Google rating
  const googleRating = intelData.reviews?.result?.google_rating as number | null
  if (googleRating != null) {
    metrics.push(`⭐${googleRating}`)
  }

  // Units available
  const totalAvailable = intelData.unit_details?.result?.total_available as number | null
  if (totalAvailable != null && totalAvailable > 0) {
    metrics.push(`${totalAvailable} units`)
  }

  // Nearby places count
  const nearbyCount = intelData.nearby_places?.result?.total_places as number | null
  if (nearbyCount != null && nearbyCount > 0 && metrics.length < 2) {
    metrics.push(`${nearbyCount} nearby`)
  }

  // Livability score
  const livability = intelData.floor_plan_analysis?.result?.livability_score as number | null
  if (livability != null && metrics.length < 2) {
    metrics.push(`Livability ${livability}`)
  }

  const displayText = metrics.length > 0
    ? (compact ? metrics.slice(0, 2).join(" • ") : metrics.slice(0, 3).join(" • "))
    : "Intel"

  return (
    <span className="text-[9px] px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-600 font-semibold flex-shrink-0 whitespace-nowrap">
      🔍 {displayText}
    </span>
  )
}
