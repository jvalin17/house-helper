/**
 * ApartmentDashboardTab — orchestrator for the NestScout Dashboard tab.
 *
 * Loads funnel + stats in parallel, renders a funnel bar with stage segments,
 * listing cards for the selected stage, and a stats strip at the top.
 * Detail components (photos, notes, etc.) come in later slabs.
 */

import { useEffect, useState, useCallback } from "react"
import { toast } from "sonner"
import { api } from "@/api/client"
import ScoreRing from "@/components/apartment/dashboard/ScoreRing"
import type { DashboardFunnelStage, DashboardListing, DashboardStats, Achievement } from "@/types"

const STAGE_ORDER = ["interested", "visited", "applied", "approved", "moved_in"]

const STAGE_LABELS: Record<string, string> = {
  interested: "Interested",
  visited: "Visited",
  applied: "Applied",
  approved: "Approved",
  moved_in: "Moved In",
}

const STAGE_COLORS: Record<string, { background: string; text: string; bar: string }> = {
  interested: { background: "bg-indigo-50", text: "text-indigo-700", bar: "bg-indigo-400" },
  visited: { background: "bg-purple-50", text: "text-purple-700", bar: "bg-purple-400" },
  applied: { background: "bg-amber-50", text: "text-amber-700", bar: "bg-amber-400" },
  approved: { background: "bg-emerald-50", text: "text-emerald-700", bar: "bg-emerald-400" },
  moved_in: { background: "bg-teal-50", text: "text-teal-700", bar: "bg-teal-400" },
}

