/**
 * ObservationToggles — icon grid for quick visit observations.
 *
 * Each toggle represents a common apartment observation.
 * Active toggles are filled; inactive are outlined. Saves immediately on toggle.
 */

interface ObservationTogglesProps {
  listingId: number
  structuredData: Record<string, boolean> | null
  onUpdate: (updatedData: Record<string, boolean>) => void
}

const OBSERVATION_OPTIONS: Array<{ key: string; label: string; icon: string }> = [
  { key: "high_ceilings", label: "High ceilings", icon: "🏛️" },
  { key: "good_sunlight", label: "Good sunlight", icon: "☀️" },
  { key: "has_elevator", label: "Has elevator", icon: "🛗" },
  { key: "easy_parking", label: "Easy parking", icon: "🅿️" },
  { key: "pet_friendly", label: "Pet-friendly", icon: "🐾" },
  { key: "good_floor", label: "Good floor", icon: "🪵" },
  { key: "quiet", label: "Quiet", icon: "🤫" },
  { key: "clean", label: "Clean", icon: "✨" },
  { key: "spacious", label: "Spacious", icon: "📐" },
]

export default function ObservationToggles({ structuredData, onUpdate }: ObservationTogglesProps) {
  const currentObservations = structuredData ?? {}

  const handleToggle = (observationKey: string) => {
    const updatedObservations = {
      ...currentObservations,
      [observationKey]: !currentObservations[observationKey],
    }
    onUpdate(updatedObservations)
  }

  return (
    <div>
      <label className="text-xs font-medium text-gray-500 mb-1.5 block">Observations</label>
      <div className="grid grid-cols-3 gap-2">
        {OBSERVATION_OPTIONS.map((observation) => {
          const isActive = !!currentObservations[observation.key]
          return (
            <button
              key={observation.key}
              onClick={() => handleToggle(observation.key)}
              className={`flex items-center gap-1.5 px-2.5 py-2 rounded-lg text-xs font-medium transition-all duration-150 cursor-pointer ${
                isActive
                  ? "bg-indigo-50 border border-indigo-300 text-indigo-700 shadow-sm"
                  : "bg-white border border-gray-200 text-gray-500 hover:border-gray-300 hover:bg-gray-50"
              }`}
            >
              <span className="text-sm">{observation.icon}</span>
              <span className="truncate">{observation.label}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
