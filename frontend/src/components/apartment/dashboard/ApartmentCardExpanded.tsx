/**
 * ApartmentCardExpanded — inline expanded view for a dashboard listing.
 *
 * Renders below/in-place-of the collapsed ApartmentCard. Contains action bar,
 * visit notes editor, observation toggles, cost summary, and stage selector.
 */

import { useState, useCallback, useEffect } from "react"
import { api } from "@/api/client"
import VisitNotesEditor from "@/components/apartment/dashboard/VisitNotesEditor"
import ObservationToggles from "@/components/apartment/dashboard/ObservationToggles"
import CostSummary from "@/components/apartment/dashboard/CostSummary"
import VisitPhotoGallery from "@/components/apartment/dashboard/VisitPhotoGallery"
import type { DashboardListing } from "@/types"

const STAGE_ORDER = ["interested", "visited", "applied", "approved", "moved_in"]

const STAGE_LABELS: Record<string, string> = {
  interested: "Interested",
  visited: "Visited",
  applied: "Applied",
  approved: "Approved",
  moved_in: "Moved In",
}

interface ApartmentCardExpandedProps {
  listing: DashboardListing
  onAdvance: () => void
  onArchive: () => void
  onStageChange: (newStage: string) => void
  onCollapse: () => void
}

export default function ApartmentCardExpanded({
  listing,
  onAdvance,
  onArchive,
  onStageChange,
  onCollapse,
}: ApartmentCardExpandedProps) {
  const [structuredObservations, setStructuredObservations] = useState<Record<string, boolean> | null>(null)
  const [archiving, setArchiving] = useState(false)

  const currentStageIndex = STAGE_ORDER.indexOf(listing.stage)
  const isAtFinalStage = currentStageIndex >= STAGE_ORDER.length - 1
  const nextStageLabel = isAtFinalStage
    ? null
    : STAGE_LABELS[STAGE_ORDER[currentStageIndex + 1]]

  // Load structured data for observations
  useEffect(() => {
    api.getDashboardNotes(listing.id).then((existingNotes) => {
      if (existingNotes?.structured_data) {
        setStructuredObservations(existingNotes.structured_data as Record<string, boolean>)
      }
    }).catch(() => {})
  }, [listing.id])

  const handleObservationUpdate = useCallback(async (updatedObservations: Record<string, boolean>) => {
    setStructuredObservations(updatedObservations)
    try {
      // Get current notes to preserve them while updating structured data
      const currentNotes = await api.getDashboardNotes(listing.id)
      await api.saveDashboardNotes(
        listing.id,
        currentNotes?.notes ?? "",
        updatedObservations,
      )
    } catch {
      // Silently fail — observations are best-effort
    }
  }, [listing.id])

  const handleArchive = useCallback(async () => {
    setArchiving(true)
    try {
      await onArchive()
    } finally {
      setArchiving(false)
    }
  }, [onArchive])

  const handleStageSelect = useCallback((event: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedStage = event.target.value
    if (selectedStage !== listing.stage) {
      onStageChange(selectedStage)
    }
  }, [listing.stage, onStageChange])

  // Lab URL uses the listing id
  const labUrl = `/apartments/${listing.id}/lab`

  return (
    <div className="rounded-xl bg-white border border-indigo-200/80 shadow-md overflow-hidden transition-all duration-200">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-gradient-to-r from-indigo-50/80 to-purple-50/40 border-b border-indigo-100/50">
        <div className="min-w-0">
          <h4 className="text-sm font-semibold text-gray-800 truncate">{listing.title}</h4>
          <p className="text-xs text-gray-400 truncate">{listing.address}</p>
        </div>
        <button
          onClick={onCollapse}
          className="text-xs text-gray-400 hover:text-gray-600 cursor-pointer px-2.5 py-1.5 rounded-lg hover:bg-white/80 transition-all flex-shrink-0"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m5 15 7-7 7 7" />
          </svg>
        </button>
      </div>

      {/* Action Bar */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-gray-100 flex-wrap">
        {!isAtFinalStage && nextStageLabel && (
          <button
            onClick={onAdvance}
            className="text-xs font-medium px-3 py-1.5 rounded-lg bg-emerald-500 text-white hover:bg-emerald-600 transition-colors cursor-pointer"
          >
            Advance to {nextStageLabel}
          </button>
        )}
        <button
          onClick={handleArchive}
          disabled={archiving}
          className="text-xs font-medium px-3 py-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer"
        >
          {archiving ? "Archiving..." : "Archive"}
        </button>
        <a
          href={listing.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-indigo-500 hover:text-indigo-700 underline underline-offset-2 px-1"
        >
          View Listing
        </a>
        <a
          href={labUrl}
          className="text-xs text-indigo-500 hover:text-indigo-700 underline underline-offset-2 px-1"
        >
          Open in Lab
        </a>
      </div>

      {/* Content Sections */}
      <div className="px-4 py-4 space-y-4">
        <VisitNotesEditor listingId={listing.id} />
        <ObservationToggles
          listingId={listing.id}
          structuredData={structuredObservations}
          onUpdate={handleObservationUpdate}
        />
        <CostSummary listingId={listing.id} />
        <VisitPhotoGallery listingId={listing.id} />
      </div>

      {/* Stage Selector */}
      <div className="px-4 py-3 border-t border-gray-100 bg-gray-50/50 rounded-b-xl">
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500">Stage:</label>
          <select
            value={listing.stage}
            onChange={handleStageSelect}
            className="text-xs rounded-lg border border-gray-200 px-2 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-300 cursor-pointer"
          >
            {STAGE_ORDER.map((stage) => (
              <option key={stage} value={stage}>
                {STAGE_LABELS[stage]}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  )
}
