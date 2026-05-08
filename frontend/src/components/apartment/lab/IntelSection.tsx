import { useState } from "react"
import { hasUsefulConcessionData, hasUsefulReviewData, hasUsefulPolicyData, hasUsefulNearbyData } from "./intelHelpers"

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
  onReGather: () => void
}

export default function IntelSection({ intelData, onReGather }: Props) {
  const [expandedSection, setExpandedSection] = useState<string | null>(null)

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

  return (
    <div className="rounded-2xl border border-indigo-200 bg-gradient-to-br from-indigo-50 via-purple-50 to-white p-1 mb-6 relative overflow-hidden">
      {/* Subtle grid */}
      <div className="absolute inset-0 opacity-[0.03]" style={{
        backgroundImage: "linear-gradient(rgba(99,102,241,.4) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,.4) 1px, transparent 1px)",
        backgroundSize: "16px 16px",
      }} />

      <div className="relative">
        {/* Header bar */}
        <div className="flex items-center justify-between px-5 py-3">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
            <h3 className="text-xs font-bold text-indigo-700 tracking-[0.15em] uppercase">Nest Intel</h3>
            <span className="text-[10px] text-indigo-400 font-mono ml-2">
              ${intelData.total_cost.toFixed(3)} spent
            </span>
          </div>
          <button
            onClick={onReGather}
            className="text-xs px-3 py-1 rounded-lg bg-indigo-100 text-indigo-600 hover:bg-indigo-200 font-medium transition-colors"
          >
            Refresh Intel
          </button>
        </div>

        {/* Content cards */}
        <div className="space-y-1.5 px-1 pb-1">
          {unitDetails && (unitDetails as Record<string, unknown>).total_available != null && Number((unitDetails as Record<string, unknown>).total_available) > 0 && <UnitAvailabilityCard data={unitDetails} expanded={expandedSection === "units"} onToggle={() => toggleSection("units")} />}
          {(verifiedScores || distances) && (
            <VerifiedScoresCard
              scores={verifiedScores as Record<string, unknown> | undefined}
              distances={distances as Record<string, unknown> | undefined}
            />
          )}
          {floorPlanAnalysis && <FloorPlanCard data={floorPlanAnalysis} expanded={expandedSection === "floorplan"} onToggle={() => toggleSection("floorplan")} />}
          {concessions && hasUsefulConcessionData(concessions) && <ConcessionsCard data={concessions} />}
          {nearbyPlaces && hasUsefulNearbyData(nearbyPlaces) && <NearbyPlacesCard data={nearbyPlaces} expanded={expandedSection === "nearby"} onToggle={() => toggleSection("nearby")} />}
          {reviews && hasUsefulReviewData(reviews) && <ReviewsCard data={reviews} expanded={expandedSection === "reviews"} onToggle={() => toggleSection("reviews")} />}
          {policies && hasUsefulPolicyData(policies) && <PoliciesCard data={policies} expanded={expandedSection === "policies"} onToggle={() => toggleSection("policies")} />}
        </div>
      </div>
    </div>
  )
}


// ── Unit Availability Card ──────────────────────────────

