import { useState } from "react"
import { hasUsefulConcessionData, hasUsefulReviewData, hasUsefulPolicyData, hasUsefulNearbyData } from "./intelHelpers"

/** Shared score-to-color style for consistent threshold coloring across intel cards. */
function getScoreStyle(
  score: number,
  { highThreshold = 70, lowThreshold = 40, intenseBackground = false }:
    { highThreshold?: number; lowThreshold?: number; intenseBackground?: boolean } = {}
): string {
  if (score >= highThreshold) {
    return intenseBackground
      ? "text-emerald-700 bg-emerald-100 border-emerald-200"
      : "text-emerald-700 bg-emerald-50 border-emerald-200"
  }
  if (score >= lowThreshold) {
    return intenseBackground
      ? "text-amber-700 bg-amber-100 border-amber-200"
      : "text-amber-700 bg-amber-50 border-amber-200"
  }
  return intenseBackground
    ? "text-red-700 bg-red-100 border-red-200"
    : "text-red-700 bg-red-50 border-red-200"
}

interface IntelData {
  intel: Record<string, {
    result: Record<string, unknown>
    source_api: string
    actual_cost: number
    created_at?: string
  }>
  total_cost: number
}

interface Props {
  intelData: IntelData
  onReGather: () => void | Promise<void>
}