export default function ApartmentDashboardTab() {
  const [funnelData, setFunnelData] = useState<{ stages: Record<string, DashboardFunnelStage>; total_saved: number } | null>(null)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [selectedStage, setSelectedStage] = useState("interested")
  const [expandedCardId, setExpandedCardId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [advancingListingId, setAdvancingListingId] = useState<number | null>(null)

  const loadDashboardData = useCallback(async () => {
    try {
      const [funnelResponse, statsResponse] = await Promise.all([
        api.getDashboardFunnel(),
        api.getDashboardStats(),
      ])
      setFunnelData(funnelResponse)
      setStats(statsResponse)

      // Auto-select first non-empty stage if current selection is empty
      if (funnelResponse.stages[selectedStage]?.count === 0) {
        const firstNonEmptyStage = STAGE_ORDER.find(
          (stage) => (funnelResponse.stages[stage]?.count ?? 0) > 0,
        )
        if (firstNonEmptyStage) {
          setSelectedStage(firstNonEmptyStage)
        }
      }
    } catch {
      toast.error("Failed to load dashboard data")
    } finally {
      setLoading(false)
    }
  }, [selectedStage])

  useEffect(() => {
    loadDashboardData()
  }, [loadDashboardData])

  const handleAdvanceStage = async (listingId: number) => {
    setAdvancingListingId(listingId)
    try {
      const result = await api.advanceStage(listingId)
      toast.success(`Moved to ${STAGE_LABELS[result.new_stage] ?? result.new_stage}`)
      if (result.achievement_unlocked) {
        showAchievementToast(result.achievement_unlocked)
      }
      await loadDashboardData()
    } catch {
      toast.error("Failed to advance listing")
    } finally {
      setAdvancingListingId(null)
    }
  }

  const showAchievementToast = (achievement: Achievement) => {
    toast.success(
      `Achievement Unlocked: ${achievement.title}`,
      { description: achievement.description, duration: 5000 },
    )
  }

  // Loading state
  if (loading) {
    return (
      <div className="rounded-2xl bg-white border shadow-sm p-8">
        <div className="flex items-center justify-center py-16">
          <div className="animate-pulse flex flex-col items-center gap-3">
            <div className="w-12 h-12 rounded-full bg-indigo-100" />
            <div className="h-4 w-40 rounded bg-gray-200" />
            <div className="h-3 w-28 rounded bg-gray-100" />
          </div>
        </div>
      </div>
    )
  }

  // Empty state — no saved apartments
  if (!funnelData || funnelData.total_saved === 0) {
    return (
      <div className="rounded-2xl bg-white border shadow-sm p-8">
        <div className="text-center py-16">
          <div className="w-16 h-16 rounded-2xl bg-indigo-50 flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955a1.126 1.126 0 011.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
            </svg>
          </div>
          <h2 className="text-lg font-semibold text-gray-800 mb-2">Start Your Apartment Hunt</h2>
          <p className="text-sm text-gray-500 max-w-md mx-auto">
            Save apartments from Nest Search to start your hunt.
            Your shortlisted homes will appear here with visual tracking through every stage.
          </p>
        </div>
      </div>
    )
  }

  const currentStageListings: DashboardListing[] =
    funnelData.stages[selectedStage]?.listings ?? []

  const totalListingsInFunnel = STAGE_ORDER.reduce(
    (total, stage) => total + (funnelData.stages[stage]?.count ?? 0),
    0,
  )

  return (
    <div className="space-y-5">
      {/* Stats Strip */}
      {stats && (
        <div className="rounded-2xl bg-white border shadow-sm p-5">
          <div className="grid grid-cols-4 gap-4">
            <StatsCard label="Total Saved" value={stats.total_saved} color="text-indigo-600" />
            <StatsCard label="Visited" value={stats.visited_count} color="text-purple-600" />
            <StatsCard label="Applied" value={stats.applied_count} color="text-amber-600" />
            <StatsCard
              label="Avg Rent"
              value={stats.average_rent ? `$${Math.round(stats.average_rent).toLocaleString()}` : "--"}
              color="text-gray-600"
            />
          </div>
        </div>
      )}

      {/* Funnel Bar */}
      <div className="rounded-2xl bg-white border shadow-sm p-5">
        <h3 className="text-sm font-medium text-gray-500 mb-3">Hunt Progress</h3>
        <div className="flex gap-1 h-10 rounded-xl overflow-hidden bg-gray-100">
          {STAGE_ORDER.map((stage) => {
            const stageCount = funnelData.stages[stage]?.count ?? 0
            const widthPercent = totalListingsInFunnel > 0
              ? Math.max((stageCount / totalListingsInFunnel) * 100, stageCount > 0 ? 8 : 2)
              : 20
            const isSelected = selectedStage === stage
            const stageColor = STAGE_COLORS[stage] ?? STAGE_COLORS.interested

            return (
              <button
                key={stage}
                onClick={() => setSelectedStage(stage)}
                className={`relative flex items-center justify-center transition-all duration-200 ${stageColor.bar} ${
                  isSelected ? "ring-2 ring-indigo-500 ring-offset-1 z-10" : "opacity-70 hover:opacity-90"
                }`}
                style={{ width: `${widthPercent}%` }}
                title={`${STAGE_LABELS[stage]}: ${stageCount}`}
              >
                <span className="text-xs font-medium text-white truncate px-2">
                  {STAGE_LABELS[stage]} ({stageCount})
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Listing Cards for Selected Stage */}
      <div className="space-y-3">
        <h3 className="text-sm font-medium text-gray-500">
          {STAGE_LABELS[selectedStage]} ({currentStageListings.length})
        </h3>

        {currentStageListings.length === 0 ? (
          <div className="rounded-2xl bg-white border shadow-sm p-6 text-center">
            <p className="text-sm text-gray-400">
              No apartments in {STAGE_LABELS[selectedStage]} stage
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {currentStageListings.map((listing) => (
              <ListingCard
                key={listing.id}
                listing={listing}
                isExpanded={expandedCardId === listing.id}
                isAdvancing={advancingListingId === listing.id}
                onToggleExpand={() =>
                  setExpandedCardId(expandedCardId === listing.id ? null : listing.id)
                }
                onAdvance={() => handleAdvanceStage(listing.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Sub-components ───────────────────────────────

interface StatsCardProps {
  label: string
  value: number | string
  color: string
}

function StatsCard({ label, value, color }: StatsCardProps) {
  return (
    <div className="text-center">
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
      <p className="text-xs text-gray-400 mt-0.5">{label}</p>
    </div>
  )
}

interface ListingCardProps {
  listing: DashboardListing
  isExpanded: boolean
  isAdvancing: boolean
  onToggleExpand: () => void
  onAdvance: () => void
}

function ListingCard({ listing, isExpanded, isAdvancing, onToggleExpand, onAdvance }: ListingCardProps) {
  const stageColor = STAGE_COLORS[listing.stage] ?? STAGE_COLORS.interested
  const currentStageIndex = STAGE_ORDER.indexOf(listing.stage)
  const isAtFinalStage = currentStageIndex >= STAGE_ORDER.length - 1
  const nextStageLabel = isAtFinalStage
    ? null
    : STAGE_LABELS[STAGE_ORDER[currentStageIndex + 1]]

  return (
    <div
      className={`rounded-xl bg-white border shadow-sm transition-all duration-200 hover:shadow-md ${
        isExpanded ? "ring-1 ring-indigo-200" : ""
      }`}
    >
      <button
        onClick={onToggleExpand}
        className="w-full text-left p-4"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-semibold text-gray-800 truncate">{listing.title}</h4>
            <p className="text-xs text-gray-400 truncate mt-0.5">{listing.address}</p>
            <div className="flex items-center gap-2 mt-2">
              {listing.effective_monthly != null && (
                <span className="text-sm font-medium text-gray-700">
                  ${Math.round(listing.effective_monthly).toLocaleString()}/mo
                </span>
              )}
              <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${stageColor.background} ${stageColor.text}`}>
                {STAGE_LABELS[listing.stage] ?? listing.stage}
              </span>
              {listing.has_intel && (
                <span className="text-[10px] font-medium px-2 py-0.5 rounded-full bg-blue-50 text-blue-600">
                  Intel
                </span>
              )}
              {listing.photo_count > 0 && (
                <span className="text-[10px] text-gray-400">
                  {listing.photo_count} photo{listing.photo_count !== 1 ? "s" : ""}
                </span>
              )}
            </div>
          </div>
          {listing.match_score != null && (
            <ScoreRing score={listing.match_score} size={44} strokeWidth={3} />
          )}
        </div>
      </button>

      {/* Expanded detail area */}
      {isExpanded && (
        <div className="border-t px-4 py-3 bg-gray-50/50 rounded-b-xl">
          <div className="flex items-center justify-between">
            <a
              href={listing.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-indigo-500 hover:text-indigo-700 underline underline-offset-2"
            >
              View Original Listing
            </a>
            {!isAtFinalStage && nextStageLabel && (
              <button
                onClick={(event) => {
                  event.stopPropagation()
                  onAdvance()
                }}
                disabled={isAdvancing}
                className="text-xs font-medium px-3 py-1.5 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isAdvancing ? "Moving..." : `Advance to ${nextStageLabel}`}
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
