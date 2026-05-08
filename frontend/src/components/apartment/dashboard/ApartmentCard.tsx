/**
 * ApartmentCard — compact listing card for the dashboard grid.
 *
 * Shows thumbnail, title, address, effective monthly price, score ring,
 * stage badge, and photo count. Expands inline when clicked.
 */

import ScoreRing from "@/components/apartment/dashboard/ScoreRing"
import type { DashboardListing } from "@/types"

const STAGE_LABELS: Record<string, string> = {
  interested: "Interested",
  visited: "Visited",
  applied: "Applied",
  approved: "Approved",
  moved_in: "Moved In",
}

const STAGE_BADGE_COLORS: Record<string, string> = {
  interested: "bg-indigo-50 text-indigo-700",
  visited: "bg-purple-50 text-purple-700",
  applied: "bg-amber-50 text-amber-700",
  approved: "bg-emerald-50 text-emerald-700",
  moved_in: "bg-green-50 text-green-700",
}

interface ApartmentCardProps {
  listing: DashboardListing
  onExpand: () => void
}

export default function ApartmentCard({ listing, onExpand }: ApartmentCardProps) {
  const badgeColor = STAGE_BADGE_COLORS[listing.stage] ?? STAGE_BADGE_COLORS.interested

  return (
    <button
      onClick={onExpand}
      className="w-full text-left rounded-xl bg-white border border-gray-200/80 shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200 overflow-hidden group cursor-pointer"
    >
      <div className="flex items-stretch">
        {/* Thumbnail */}
        <div className="w-24 min-h-[88px] flex-shrink-0 bg-gray-100 relative overflow-hidden">
          {listing.image_url ? (
            <img
              src={listing.image_url}
              alt={listing.title}
              className="w-full h-full object-cover"
              loading="lazy"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <svg className="w-8 h-8 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 12l8.954-8.955a1.126 1.126 0 011.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
              </svg>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0 p-3 flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-semibold text-gray-800 truncate">{listing.title}</h4>
            <p className="text-xs text-gray-400 truncate mt-0.5">{listing.address}</p>

            <div className="flex items-center gap-2 mt-2 flex-wrap">
              {listing.effective_monthly != null && (
                <span className="text-sm font-semibold text-indigo-600 font-mono">
                  ${Math.round(listing.effective_monthly).toLocaleString()}/mo
                </span>
              )}
              <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${badgeColor}`}>
                {STAGE_LABELS[listing.stage] ?? listing.stage}
              </span>
              {listing.photo_count > 0 && (
                <span className="text-[10px] text-gray-400">
                  {listing.photo_count} photo{listing.photo_count !== 1 ? "s" : ""}
                </span>
              )}
            </div>
          </div>

          {/* Score ring + expand chevron */}
          <div className="flex flex-col items-center gap-1.5 flex-shrink-0">
            {listing.match_score != null && (
              <ScoreRing score={listing.match_score} size={44} strokeWidth={3} />
            )}
            <svg
              className="w-4 h-4 text-gray-300 group-hover:text-indigo-400 transition-colors"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="m19 9-7 7-7-7" />
            </svg>
          </div>
        </div>
      </div>
    </button>
  )
}