export default function IntelSection({ intelData, onReGather }: Props) {
  const [expandedSection, setExpandedSection] = useState<string | null>(null)
  const [selectedUnit, setSelectedUnit] = useState<Record<string, unknown> | null>(null)
  const [refreshing, setRefreshing] = useState(false)

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await onReGather()
    } finally {
      setRefreshing(false)
    }
  }

  const toggleSection = (section: string) => {
    setExpandedSection(previous => previous === section ? null : section)
  }

  const unitDetails = intelData.intel.unit_details?.result
  const verifiedScores = intelData.intel.verified_scores?.result
  const distances = intelData.intel.distances?.result
  const floorPlanAnalysis = intelData.intel.floor_plan_analysis?.result
  const concessions = intelData.intel.concessions?.result
  const reviews = intelData.intel.reviews?.result
  const nearbyPlaces = intelData.intel.nearby_places?.result
  const policies = intelData.intel.policies?.result

  // Extract curated neighborhood data for headline + warnings
  const isCurated = nearbyPlaces && (nearbyPlaces as Record<string, unknown>).curated
  const neighborhoodAnalysis = isCurated ? (nearbyPlaces as Record<string, unknown>).analysis as Record<string, unknown> | undefined : undefined
  const headline = neighborhoodAnalysis?.headline as string | undefined
  const watchOutWarnings = neighborhoodAnalysis?.watch_out as string[] | undefined
  const bestFor = neighborhoodAnalysis?.best_for as string | undefined
  const notIdealFor = neighborhoodAnalysis?.not_ideal_for as string | undefined

  // Scores for metrics row
  const walkScore = (verifiedScores as Record<string, unknown> | undefined)?.walk_score as number | null | undefined
  const googleRating = (reviews as Record<string, unknown> | undefined)?.google_rating as number | null | undefined
  const totalRatings = (reviews as Record<string, unknown> | undefined)?.total_ratings as number | null | undefined

  // Build squares — each section that has data gets a square
  const intelSquares: Array<{ key: string; icon: string; label: string; metric: string }> = []
  if (unitDetails && Number((unitDetails as Record<string, unknown>).total_available) > 0) {
    intelSquares.push({ key: "units", icon: "🏢", label: "Units", metric: `${(unitDetails as Record<string, unknown>).total_available}` })
  }
  if (verifiedScores || distances) {
    intelSquares.push({ key: "scores", icon: "✈️", label: "Distances", metric: "" })
  }
  if (floorPlanAnalysis) {
    intelSquares.push({ key: "floorplan", icon: "📐", label: "Floor Plan", metric: "" })
  }
  if (nearbyPlaces && hasUsefulNearbyData(nearbyPlaces)) {
    intelSquares.push({ key: "nearby", icon: "📍", label: "Nearby", metric: "" })
  }
  if (reviews && hasUsefulReviewData(reviews)) {
    intelSquares.push({ key: "reviews", icon: "💬", label: "Reviews", metric: "" })
  }
  if (concessions && hasUsefulConcessionData(concessions)) {
    intelSquares.push({ key: "concessions", icon: "💰", label: "Fees", metric: "" })
  }
  if (policies && hasUsefulPolicyData(policies)) {
    intelSquares.push({ key: "policies", icon: "📋", label: "Policies", metric: "" })
  }

  return (
    <div className="rounded-2xl border border-indigo-200/60 bg-gradient-to-br from-slate-50 via-indigo-50/30 to-white mb-6 relative overflow-hidden shadow-sm">
      {/* Subtle dot pattern */}
      <div className="absolute inset-0 opacity-[0.025]" style={{
        backgroundImage: "radial-gradient(circle, rgba(99,102,241,.6) 1px, transparent 1px)",
        backgroundSize: "20px 20px",
      }} />

      <div className="relative p-5">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center shadow-sm">
              <span className="text-white text-[10px] font-bold">NI</span>
            </div>
            <h3 className="text-xs font-bold text-gray-800 tracking-[0.12em] uppercase">Nest Intel</h3>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[10px] text-gray-400 font-mono">${intelData.total_cost.toFixed(3)}</span>
            <button onClick={handleRefresh} disabled={refreshing}
              className={`text-[11px] px-3.5 py-1.5 rounded-lg font-medium transition-all cursor-pointer ${
                refreshing ? "bg-indigo-100 text-indigo-400 cursor-wait" : "bg-white text-indigo-600 border border-indigo-200 hover:bg-indigo-50 hover:shadow-sm"
              }`}>
              {refreshing ? <span className="flex items-center gap-1.5"><span className="w-3 h-3 border-2 border-indigo-200 border-t-indigo-500 rounded-full animate-spin" />Refreshing...</span> : "Refresh"}
            </button>
          </div>
        </div>

        {/* Headline insight */}
        {headline && (
          <div className="mb-4 px-3.5 py-2.5 rounded-xl bg-white/80 border border-indigo-100/50 shadow-sm">
            <p className="text-[13px] text-gray-700 leading-relaxed">{headline}</p>
          </div>
        )}

        {/* Key insights — plain language, not numbers */}
        {(walkScore != null || googleRating != null) && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {walkScore != null && (
              <span className={`text-[11px] px-3 py-1 rounded-full font-medium backdrop-blur-sm ${
                walkScore >= 70 ? "bg-emerald-50/80 text-emerald-700 border border-emerald-200/60" :
                walkScore >= 40 ? "bg-amber-50/80 text-amber-700 border border-amber-200/60" :
                "bg-red-50/80 text-red-700 border border-red-200/60"
              }`}>
                {walkScore >= 90 ? "🚶 Walker's paradise" :
                 walkScore >= 70 ? "🚶 Very walkable" :
                 walkScore >= 50 ? "🚶 Somewhat walkable" :
                 "🚗 Car-dependent"}
              </span>
            )}
            {googleRating != null && (
              <span className={`text-[11px] px-3 py-1 rounded-full font-medium backdrop-blur-sm ${
                googleRating >= 4.0 ? "bg-emerald-50/80 text-emerald-700 border border-emerald-200/60" :
                googleRating >= 3.0 ? "bg-amber-50/80 text-amber-700 border border-amber-200/60" :
                "bg-red-50/80 text-red-700 border border-red-200/60"
              }`}>
                {googleRating >= 4.5 ? "⭐ Loved by residents" :
                 googleRating >= 4.0 ? "⭐ Well-rated" :
                 googleRating >= 3.0 ? "⭐ Mixed reviews" :
                 "⭐ Poorly rated"}{totalRatings ? ` (${totalRatings})` : ""}
              </span>
            )}
            {(verifiedScores as Record<string, unknown> | undefined)?.transit_score != null && (
              <span className={`text-[11px] px-3 py-1 rounded-full font-medium backdrop-blur-sm ${
                Number((verifiedScores as Record<string, unknown>).transit_score) >= 50 ? "bg-emerald-50/80 text-emerald-700 border border-emerald-200/60" :
                "bg-gray-50/80 text-gray-600 border border-gray-200/60"
              }`}>
                {Number((verifiedScores as Record<string, unknown>).transit_score) >= 70 ? "🚇 Excellent transit" :
                 Number((verifiedScores as Record<string, unknown>).transit_score) >= 50 ? "🚇 Good transit" :
                 "🚇 Limited transit"}
              </span>
            )}
          </div>
        )}

        {/* Interactive squares grid */}
        <div className="flex flex-wrap gap-2.5 mb-4">
          {intelSquares.map(square => {
            const isExpanded = expandedSection === square.key
            return isExpanded ? null : (
              <button key={square.key} onClick={() => toggleSection(square.key)}
                className="group w-[76px] h-[76px] rounded-xl bg-white border border-gray-200/80 shadow-sm hover:shadow-md hover:border-indigo-300 hover:-translate-y-0.5 transition-all duration-200 cursor-pointer flex flex-col items-center justify-center gap-1.5 relative overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-indigo-50/0 to-indigo-50/0 group-hover:from-indigo-50/50 group-hover:to-purple-50/30 transition-all duration-200" />
                <span className="text-lg relative z-10">{square.icon}</span>
                <span className="text-[10px] text-gray-500 font-medium relative z-10 group-hover:text-indigo-600 transition-colors">{square.label}</span>
                {square.metric && <span className="text-[10px] text-indigo-600 font-bold relative z-10">{square.metric}</span>}
              </button>
            )
          })}
        </div>

        {/* Expanded section — only one at a time */}
        {expandedSection === "units" && unitDetails && (
          <ExpandableWrapper onClose={() => toggleSection("units")} icon="🏢" title="Unit Availability">
            <UnitAvailabilityCard data={unitDetails} expanded={true} onToggle={() => toggleSection("units")} selectedUnit={selectedUnit} onSelectUnit={(unit) => setSelectedUnit(unit)} />
          </ExpandableWrapper>
        )}
        {expandedSection === "scores" && (
          <ExpandableWrapper onClose={() => toggleSection("scores")} icon="📊" title="Verified Scores">
            <VerifiedScoresCard scores={verifiedScores as Record<string, unknown> | undefined} distances={distances as Record<string, unknown> | undefined} />
          </ExpandableWrapper>
        )}
        {expandedSection === "floorplan" && floorPlanAnalysis && (
          <ExpandableWrapper onClose={() => toggleSection("floorplan")} icon="📐" title="Floor Plan Analysis">
            <FloorPlanCard data={floorPlanAnalysis} expanded={true} onToggle={() => toggleSection("floorplan")} selectedUnit={selectedUnit} />
          </ExpandableWrapper>
        )}
        {expandedSection === "nearby" && nearbyPlaces && (
          <ExpandableWrapper onClose={() => toggleSection("nearby")} icon="📍" title="Neighborhood">
            <NearbyPlacesCard data={nearbyPlaces} expanded={true} onToggle={() => toggleSection("nearby")} />
          </ExpandableWrapper>
        )}
        {expandedSection === "reviews" && reviews && (
          <ExpandableWrapper onClose={() => toggleSection("reviews")} icon="💬" title="Resident Reviews">
            <ReviewsCard data={reviews} expanded={true} onToggle={() => toggleSection("reviews")} />
          </ExpandableWrapper>
        )}
        {expandedSection === "concessions" && concessions && (
          <ExpandableWrapper onClose={() => toggleSection("concessions")} icon="💰" title="Concessions & Fees">
            <ConcessionsCard data={concessions} />
          </ExpandableWrapper>
        )}
        {expandedSection === "policies" && policies && (
          <ExpandableWrapper onClose={() => toggleSection("policies")} icon="📋" title="Lease Policies">
            <PoliciesCard data={policies} expanded={true} onToggle={() => toggleSection("policies")} />
          </ExpandableWrapper>
        )}

        {/* Best for / Not ideal for */}
        {(bestFor || notIdealFor) && (
          <div className="grid grid-cols-2 gap-2.5 mt-3">
            {bestFor && (
              <div className="px-3.5 py-2.5 rounded-xl bg-gradient-to-br from-emerald-50 to-emerald-50/50 border border-emerald-100/60">
                <p className="text-[10px] text-emerald-500 font-semibold uppercase tracking-wider mb-1">Best for</p>
                <p className="text-xs text-emerald-800 leading-relaxed">{bestFor}</p>
              </div>
            )}
            {notIdealFor && (
              <div className="px-3.5 py-2.5 rounded-xl bg-gradient-to-br from-amber-50 to-amber-50/50 border border-amber-100/60">
                <p className="text-[10px] text-amber-500 font-semibold uppercase tracking-wider mb-1">Not ideal for</p>
                <p className="text-xs text-amber-800 leading-relaxed">{notIdealFor}</p>
              </div>
            )}
          </div>
        )}

        {/* Warnings — at the very bottom, subtle */}
        {watchOutWarnings && watchOutWarnings.length > 0 && (
          <div className="mt-3 space-y-1">
            {watchOutWarnings.map((warning, warningIndex) => (
              <p key={warningIndex} className="text-[11px] text-red-600/80 px-3 py-1.5 rounded-lg bg-red-50/50 border border-red-100/40">⚠️ {warning}</p>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}


// ── Unit Availability Card ──────────────────────────────

function ExpandableWrapper({ onClose, icon, title, children }: {
  onClose: () => void; icon: string; title: string; children: React.ReactNode
}) {
  return (
    <div className="mb-3 rounded-xl bg-white border border-gray-200/80 shadow-lg shadow-indigo-100/30 overflow-hidden animate-in fade-in duration-200">
      <div className="flex items-center justify-between px-4 py-2.5 bg-gradient-to-r from-indigo-50/80 to-purple-50/40 border-b border-indigo-100/50">
        <div className="flex items-center gap-2">
          <span className="text-sm">{icon}</span>
          <span className="text-[13px] font-semibold text-gray-800">{title}</span>
        </div>
        <button onClick={onClose} className="text-[11px] text-gray-400 hover:text-gray-600 cursor-pointer px-2.5 py-1 rounded-lg hover:bg-white/80 transition-all">
          ✕
        </button>
      </div>
      <div className="p-1.5">{children}</div>
    </div>
  )
}


function UnitAvailabilityCard({ data, expanded, onToggle, selectedUnit, onSelectUnit }: {
  data: Record<string, unknown>; expanded: boolean; onToggle: () => void
  selectedUnit?: Record<string, unknown> | null
  onSelectUnit?: (unit: Record<string, unknown>) => void
}) {
  const summary = data.summary as Record<number, {
    label: string; min_price: number; max_price: number; total_available: number
  }> | undefined
  const totalAvailable = data.total_available as number | undefined
  const floorPlans = data.floor_plans as Array<Record<string, unknown>> | undefined

  return (
    <div className="bg-white rounded-xl border border-indigo-100 shadow-sm">
      <button onClick={onToggle} className="w-full px-4 py-3 flex items-center justify-between text-left cursor-pointer">
        <div className="flex items-center gap-2">
          <span className="text-indigo-500 text-sm">🏢</span>
          <span className="text-sm font-semibold text-gray-800">Unit Availability</span>
          {totalAvailable != null && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-600 font-semibold">
              {totalAvailable} available
            </span>
          )}
        </div>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          className={`text-gray-400 transition-transform ${expanded ? "rotate-180" : ""}`}>
          <path d="m6 9 6 6 6-6"/>
        </svg>
      </button>

      {summary && (
        <div className="px-4 pb-3 grid grid-cols-3 gap-2">
          {Object.entries(summary).map(([bedroomKey, typeInfo]) => {
            const isSelected = selectedUnit && String((selectedUnit as Record<string, unknown>).bedrooms) === bedroomKey
            return (
              <button key={bedroomKey}
                onClick={() => onSelectUnit?.({ bedrooms: Number(bedroomKey), label: typeInfo.label, min_price: typeInfo.min_price })}
                className={`px-3 py-2 rounded-lg border text-center transition-all ${
                  isSelected
                    ? "bg-indigo-100 border-indigo-300 ring-1 ring-indigo-400 cursor-pointer"
                    : "bg-indigo-50 border-indigo-100 hover:border-indigo-200 cursor-pointer"
                }`}>
                <p className="text-[10px] text-indigo-400 uppercase font-medium">{typeInfo.label}</p>
                <p className="text-sm font-bold text-gray-800 font-mono">${typeInfo.min_price?.toLocaleString() ?? "—"}</p>
                {typeInfo.min_price !== typeInfo.max_price && typeInfo.max_price && (
                  <p className="text-[10px] text-gray-400">to ${typeInfo.max_price.toLocaleString()}</p>
                )}
                <p className="text-[10px] text-indigo-500 font-medium">{typeInfo.total_available} avail.</p>
                {isSelected && <p className="text-[9px] text-indigo-600 font-semibold mt-0.5">Selected</p>}
              </button>
            )
          })}
          {!selectedUnit && (
            <p className="text-[10px] text-indigo-400 mt-1 col-span-3 text-center">Select a unit type for targeted floor plan analysis</p>
          )}
        </div>
      )}

      {expanded && floorPlans && (
        <div className="px-4 pb-3 space-y-2 border-t border-indigo-50 pt-2">
          {(floorPlans as Array<Record<string, unknown>>).map((plan, planIndex) => {
            const units = plan.units as Array<Record<string, unknown>> | undefined
            if (!units || units.length === 0) return null
            return (
              <div key={planIndex}>
                <p className="text-xs text-indigo-600 font-semibold mb-1">{plan.name as string}</p>
                <div className="space-y-1">
                  {units.map((unit, unitIndex) => (
                    <div key={unitIndex} className="flex items-center justify-between px-3 py-1.5 rounded-lg bg-gray-50 border border-gray-100">
                      <span className="text-xs text-gray-600 font-mono">Unit {unit.unit_number as string || "—"}</span>
                      <div className="flex items-center gap-3 text-xs">
                        {unit.sqft != null && <span className="text-gray-400">{String(unit.sqft)} sqft</span>}
                        {unit.price != null && <span className="text-indigo-600 font-mono font-semibold">${Number(unit.price).toLocaleString()}</span>}
                        {unit.available_date != null && <span className="text-gray-400">{String(unit.available_date)}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}


// ── Verified Scores Card ────────────────────────────────

function VerifiedScoresCard({ scores, distances }: {
  scores?: Record<string, unknown>; distances?: Record<string, unknown>
}) {
  const walkScore = scores?.walk_score as number | null
  const transitScore = scores?.transit_score as number | null
  const bikeScore = scores?.bike_score as number | null
  const airport = distances?.airport as Record<string, unknown> | undefined
  const commute = distances?.commute as Record<string, unknown> | undefined

  const getCommuteVerdict = (durationMinutes: number | null) => {
    if (durationMinutes == null) return null
    if (durationMinutes <= 15) return { text: "Quick commute", style: "text-emerald-700" }
    if (durationMinutes <= 30) return { text: "Reasonable commute", style: "text-emerald-600" }
    if (durationMinutes <= 45) return { text: "Moderate commute", style: "text-amber-600" }
    if (durationMinutes <= 60) return { text: "Long commute", style: "text-orange-600" }
    return { text: "Very long commute", style: "text-red-600" }
  }

  const commuteDurationMinutes = commute?.commute_duration_minutes != null
    ? commute.commute_duration_minutes as number
    : null
  const commuteVerdict = getCommuteVerdict(commuteDurationMinutes)

  return (
    <div className="space-y-3">
      {(walkScore != null || transitScore != null || bikeScore != null) && (
        <div className="flex gap-3">
          {[
            { label: "Walk", value: walkScore, description: scores?.walk_description as string | undefined },
            { label: "Transit", value: transitScore, description: scores?.transit_description as string | undefined },
            { label: "Bike", value: bikeScore, description: scores?.bike_description as string | undefined },
          ].map(({ label, value, description }) => value != null ? (
            <div key={label} className={`flex-1 px-3 py-3 rounded-xl border text-center ${getScoreStyle(value)}`}>
              <p className="text-2xl font-bold font-mono">{value}</p>
              <div className="w-full bg-gray-200 rounded-full h-1.5 mt-1.5 mb-1">
                <div className={`h-1.5 rounded-full transition-all ${
                  value >= 70 ? "bg-emerald-500" : value >= 40 ? "bg-amber-500" : "bg-red-400"
                }`} style={{ width: `${value}%` }} />
              </div>
              <p className="text-[10px] font-semibold">{label}</p>
              {description && <p className="text-[9px] opacity-60 mt-0.5">{description}</p>}
            </div>
          ) : null)}
        </div>
      )}

      {(airport || commute) && (
        <div className="bg-gray-50 rounded-lg px-3 py-2.5 space-y-2">
          {airport && (
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <span>✈️</span>
                <span className="text-gray-600">Airport</span>
              </div>
              <span className="text-indigo-600 font-medium">
                {airport.airport_distance_text as string} ({airport.airport_drive_text as string})
              </span>
            </div>
          )}
          {commute ? (
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <span>🏢</span>
                <span className="text-gray-600">Workplace</span>
              </div>
              <div className="text-right">
                <span className={`font-medium ${commuteVerdict?.style || "text-gray-700"}`}>
                  {commuteVerdict?.text || String(commute.commute_duration_text)}
                </span>
                <span className="text-gray-400 text-xs ml-1.5">
                  {commuteDurationMinutes != null ? `${commuteDurationMinutes} min` : String(commute.commute_duration_text)} · {String(commute.commute_mode)}
                </span>
              </div>
            </div>
          ) : airport ? (
            <p className="text-xs text-gray-400">Set workplace in NestScout Settings for commute insights</p>
          ) : null}
        </div>
      )}
    </div>
  )
}


// ── Floor Plan Analysis Card ────────────────────────────

function FloorPlanCard({ data, expanded, onToggle, selectedUnit }: {
  data: Record<string, unknown>; expanded: boolean; onToggle: () => void
  selectedUnit?: Record<string, unknown> | null
}) {
  const floorPlanImageUrl = data.floor_plan_image_url as string | undefined
  const livabilityScore = data.livability_score as number | undefined
  const roomAssessment = data.room_assessment as Record<string, string> | undefined
  const redFlags = data.red_flags as string[] | undefined
  const greenLights = data.green_lights as string[] | undefined
  const furnitureFit = data.furniture_fit as Record<string, boolean> | undefined
  const wfhSuitability = data.wfh_suitability as string | undefined
  const efficiencyRating = data.efficiency_rating as string | undefined

  return (
    <div className="bg-white rounded-xl border border-indigo-100 shadow-sm">
      <button onClick={onToggle} className="w-full px-4 py-3 flex items-center justify-between text-left cursor-pointer">
        <div className="flex items-center gap-2">
          <span className="text-indigo-500 text-sm">📐</span>
          <span className="text-sm font-semibold text-gray-800">Floor Plan Analysis</span>
          {selectedUnit && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-600 font-medium">
              {String(selectedUnit.label || `${selectedUnit.bedrooms}BR`)} selected
            </span>
          )}
          {livabilityScore != null && (
            <span className={`text-xs px-2 py-0.5 rounded-full font-bold font-mono border ${getScoreStyle(livabilityScore, { highThreshold: 75, lowThreshold: 50, intenseBackground: true })}`}>
              {livabilityScore}/100
            </span>
          )}
        </div>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          className={`text-gray-400 transition-transform ${expanded ? "rotate-180" : ""}`}>
          <path d="m6 9 6 6 6-6"/>
        </svg>
      </button>

      <div className="px-4 pb-3">
        {/* Floor plan image */}
        {floorPlanImageUrl && (
          <div className="mb-3 rounded-lg overflow-hidden border border-gray-100">
            <img src={floorPlanImageUrl} alt="Floor plan" className="w-full max-h-64 object-contain bg-gray-50" loading="lazy" />
          </div>
        )}

        <div className="grid grid-cols-2 gap-2">
          {greenLights && greenLights.length > 0 && (
            <div>
              {greenLights.slice(0, expanded ? 10 : 2).map((light, index) => (
                <p key={index} className="text-xs text-emerald-600 py-0.5">✓ {light}</p>
              ))}
            </div>
          )}
          {redFlags && redFlags.length > 0 && (
            <div>
              {redFlags.slice(0, expanded ? 10 : 2).map((flag, index) => (
                <p key={index} className="text-xs text-red-600 py-0.5">✗ {flag}</p>
              ))}
            </div>
          )}
        </div>

        {furnitureFit && (
          <div className="flex gap-2 mt-2 flex-wrap">
            {Object.entries(furnitureFit).map(([item, fits]) => (
              <span key={item} className={`text-[10px] px-2 py-0.5 rounded-full border font-medium ${
                fits ? "border-emerald-200 bg-emerald-50 text-emerald-700" : "border-red-200 bg-red-50 text-red-700"
              }`}>
                {fits ? "✓" : "✗"} {item.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        )}
      </div>

      {expanded && (
        <div className="px-4 pb-3 space-y-3 border-t border-gray-100 pt-3">
          {wfhSuitability && (
            <div>
              <p className="text-[10px] text-indigo-500 uppercase font-medium mb-1">WFH Suitability</p>
              <p className="text-sm text-gray-700">{wfhSuitability}</p>
            </div>
          )}
          {efficiencyRating && (
            <div>
              <p className="text-[10px] text-indigo-500 uppercase font-medium mb-1">Space Efficiency</p>
              <p className="text-sm text-gray-700">{efficiencyRating}</p>
            </div>
          )}
          {roomAssessment && (
            <div>
              <p className="text-[10px] text-indigo-500 uppercase font-medium mb-1">Room Assessment</p>
              <div className="space-y-1">
                {Object.entries(roomAssessment).map(([room, assessment]) => (
                  <div key={room} className="flex gap-2 text-sm">
                    <span className="text-indigo-600 capitalize font-semibold min-w-[60px]">{room}:</span>
                    <span className="text-gray-600">{assessment}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}


// ── Concessions Card ────────────────────────────────────

function ConcessionsCard({ data }: { data: Record<string, unknown> }) {
  const concessionsList = data.concessions as Array<Record<string, unknown>> | undefined
  const applicationFee = data.application_fee as number | null
  const adminFee = data.admin_fee as number | null
  const petDeposit = data.pet_deposit as number | null
  const petMonthly = data.pet_monthly as number | null
  const parkingMonthly = data.parking_monthly as number | null

  const feeItems = [
    { label: "Application", value: applicationFee },
    { label: "Admin fee", value: adminFee },
    { label: "Pet deposit", value: petDeposit },
    { label: "Pet/mo", value: petMonthly },
    { label: "Parking/mo", value: parkingMonthly },
  ].filter(item => item.value != null)

  return (
    <div className="space-y-3">
      {concessionsList && concessionsList.length > 0 && (
        <div className="space-y-1.5">
          {concessionsList.map((concession, index) => (
            <div key={index} className="px-3.5 py-2.5 rounded-xl bg-gradient-to-r from-emerald-50 to-emerald-50/30 border border-emerald-200/50">
              <p className="text-[13px] text-emerald-700 font-medium">{concession.description as string}</p>
              {concession.monthly_discount != null && (
                <p className="text-[11px] text-emerald-600/70 mt-0.5">
                  Saves ~${(concession.monthly_discount as number).toFixed(0)}/mo effective
                </p>
              )}
            </div>
          ))}
        </div>
      )}

      {feeItems.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {feeItems.map(({ label, value }) => (
            <div key={label} className="px-3 py-2 rounded-xl bg-gray-50/80 border border-gray-100/60">
              <p className="text-[10px] text-gray-400 uppercase tracking-wider">{label}</p>
              <p className="text-[13px] text-gray-800 font-mono font-semibold">${value?.toLocaleString()}</p>
            </div>
          ))}
        </div>
      )}

      {feeItems.length === 0 && !concessionsList?.length && (
        <p className="text-[13px] text-gray-400">No concessions or fees found on listing page</p>
      )}
    </div>
  )
}


// ── Reviews Card ────────────────────────────────────────

function ReviewsCard({ data, expanded, onToggle }: {
  data: Record<string, unknown>; expanded: boolean; onToggle: () => void
}) {
  const googleRating = data.google_rating as number | null
  const totalRatings = data.total_ratings as number | null
  const sentiment = data.sentiment as Record<string, unknown> | undefined
  const themes = (sentiment?.themes || []) as Array<{
    topic: string; sentiment: string; mention_count: number; summary: string
  }>
  const keyQuotes = (sentiment?.key_quotes || []) as Array<{
    text: string; sentiment: string; topic: string
  }>
  const recommendation = sentiment?.recommendation as string | undefined

  const getSentimentStyle = (sentimentValue: string) => {
    if (sentimentValue === "positive") return "text-emerald-700 bg-emerald-50 border-emerald-200"
    if (sentimentValue === "negative") return "text-red-700 bg-red-50 border-red-200"
    return "text-amber-700 bg-amber-50 border-amber-200"
  }

  return (
    <div className="bg-white rounded-xl border border-indigo-100 shadow-sm">
      <button onClick={onToggle} className="w-full px-4 py-3 flex items-center justify-between text-left cursor-pointer">
        <div className="flex items-center gap-2">
          <span className="text-indigo-500 text-sm">💬</span>
          <span className="text-sm font-semibold text-gray-800">Resident Reviews</span>
          {googleRating != null && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-amber-700 font-semibold">
              ⭐ {googleRating} ({totalRatings} reviews)
            </span>
          )}
        </div>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          className={`text-gray-400 transition-transform ${expanded ? "rotate-180" : ""}`}>
          <path d="m6 9 6 6 6-6"/>
        </svg>
      </button>

      {/* Theme summary — always visible */}
      {themes.length > 0 && (
        <div className="px-4 pb-3 space-y-1">
          {themes.slice(0, expanded ? 10 : 4).map((theme, index) => (
            <div key={index} className={`flex items-center justify-between px-3 py-2 rounded-lg border ${getSentimentStyle(theme.sentiment)}`}>
              <div className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{
                  backgroundColor: theme.sentiment === "positive" ? "#059669" : theme.sentiment === "negative" ? "#dc2626" : "#d97706"
                }} />
                <span className="text-[13px] font-medium">{theme.topic}</span>
                <span className="text-[10px] opacity-50">({theme.mention_count})</span>
              </div>
              <span className="text-[11px] text-right max-w-[50%] truncate">{theme.summary}</span>
            </div>
          ))}
        </div>
      )}

      {/* Expanded: quotes + recommendation */}
      {expanded && (
        <div className="px-4 pb-3 space-y-3 border-t border-gray-100/80 pt-3">
          {keyQuotes.length > 0 && (
            <div>
              <p className="text-[10px] text-gray-400 uppercase font-medium tracking-wider mb-2">What residents say</p>
              <div className="space-y-1.5">
                {keyQuotes.map((quote, index) => (
                  <div key={index} className={`px-3.5 py-2.5 rounded-xl border ${
                    quote.sentiment === "positive" ? "bg-emerald-50/30 border-emerald-100/60" : "bg-red-50/30 border-red-100/60"
                  }`}>
                    <p className="text-[13px] text-gray-700 italic leading-relaxed">"{quote.text}"</p>
                    <p className="text-[10px] text-gray-400 mt-1">About {quote.topic}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
          {recommendation && (
            <div className="px-3.5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-50/80 to-purple-50/40 border border-indigo-100/50">
              <p className="text-[10px] text-indigo-400 uppercase font-medium tracking-wider mb-1">Bottom line</p>
              <p className="text-[13px] text-indigo-800 leading-relaxed">{recommendation}</p>
            </div>
          )}
        </div>
      )}

    </div>
  )
}


// ── Policies Card ───────────────────────────────────────

function PoliciesCard({ data, expanded, onToggle }: {
  data: Record<string, unknown>; expanded: boolean; onToggle: () => void
}) {
  const petPolicy = data.pet_policy as Record<string, unknown> | undefined
  const leaseTerms = data.lease_terms as Record<string, unknown> | undefined
  const subletting = data.subletting as Record<string, unknown> | undefined
  const parking = data.parking as Record<string, unknown> | undefined
  const utilities = data.utilities as Record<string, unknown> | undefined
  const moveIn = data.move_in_requirements as Record<string, unknown> | undefined

  // Count how many policy sections have data
  const policyCount = [petPolicy, leaseTerms, subletting, parking, utilities, moveIn]
    .filter(section => section && Object.values(section).some(value => value != null)).length

  return (
    <div className="bg-white rounded-xl border border-indigo-100 shadow-sm">
      <button onClick={onToggle} className="w-full px-4 py-3 flex items-center justify-between text-left cursor-pointer">
        <div className="flex items-center gap-2">
          <span className="text-indigo-500 text-sm">📋</span>
          <span className="text-sm font-semibold text-gray-800">Lease Policies</span>
          {policyCount > 0 && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-600 font-medium">
              {policyCount} sections found
            </span>
          )}
        </div>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          className={`text-gray-400 transition-transform ${expanded ? "rotate-180" : ""}`}>
          <path d="m6 9 6 6 6-6"/>
        </svg>
      </button>

      {/* Quick summary — always visible */}
      <div className="px-4 pb-3 flex flex-wrap gap-2">
        {petPolicy?.allowed != null && (
          <span className={`text-[11px] px-2 py-1 rounded-lg border ${
            petPolicy.allowed ? "bg-emerald-50 border-emerald-200 text-emerald-700" : "bg-red-50 border-red-200 text-red-700"
          }`}>
            {petPolicy.allowed ? `🐾 Pets OK${petPolicy.weight_limit_lbs ? ` (${petPolicy.weight_limit_lbs}lb limit)` : ""}` : "🚫 No pets"}
          </span>
        )}
        {subletting?.allowed != null && (
          <span className={`text-[11px] px-2 py-1 rounded-lg border ${
            subletting.allowed ? "bg-emerald-50 border-emerald-200 text-emerald-700" : "bg-red-50 border-red-200 text-red-700"
          }`}>
            {subletting.allowed ? "✓ Subletting OK" : "✗ No subletting"}
          </span>
        )}
        {leaseTerms?.minimum_months != null && (
          <span className="text-[11px] px-2 py-1 rounded-lg border bg-gray-50 border-gray-200 text-gray-600">
            📅 {String(leaseTerms.minimum_months)}-{String((leaseTerms.maximum_months as number) || "?")} mo lease
          </span>
        )}
        {Boolean(parking?.ev_charging) && (
          <span className="text-[11px] px-2 py-1 rounded-lg border bg-emerald-50 border-emerald-200 text-emerald-700">
            ⚡ EV charging
          </span>
        )}
        {moveIn?.credit_score_minimum != null && (
          <span className="text-[11px] px-2 py-1 rounded-lg border bg-gray-50 border-gray-200 text-gray-600">
            Credit: {String(moveIn.credit_score_minimum)}+
          </span>
        )}
      </div>

      {/* Expanded: full policy details */}
      {expanded && (
        <div className="px-4 pb-3 space-y-3 border-t border-gray-100 pt-3">
          {petPolicy && <PolicySection title="Pet Policy" data={petPolicy} />}
          {leaseTerms && <PolicySection title="Lease Terms" data={leaseTerms} />}
          {parking && <PolicySection title="Parking" data={parking} />}
          {utilities && <PolicySection title="Utilities" data={utilities} />}
          {moveIn && <PolicySection title="Move-In Requirements" data={moveIn} />}
        </div>
      )}
    </div>
  )
}

// ── Nearby Places Card ──────────────────────────────────

function NearbyPlacesCard({ data, expanded, onToggle }: {
  data: Record<string, unknown>; expanded: boolean; onToggle: () => void
}) {
  const isCurated = data.curated as boolean | undefined
  const analysis = data.analysis as Record<string, unknown> | undefined

  // Curated (LLM-analyzed) view
  if (isCurated && analysis) {
    return <CuratedNeighborhoodCard analysis={analysis} expanded={expanded} onToggle={onToggle} />
  }

  // Fallback: raw counts (no LLM)
  const categories = data.categories as Record<string, {
    label: string; icon: string; count: number;
    places: Array<{ name: string; rating: number | null; total_ratings: number | null }>
  }> | undefined

  if (!categories || Object.keys(categories).length === 0) return null

  const categoryEntries = Object.entries(categories).sort(
    ([, categoryA], [, categoryB]) => categoryB.count - categoryA.count
  )

  return (
    <div className="bg-white rounded-xl border border-indigo-100 shadow-sm">
      <button onClick={onToggle} className="w-full px-4 py-3 flex items-center justify-between text-left cursor-pointer">
        <div className="flex items-center gap-2">
          <span className="text-indigo-500 text-sm">📍</span>
          <span className="text-sm font-semibold text-gray-800">Neighborhood</span>
        </div>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          className={`text-gray-400 transition-transform ${expanded ? "rotate-180" : ""}`}>
          <path d="m6 9 6 6 6-6"/>
        </svg>
      </button>
      {expanded && (
        <div className="px-4 pb-3 space-y-2">
          {categoryEntries.slice(0, 6).map(([categoryKey, categoryData]) => (
            <div key={categoryKey}>
              <p className="text-xs text-gray-500 font-medium mb-1">{categoryData.label}</p>
              {categoryData.places.slice(0, 3).map((place, placeIndex) => (
                <p key={placeIndex} className="text-sm text-gray-700 pl-2">
                  {place.name} {place.rating ? `⭐${place.rating}` : ""}
                </p>
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function PolicySection({ title, data }: { title: string; data: Record<string, unknown> }) {
  const entries = Object.entries(data).filter(([, value]) => value != null)
  if (entries.length === 0) return null

  return (
    <div>
      <p className="text-[10px] text-indigo-500 uppercase font-medium mb-1">{title}</p>
      <div className="space-y-0.5">
        {entries.map(([key, value]) => (
          <div key={key} className="flex gap-2 text-sm">
            <span className="text-gray-400 min-w-[120px] capitalize">{key.replace(/_/g, " ")}:</span>
            <span className="text-gray-700">
              {typeof value === "boolean" ? (value ? "Yes" : "No") :
               Array.isArray(value) ? value.join(", ") :
               typeof value === "number" ? (key.includes("monthly") || key.includes("fee") || key.includes("deposit") || key.includes("premium") ? `$${value}` : String(value)) :
               String(value)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}


// ── Curated Neighborhood (LLM-analyzed) ─────────────────

function CuratedNeighborhoodCard({ analysis, expanded, onToggle }: {
  analysis: Record<string, unknown>; expanded: boolean; onToggle: () => void
}) {
  const headline = analysis.headline as string | undefined
  const neighborhoodScore = analysis.neighborhood_score as number | undefined
  const dining = analysis.dining as Record<string, unknown> | undefined
  const dailyEssentials = analysis.daily_essentials as Record<string, unknown> | undefined
  const schools = analysis.schools as Record<string, unknown> | undefined
  const fitnessOutdoors = analysis.fitness_outdoors as Record<string, unknown> | undefined
  const transitCommute = analysis.transit_commute as Record<string, unknown> | undefined
  const watchOut = analysis.watch_out as string[] | undefined
  const bestFor = analysis.best_for as string | undefined
  const notIdealFor = analysis.not_ideal_for as string | undefined

  return (
    <div className="bg-white rounded-xl border border-indigo-100 shadow-sm">
      <button onClick={onToggle} className="w-full px-4 py-3 flex items-center justify-between text-left cursor-pointer">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className="text-indigo-500 text-sm">📍</span>
          <span className="text-sm font-semibold text-gray-800">Neighborhood Intel</span>
          {neighborhoodScore != null && (
            <span className={`text-xs px-2 py-0.5 rounded-full font-bold border ${getScoreStyle(neighborhoodScore, { highThreshold: 75, lowThreshold: 50 })}`}>
              {neighborhoodScore}/100
            </span>
          )}
        </div>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          className={`text-gray-400 transition-transform flex-shrink-0 ${expanded ? "rotate-180" : ""}`}>
          <path d="m6 9 6 6 6-6"/>
        </svg>
      </button>

      {headline && (
        <p className="px-4 pb-2 text-sm text-gray-600 italic">{headline}</p>
      )}

      {watchOut && watchOut.length > 0 && (
        <div className="px-4 pb-3">
          {watchOut.slice(0, expanded ? 10 : 2).map((warning, warningIndex) => (
            <p key={warningIndex} className="text-xs text-red-600 py-0.5">⚠️ {warning}</p>
          ))}
        </div>
      )}

      {expanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-gray-100 pt-3">
          {dining && (
            <NeighborhoodSection
              icon="🍽️" title="Dining" verdict={dining.verdict as string}
              items={(dining.top_picks as Array<Record<string, unknown>> || []).map(pick => ({
                name: String(pick.name || ""),
                detail: pick.cuisine ? `${pick.cuisine}${pick.rating ? ` ⭐${pick.rating}` : ""}` : undefined,
                note: pick.why as string | undefined,
              }))}
              missing={dining.missing as string | undefined}
            />
          )}

          {dailyEssentials && (
            <NeighborhoodSection
              icon="🛒" title="Daily Essentials" verdict={dailyEssentials.verdict as string}
              items={[
                ...((dailyEssentials.grocery as Array<Record<string, unknown>> || []).map(grocery_item => ({
                  name: String(grocery_item.name || ""),
                  detail: grocery_item.distance_note ? String(grocery_item.distance_note) : undefined,
                }))),
                ...((dailyEssentials.pharmacy as Array<Record<string, unknown>> || []).map(pharmacy_item => ({
                  name: `${String(pharmacy_item.name || "")} (pharmacy)`,
                  detail: pharmacy_item.distance_note ? String(pharmacy_item.distance_note) : undefined,
                }))),
              ]}
            />
          )}

          {schools && (
            <NeighborhoodSection
              icon="🏫" title="Schools" verdict={schools.verdict as string}
              items={(schools.notable as Array<Record<string, unknown>> || []).map(school_item => ({
                name: String(school_item.name || ""),
                detail: school_item.rating ? `Rating: ${school_item.rating}` : undefined,
                note: school_item.note as string | undefined,
              }))}
            />
          )}

          {fitnessOutdoors && (
            <NeighborhoodSection
              icon="🌳" title="Fitness & Outdoors" verdict={fitnessOutdoors.verdict as string}
              items={[
                ...((fitnessOutdoors.parks as Array<Record<string, unknown>> || []).map(park_item => ({
                  name: String(park_item.name || ""),
                  note: park_item.note as string | undefined,
                }))),
                ...((fitnessOutdoors.gyms as Array<Record<string, unknown>> || []).map(gym_item => ({
                  name: String(gym_item.name || ""),
                  detail: gym_item.rating ? `⭐${gym_item.rating}` : undefined,
                }))),
              ]}
            />
          )}

          {transitCommute && (
            <NeighborhoodSection
              icon="🚇" title="Transit & Commute" verdict={transitCommute.verdict as string}
              items={transitCommute.nearest_transit ? [{
                name: String(transitCommute.nearest_transit),
                note: transitCommute.notes as string | undefined,
              }] : []}
            />
          )}

          <div className="grid grid-cols-2 gap-3 pt-2">
            {bestFor && (
              <div className="px-3 py-2 rounded-lg bg-emerald-50 border border-emerald-100">
                <p className="text-[10px] text-emerald-600 font-semibold uppercase mb-0.5">Best for</p>
                <p className="text-xs text-emerald-800">{bestFor}</p>
              </div>
            )}
            {notIdealFor && (
              <div className="px-3 py-2 rounded-lg bg-amber-50 border border-amber-100">
                <p className="text-[10px] text-amber-600 font-semibold uppercase mb-0.5">Not ideal for</p>
                <p className="text-xs text-amber-800">{notIdealFor}</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function NeighborhoodSection({ icon, title, verdict, items, missing }: {
  icon: string; title: string; verdict?: string
  items: Array<{ name: string; detail?: string; note?: string }>
  missing?: string
}) {
  return (
    <div className="rounded-lg bg-gray-50/50 px-3.5 py-2.5">
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-sm">{icon}</span>
        <span className="text-xs font-semibold text-gray-800">{title}</span>
      </div>
      {verdict && <p className="text-[11px] text-gray-500 mb-2 pl-5 leading-relaxed">{verdict}</p>}
      <div className="space-y-1 pl-5">
        {items.slice(0, 5).map((item, itemIndex) => (
          <div key={itemIndex} className="flex items-baseline gap-2 text-[13px]">
            <span className="text-gray-700 font-medium">{item.name}</span>
            {item.detail && <span className="text-[11px] text-gray-400 flex-shrink-0">{item.detail}</span>}
            {item.note && <span className="text-[11px] text-gray-500 italic">— {item.note}</span>}
          </div>
        ))}
        {missing && (
          <p className="text-[11px] text-amber-600/80 mt-1.5 italic">Missing nearby: {missing}</p>
        )}
      </div>
    </div>
  )
}
