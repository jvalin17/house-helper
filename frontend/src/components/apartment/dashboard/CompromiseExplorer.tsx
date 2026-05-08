/**
 * CompromiseExplorer — slide-over drawer for toggling search preferences
 * and seeing live matching counts + suggestions.
 *
 * Each preference can be toggled on/off. Disabled preferences show
 * impact stats ("adds X listings, saves $Y/mo"). Positive framing only.
 * Delegates individual toggle rendering to PreferenceToggleCard.
 */

import { useEffect, useState, useCallback } from "react"
import { api } from "@/api/client"
import type { SearchProfile, CompromiseResult } from "@/types"
import PreferenceToggleCard from "@/components/apartment/dashboard/PreferenceToggleCard"

interface CompromiseExplorerProps {
  profile: SearchProfile
  onClose: () => void
}

export default function CompromiseExplorer({
  profile,
  onClose,
}: CompromiseExplorerProps) {
  const preferences = profile.preferences ?? []

  const [enabledTerms, setEnabledTerms] = useState<Set<string>>(
    () => new Set(preferences.map((preference) => preference.term))
  )
  const [compromiseResult, setCompromiseResult] = useState<CompromiseResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const fetchCompromises = useCallback(async () => {
    setLoading(true)
    setErrorMessage(null)
    try {
      const enabledList = preferences
        .filter((preference) => enabledTerms.has(preference.term))
        .map((preference) => preference.term)
      const disabledList = preferences
        .filter((preference) => !enabledTerms.has(preference.term))
        .map((preference) => preference.term)

      const result = await api.exploreCompromises(enabledList, disabledList)
      setCompromiseResult(result)
    } catch {
      setErrorMessage("Failed to load compromise data. Please try again.")
    } finally {
      setLoading(false)
    }
  }, [enabledTerms, preferences])

  useEffect(() => {
    fetchCompromises()
  }, [fetchCompromises])

  const handleTogglePreference = (term: string) => {
    setEnabledTerms((previous) => {
      const updated = new Set(previous)
      if (updated.has(term)) {
        updated.delete(term)
      } else {
        updated.add(term)
      }
      return updated
    })
  }

  const getImpactForTerm = (term: string) => {
    if (!compromiseResult) return null
    return compromiseResult.per_preference_impact.find(
      (impact) => impact.term === term
    ) ?? null
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/20 transition-opacity"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="relative w-full max-w-md bg-white shadow-xl flex flex-col h-full overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b">
          <h2 className="text-base font-semibold text-gray-800">Compromise Explorer</h2>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
            aria-label="Close"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Live counter strip */}
        <div className="px-5 py-3 bg-indigo-50 border-b flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div>
              <span className="text-xs text-gray-500">Matching</span>
              <p className="text-lg font-bold text-indigo-700" data-testid="matching-count">
                {loading ? "--" : compromiseResult?.matching_count ?? 0}
              </p>
            </div>
            <div>
              <span className="text-xs text-gray-500">Avg Rent</span>
              <p className="text-lg font-bold text-gray-700">
                {loading ? "--" : compromiseResult?.average_rent
                  ? `$${compromiseResult.average_rent.toLocaleString()}/mo`
                  : "--"
                }
              </p>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          {/* Error state */}
          {errorMessage && (
            <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
              {errorMessage}
            </div>
          )}

          {/* Toggle cards */}
          <div className="space-y-2">
            <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider">
              Your Preferences
            </h3>
            {preferences.map((preference) => (
              <PreferenceToggleCard
                key={preference.term}
                term={preference.term}
                weight={preference.weight}
                isEnabled={enabledTerms.has(preference.term)}
                impact={getImpactForTerm(preference.term)}
                onToggle={handleTogglePreference}
              />
            ))}
          </div>

          {/* Suggestions */}
          {compromiseResult?.suggestions && compromiseResult.suggestions.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wider">
                Suggested Listings
              </h3>
              {compromiseResult.suggestions.map((suggestion) => (
                <div
                  key={suggestion.listing_id}
                  className="rounded-xl border border-emerald-200 bg-emerald-50/50 p-3"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-800">
                      {suggestion.title}
                    </span>
                    {suggestion.price !== null && (
                      <span className="text-sm font-semibold text-emerald-700">
                        ${suggestion.price.toLocaleString()}/mo
                      </span>
                    )}
                  </div>
                  {suggestion.match_score !== null && (
                    <p className="text-[11px] text-gray-500 mt-0.5">
                      Match: {suggestion.match_score}%
                    </p>
                  )}
                  {(suggestion.matching_preferences?.length ?? 0) > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {suggestion.matching_preferences.map((matchedTerm) => (
                        <span
                          key={matchedTerm}
                          className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-xs text-emerald-700"
                        >
                          {matchedTerm}
                        </span>
                      ))}
                    </div>
                  )}
                  {(suggestion.missing_preferences?.length ?? 0) > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {suggestion.missing_preferences.map((missingTerm) => (
                        <span
                          key={missingTerm}
                          className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-500 line-through"
                        >
                          {missingTerm}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Positive message */}
          {compromiseResult?.positive_message && (
            <div className="rounded-xl bg-amber-50 border border-amber-200 px-4 py-3">
              <p className="text-sm text-amber-800">{compromiseResult.positive_message}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
