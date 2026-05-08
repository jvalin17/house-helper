/**
 * SearchProfileCard — displays the user's learned search preferences
 * with achievable/stretch classification and budget summary.
 *
 * Shown below the funnel when profile.ready === true.
 * Clicking "Explore Compromises" opens the CompromiseExplorer drawer.
 */

import type { SearchProfile } from "@/types"

interface SearchProfileCardProps {
  profile: SearchProfile
  onExploreCompromises: () => void
  onDismiss: () => void
}

export default function SearchProfileCard({
  profile,
  onExploreCompromises,
  onDismiss,
}: SearchProfileCardProps) {
  if (!profile.ready) {
    return null
  }

  const preferences = profile.preferences ?? []

  return (
    <div className="rounded-2xl bg-white border shadow-sm p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-semibold text-gray-800">Your Search Profile</h3>
          {profile.interaction_count && (
            <span className="inline-flex items-center rounded-full bg-indigo-50 px-2 py-0.5 text-xs font-medium text-indigo-600">
              {profile.interaction_count} interactions
            </span>
          )}
        </div>
        <button
          onClick={onDismiss}
          className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
          aria-label="Dismiss"
        >
          Dismiss
        </button>
      </div>

      {/* Preferences list */}
      <div className="flex flex-wrap gap-2">
        {preferences.map((preference) => (
          <div
            key={preference.term}
            data-preference={preference.term}
            className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-colors ${
              preference.achievable
                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                : "bg-amber-50 text-amber-700 border border-amber-200 border-dashed"
            }`}
          >
            {/* Achievable: filled circle, Stretch: outlined circle */}
            {preference.achievable ? (
              <svg className="w-3.5 h-3.5 text-emerald-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clipRule="evenodd" />
              </svg>
            ) : (
              <svg className="w-3.5 h-3.5 text-amber-500" fill="none" viewBox="0 0 20 20" stroke="currentColor" strokeWidth={1.5}>
                <circle cx="10" cy="10" r="7.5" />
              </svg>
            )}
            <span>{preference.term}</span>
            {preference.average_rent > 0 && (
              <span className="text-xs opacity-70">
                ${preference.average_rent.toLocaleString()}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Summary */}
      {profile.summary && (
        <p className="text-sm text-gray-600 bg-gray-50 rounded-lg px-3 py-2">
          {profile.summary}
        </p>
      )}

      {/* Explore Compromises button */}
      <button
        onClick={onExploreCompromises}
        className="w-full rounded-xl bg-indigo-50 text-indigo-700 font-medium text-sm py-2.5 hover:bg-indigo-100 transition-colors"
      >
        Explore Compromises
      </button>
    </div>
  )
}
