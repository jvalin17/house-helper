import { useState } from "react"

interface Props {
  score: number | null | undefined
  breakdown?: {
    matched_learned?: Record<string, number>
    matched_search?: string[]
    term_count?: number
  }
  size?: "sm" | "md"
}

export default function RankingBadge({ score, breakdown, size = "sm" }: Props) {
  const [showTooltip, setShowTooltip] = useState(false)

  if (score == null) return null

  const badgeColor = score >= 75
    ? "bg-emerald-100 text-emerald-700 border-emerald-200"
    : score >= 50
      ? "bg-amber-100 text-amber-700 border-amber-200"
      : "bg-gray-100 text-gray-500 border-gray-200"

  const sizeClasses = size === "md"
    ? "text-xs px-2 py-1"
    : "text-[10px] px-1.5 py-0.5"

  const learnedTerms = breakdown?.matched_learned || {}
  const searchTerms = breakdown?.matched_search || []
  const hasBreakdown = Object.keys(learnedTerms).length > 0 || searchTerms.length > 0

  return (
    <div className="relative inline-block">
      <span
        className={`rounded-full border font-semibold cursor-default ${badgeColor} ${sizeClasses}`}
        tabIndex={hasBreakdown ? 0 : undefined}
        role={hasBreakdown ? "button" : undefined}
        aria-label={`Ranking score ${score}`}
        aria-describedby={showTooltip ? "ranking-tooltip" : undefined}
        onMouseEnter={() => hasBreakdown && setShowTooltip(true)}
        onMouseLeave={() => setShowTooltip(false)}
        onFocus={() => hasBreakdown && setShowTooltip(true)}
        onBlur={() => setShowTooltip(false)}
      >
        {score}
      </span>

      {showTooltip && hasBreakdown && (
        <div id="ranking-tooltip" role="tooltip" className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-1.5 w-52 p-2.5 rounded-lg bg-white border border-gray-200 shadow-lg text-left">
          <p className="text-[10px] text-gray-400 uppercase font-medium mb-1.5">Ranking breakdown</p>

          {Object.keys(learnedTerms).length > 0 && (
            <div className="mb-1.5">
              <p className="text-[9px] text-gray-400 mb-0.5">Learned preferences:</p>
              <div className="flex flex-wrap gap-1">
                {Object.entries(learnedTerms)
                  .sort(([, weightA], [, weightB]) => weightB - weightA)
                  .slice(0, 6)
                  .map(([term, weight]) => (
                    <span key={term} className={`text-[9px] px-1 py-0.5 rounded ${
                      weight > 0 ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-500"
                    }`}>
                      {term} {weight > 0 ? "+" : ""}{weight.toFixed(1)}
                    </span>
                  ))}
              </div>
            </div>
          )}

          {searchTerms.length > 0 && (
            <div>
              <p className="text-[9px] text-gray-400 mb-0.5">Matched search:</p>
              <div className="flex flex-wrap gap-1">
                {searchTerms.slice(0, 5).map(term => (
                  <span key={term} className="text-[9px] px-1 py-0.5 rounded bg-blue-50 text-blue-600">
                    {term}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