function UnitAvailabilityCard({ data, expanded, onToggle }: {
  data: Record<string, unknown>; expanded: boolean; onToggle: () => void
}) {
  const summary = data.summary as Record<number, {
    label: string; min_price: number; max_price: number; total_available: number
  }> | undefined
  const totalAvailable = data.total_available as number | undefined
  const floorPlans = data.floor_plans as Array<Record<string, unknown>> | undefined

  return (
    <div className="bg-white rounded-xl border border-indigo-100 shadow-sm">
      <button onClick={onToggle} className="w-full px-4 py-3 flex items-center justify-between text-left">
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
          {Object.entries(summary).map(([bedroomKey, typeInfo]) => (
            <div key={bedroomKey} className="px-3 py-2 rounded-lg bg-indigo-50 border border-indigo-100 text-center">
              <p className="text-[10px] text-indigo-400 uppercase font-medium">{typeInfo.label}</p>
              <p className="text-sm font-bold text-gray-800 font-mono">${typeInfo.min_price?.toLocaleString() ?? "—"}</p>
              {typeInfo.min_price !== typeInfo.max_price && typeInfo.max_price && (
                <p className="text-[10px] text-gray-400">to ${typeInfo.max_price.toLocaleString()}</p>
              )}
              <p className="text-[10px] text-indigo-500 font-medium">{typeInfo.total_available} avail.</p>
            </div>
          ))}
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

  const getScoreStyle = (score: number) => {
    if (score >= 70) return "text-emerald-700 bg-emerald-50 border-emerald-200"
    if (score >= 40) return "text-amber-700 bg-amber-50 border-amber-200"
    return "text-red-700 bg-red-50 border-red-200"
  }

  return (
    <div className="bg-white rounded-xl border border-indigo-100 shadow-sm px-4 py-3">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-indigo-500 text-sm">📊</span>
        <span className="text-sm font-semibold text-gray-800">Verified Scores</span>
      </div>

      {(walkScore != null || transitScore != null || bikeScore != null) && (
        <div className="flex gap-3 mb-3">
          {[
            { label: "Walk", value: walkScore, description: scores?.walk_description as string | undefined },
            { label: "Transit", value: transitScore, description: scores?.transit_description as string | undefined },
            { label: "Bike", value: bikeScore, description: scores?.bike_description as string | undefined },
          ].map(({ label, value, description }) => value != null ? (
            <div key={label} className={`flex-1 px-3 py-2 rounded-xl border text-center ${getScoreStyle(value)}`}>
              <p className="text-xl font-bold font-mono">{value}</p>
              <p className="text-[10px] font-medium">{label}</p>
              {description && <p className="text-[9px] opacity-70 mt-0.5">{description}</p>}
            </div>
          ) : null)}
        </div>
      )}

      {(airport || commute) && (
        <div className="space-y-1.5">
          {airport && (
            <div className="flex items-center gap-2 text-sm">
              <span>✈️</span>
              <span className="text-gray-500">Airport:</span>
              <span className="text-indigo-600 font-medium">
                {airport.airport_distance_text as string} ({airport.airport_drive_text as string})
              </span>
            </div>
          )}
          {commute ? (
            <div className="flex items-center gap-2 text-sm">
              <span>🏢</span>
              <span className="text-gray-500">Commute:</span>
              <span className="text-indigo-600 font-medium">
                {String(commute.commute_duration_text)} by {String(commute.commute_mode)}
              </span>
            </div>
          ) : airport ? (
            <p className="text-xs text-gray-400 mt-1">Set workplace in NestScout Settings for commute time</p>
          ) : null}
        </div>
      )}
    </div>
  )
}


// ── Floor Plan Analysis Card ────────────────────────────

function FloorPlanCard({ data, expanded, onToggle }: {
  data: Record<string, unknown>; expanded: boolean; onToggle: () => void
}) {
  const livabilityScore = data.livability_score as number | undefined
  const roomAssessment = data.room_assessment as Record<string, string> | undefined
  const redFlags = data.red_flags as string[] | undefined
  const greenLights = data.green_lights as string[] | undefined
  const furnitureFit = data.furniture_fit as Record<string, boolean> | undefined
  const wfhSuitability = data.wfh_suitability as string | undefined
  const efficiencyRating = data.efficiency_rating as string | undefined

  const getScoreStyle = (score: number) => {
    if (score >= 75) return "bg-emerald-100 text-emerald-700 border-emerald-200"
    if (score >= 50) return "bg-amber-100 text-amber-700 border-amber-200"
    return "bg-red-100 text-red-700 border-red-200"
  }

  return (
    <div className="bg-white rounded-xl border border-indigo-100 shadow-sm">
      <button onClick={onToggle} className="w-full px-4 py-3 flex items-center justify-between text-left">
        <div className="flex items-center gap-2">
          <span className="text-indigo-500 text-sm">📐</span>
          <span className="text-sm font-semibold text-gray-800">Floor Plan Analysis</span>
          {livabilityScore != null && (
            <span className={`text-xs px-2 py-0.5 rounded-full font-bold font-mono border ${getScoreStyle(livabilityScore)}`}>
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
    <div className="bg-white rounded-xl border border-indigo-100 shadow-sm px-4 py-3">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-indigo-500 text-sm">💰</span>
        <span className="text-sm font-semibold text-gray-800">Concessions + Fees</span>
      </div>

      {concessionsList && concessionsList.length > 0 && (
        <div className="space-y-1.5 mb-3">
          {concessionsList.map((concession, index) => (
            <div key={index} className="px-3 py-2 rounded-lg bg-emerald-50 border border-emerald-200">
              <p className="text-sm text-emerald-700 font-semibold">{concession.description as string}</p>
              {concession.monthly_discount != null && (
                <p className="text-[10px] text-emerald-600 mt-0.5">
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
            <div key={label} className="px-3 py-1.5 rounded-lg bg-gray-50 border border-gray-100">
              <p className="text-[10px] text-gray-400">{label}</p>
              <p className="text-sm text-gray-800 font-mono font-semibold">${value?.toLocaleString()}</p>
            </div>
          ))}
        </div>
      )}

      {feeItems.length === 0 && !concessionsList?.length && (
        <p className="text-sm text-gray-400">No concessions or fees found on listing page</p>
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
      <button onClick={onToggle} className="w-full px-4 py-3 flex items-center justify-between text-left">
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
        <div className="px-4 pb-3 space-y-1.5">
          {themes.slice(0, expanded ? 10 : 4).map((theme, index) => (
            <div key={index} className={`flex items-center justify-between px-3 py-1.5 rounded-lg border ${getSentimentStyle(theme.sentiment)}`}>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{theme.topic}</span>
                <span className="text-[10px] opacity-70">({theme.mention_count} mentions)</span>
              </div>
              <span className="text-xs">{theme.summary}</span>
            </div>
          ))}
        </div>
      )}

      {/* Expanded: quotes + recommendation */}
      {expanded && (
        <div className="px-4 pb-3 space-y-3 border-t border-gray-100 pt-3">
          {keyQuotes.length > 0 && (
            <div>
              <p className="text-[10px] text-indigo-500 uppercase font-medium mb-1">Key Quotes</p>
              {keyQuotes.map((quote, index) => (
                <div key={index} className={`px-3 py-2 rounded-lg border mb-1.5 ${
                  quote.sentiment === "positive" ? "bg-emerald-50/50 border-emerald-100" : "bg-red-50/50 border-red-100"
                }`}>
                  <p className="text-sm text-gray-700 italic">"{quote.text}"</p>
                  <p className="text-[10px] text-gray-400 mt-0.5">Re: {quote.topic}</p>
                </div>
              ))}
            </div>
          )}
          {recommendation && (
            <div className="px-3 py-2 rounded-lg bg-indigo-50 border border-indigo-100">
              <p className="text-[10px] text-indigo-500 uppercase font-medium mb-0.5">Recommendation</p>
              <p className="text-sm text-indigo-800">{recommendation}</p>
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
      <button onClick={onToggle} className="w-full px-4 py-3 flex items-center justify-between text-left">
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
  const categories = data.categories as Record<string, {
    label: string; icon: string; count: number;
    places: Array<{ name: string; rating: number | null; total_ratings: number | null; address: string | null }>
  }> | undefined
  const totalPlaces = data.total_places as number | undefined

  if (!categories || Object.keys(categories).length === 0) return null

  const categoryEntries = Object.entries(categories).sort(
    ([, categoryA], [, categoryB]) => categoryB.count - categoryA.count
  )

  return (
    <div className="bg-white rounded-xl border border-indigo-100 shadow-sm">
      <button onClick={onToggle} className="w-full px-4 py-3 flex items-center justify-between text-left">
        <div className="flex items-center gap-2">
          <span className="text-indigo-500 text-sm">📍</span>
          <span className="text-sm font-semibold text-gray-800">Nearby Places</span>
          {totalPlaces != null && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-600 font-medium">
              {totalPlaces} places found
            </span>
          )}
        </div>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
          className={`text-gray-400 transition-transform ${expanded ? "rotate-180" : ""}`}>
          <path d="m6 9 6 6 6-6"/>
        </svg>
      </button>

      <div className="px-4 pb-3 grid grid-cols-3 sm:grid-cols-4 gap-2">
        {categoryEntries.slice(0, expanded ? 12 : 8).map(([categoryKey, categoryData]) => (
          <div key={categoryKey} className="px-2 py-1.5 rounded-lg bg-gray-50 border border-gray-100 text-center">
            <span className="text-sm">{categoryData.icon}</span>
            <p className="text-[10px] text-gray-500 font-medium truncate">{categoryData.label}</p>
            <p className="text-xs text-indigo-600 font-semibold">{categoryData.count}</p>
          </div>
        ))}
      </div>

      {expanded && (
        <div className="px-4 pb-3 space-y-3 border-t border-gray-100 pt-3">
          {categoryEntries.map(([categoryKey, categoryData]) => (
            <div key={categoryKey}>
              <p className="text-xs text-indigo-600 font-semibold mb-1">
                {categoryData.icon} {categoryData.label} ({categoryData.count})
              </p>
              <div className="space-y-1">
                {categoryData.places.slice(0, 5).map((place, placeIndex) => (
                  <div key={placeIndex} className="flex items-center justify-between text-sm px-2 py-1 rounded bg-gray-50">
                    <span className="text-gray-700 truncate flex-1">{place.name}</span>
                    <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                      {place.rating != null && (
                        <span className={`text-xs font-medium ${
                          place.rating >= 4.0 ? "text-emerald-600" : place.rating >= 3.0 ? "text-amber-600" : "text-gray-400"
                        }`}>
                          ⭐ {place.rating}
                        </span>
                      )}
                      {place.total_ratings != null && (
                        <span className="text-[10px] text-gray-400">({String(place.total_ratings)})</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
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
