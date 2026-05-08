/**
 * PreferenceToggleCard — individual toggle card with impact stats.
 *
 * Shows a preference term with toggle switch, weight bar, and impact info
 * for disabled preferences (listings added, rent saved).
 */

interface PreferenceImpact {
  term: string
  enabled: boolean
  listings_added: number
  rent_saved: number
}

interface PreferenceToggleCardProps {
  term: string
  weight: number
  isEnabled: boolean
  impact: PreferenceImpact | null
  onToggle: (term: string) => void
}

export default function PreferenceToggleCard({
  term,
  weight,
  isEnabled,
  impact,
  onToggle,
}: PreferenceToggleCardProps) {
  return (
    <button
      onClick={() => onToggle(term)}
      className={`w-full text-left rounded-xl border p-3 transition-all ${
        isEnabled
          ? "border-indigo-200 bg-indigo-50/50"
          : "border-gray-200 bg-gray-50/50"
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {/* Toggle indicator */}
          <div
            className={`w-8 h-5 rounded-full transition-colors flex items-center ${
              isEnabled ? "bg-indigo-500 justify-end" : "bg-gray-300 justify-start"
            }`}
          >
            <div className="w-4 h-4 rounded-full bg-white mx-0.5 shadow-sm" />
          </div>
          <span className={`text-sm font-medium ${isEnabled ? "text-gray-800" : "text-gray-500"}`}>
            {term}
          </span>
        </div>
        {/* Weight bar */}
        <div className="flex items-center gap-2">
          <div className="w-16 h-1.5 rounded-full bg-gray-200 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                isEnabled ? "bg-indigo-400" : "bg-gray-300"
              }`}
              style={{ width: `${Math.min(100, (weight / 5) * 100)}%` }}
            />
          </div>
        </div>
      </div>

      {/* Impact info for disabled preferences */}
      {!isEnabled && impact && (impact.listings_added > 0 || impact.rent_saved > 0) && (
        <p className="mt-1.5 text-xs text-gray-500 ml-10">
          Turning this off adds {impact.listings_added} listing{impact.listings_added !== 1 ? "s" : ""}
          {impact.rent_saved > 0 && `, saves $${impact.rent_saved.toLocaleString()}/mo`}
        </p>
      )}
    </button>
  )
}
