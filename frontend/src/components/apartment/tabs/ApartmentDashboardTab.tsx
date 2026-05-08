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
import ApartmentCard from "@/components/apartment/dashboard/ApartmentCard"
import ApartmentCardExpanded from "@/components/apartment/dashboard/ApartmentCardExpanded"
import HuntFunnel from "@/components/apartment/dashboard/HuntFunnel"
import HuntStatsStrip from "@/components/apartment/dashboard/HuntStatsStrip"
import CelebrationOverlay from "@/components/apartment/dashboard/CelebrationOverlay"
import SearchProfileCard from "@/components/apartment/dashboard/SearchProfileCard"
import CompromiseExplorer from "@/components/apartment/dashboard/CompromiseExplorer"
import type { DashboardFunnelStage, DashboardListing, DashboardStats, Achievement, SearchProfile } from "@/types"

const STAGE_ORDER = ["interested", "visited", "applied", "approved", "moved_in"]

const STAGE_LABELS: Record<string, string> = {
  interested: "Interested",
  visited: "Visited",
  applied: "Applied",
  approved: "Approved",
  moved_in: "Moved In",
}

export default function ApartmentDashboardTab() {
  const [funnelData, setFunnelData] = useState<{ stages: Record<string, DashboardFunnelStage>; total_saved: number } | null>(null)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [selectedStage, setSelectedStage] = useState("interested")
  const [expandedCardId, setExpandedCardId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [advancingListingId, setAdvancingListingId] = useState<number | null>(null)
  const [achievements, setAchievements] = useState<Achievement[]>([])
  const [celebratingAchievement, setCelebratingAchievement] = useState<Achievement | null>(null)
  const [searchProfile, setSearchProfile] = useState<SearchProfile | null>(null)
  const [showCompromiseExplorer, setShowCompromiseExplorer] = useState(false)
  const [profileDismissed, setProfileDismissed] = useState(false)

  const loadDashboardData = useCallback(async () => {
    try {
      const [funnelResponse, statsResponse] = await Promise.all([
        api.getDashboardFunnel(),
        api.getDashboardStats(),
      ])
      setFunnelData(funnelResponse)
      setStats(statsResponse)

      // Load search profile and achievements (non-blocking — don't fail dashboard if these fail)
      api.getDashboardProfile()
        .then((profileResponse) => setSearchProfile(profileResponse))
        .catch(() => setSearchProfile(null))

      api.getAchievements()
        .then((achievementsResponse) => setAchievements(achievementsResponse))
        .catch(() => setAchievements([]))

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
        setCelebratingAchievement(result.achievement_unlocked)
      }
      await loadDashboardData()
    } catch {
      toast.error("Failed to advance listing")
    } finally {
      setAdvancingListingId(null)
    }
  }

  const handleArchiveListing = async (listingId: number) => {
    try {
      await api.archiveListing(listingId)
      toast.success("Listing archived")
      setExpandedCardId(null)
      await loadDashboardData()
    } catch {
      toast.error("Failed to archive listing")
    }
  }

  const handleSetStage = async (listingId: number, newStage: string) => {
    try {
      await api.setStage(listingId, newStage)
      toast.success(`Moved to ${STAGE_LABELS[newStage] ?? newStage}`)
      setExpandedCardId(null)
      await loadDashboardData()
    } catch {
      toast.error("Failed to change stage")
    }
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

  return (
    <div className="space-y-5">
      {/* Stats Strip */}
      {stats && (
        <HuntStatsStrip stats={stats} achievements={achievements} />
      )}

      {/* Funnel */}
      <HuntFunnel
        stages={Object.fromEntries(
          STAGE_ORDER.map((stage) => [stage, { count: funnelData.stages[stage]?.count ?? 0 }]),
        )}
        selectedStage={selectedStage}
        onSelectStage={setSelectedStage}
      />

      {/* Celebration Overlay */}
      {celebratingAchievement && (
        <CelebrationOverlay
          achievement={celebratingAchievement}
          onDismiss={() => setCelebratingAchievement(null)}
        />
      )}

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
            {currentStageListings.map((listing) =>
              expandedCardId === listing.id ? (
                <div key={listing.id} className="md:col-span-2">
                  <ApartmentCardExpanded
                    listing={listing}
                    onAdvance={() => handleAdvanceStage(listing.id)}
                    onArchive={() => handleArchiveListing(listing.id)}
                    onStageChange={(newStage) => handleSetStage(listing.id, newStage)}
                    onCollapse={() => setExpandedCardId(null)}
                  />
                </div>
              ) : (
                <ApartmentCard
                  key={listing.id}
                  listing={listing}
                  onExpand={() => setExpandedCardId(listing.id)}
                />
              ),
            )}
          </div>
        )}
      </div>

      {/* Search Profile Card — shown when profile is ready and not dismissed */}
      {searchProfile?.ready && !profileDismissed && (
        <SearchProfileCard
          profile={searchProfile}
          onExploreCompromises={() => setShowCompromiseExplorer(true)}
          onDismiss={() => setProfileDismissed(true)}
        />
      )}

      {/* Compromise Explorer drawer */}
      {showCompromiseExplorer && searchProfile?.ready && (
        <CompromiseExplorer
          profile={searchProfile}
          onClose={() => setShowCompromiseExplorer(false)}
        />
      )}
    </div>
  )
}


