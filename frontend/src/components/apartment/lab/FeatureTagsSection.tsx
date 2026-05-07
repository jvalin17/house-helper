interface Props {
  amenities: string[]
  localMustHaves: Set<string>
  localDealBreakers: Set<string>
  onTagClick: (featureName: string, category: string) => void
}

export default function FeatureTagsSection({ amenities, localMustHaves, localDealBreakers, onTagClick }: Props) {
  if (amenities.length === 0) return null

  return (
    <div className="rounded-2xl bg-white border shadow-sm p-6 mb-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-purple-600 uppercase tracking-wider">Features</h3>
        <p className="text-[10px] text-gray-400">Click any feature below to mark as must-have or deal-breaker</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {amenities.map((amenity) => {
          const isMustHave = localMustHaves.has(amenity)
          const isDealBreaker = localDealBreakers.has(amenity)
          return (
            <button
              key={amenity}
              onClick={() => onTagClick(amenity, "general")}
              className={`text-xs px-3 py-1.5 rounded-full font-medium transition-all cursor-pointer ${
                isMustHave
                  ? "bg-purple-100 text-purple-700 ring-1 ring-purple-300 hover:bg-purple-200"
                  : isDealBreaker
                    ? "bg-red-100 text-red-700 ring-1 ring-red-300 hover:bg-red-200"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {isMustHave ? "✓ " : isDealBreaker ? "✗ " : ""}{amenity}
            </button>
          )
        })}
      </div>
      {(localMustHaves.size > 0 || localDealBreakers.size > 0) && (
        <div className="flex gap-4 mt-3 pt-3 border-t border-gray-100 text-[10px] text-gray-400">
          <span><span className="inline-block w-2 h-2 rounded-full bg-purple-400 mr-1" />Must have ({localMustHaves.size})</span>
          <span><span className="inline-block w-2 h-2 rounded-full bg-red-400 mr-1" />Deal breaker ({localDealBreakers.size})</span>
          <span><span className="inline-block w-2 h-2 rounded-full bg-gray-300 mr-1" />Neutral (tap to cycle)</span>
        </div>
      )}
    </div>
  )
}
