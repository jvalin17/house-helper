import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { api } from "@/api/client"
import { summarizeAnswer, shortenQuestion } from "@/utils/textSummarizer"

interface CompareEntry {
  listing: Record<string, unknown>
  score: number | null
  matched_must_haves: string[]
  matched_deal_breakers: string[]
  analysis_summary: string | null
  price_verdict: string | null
}

interface Props {
  nestedListings: Array<{ id: number; title: string; address: string | null; price: number | null; images: string[] }>
  localMustHaves: Set<string>
  localDealBreakers: Set<string>
  analyzedIds: Set<number>
  onSelectListing: (listingId: number) => void
  onToggleMustHave: (featureName: string, category: string) => void
  onToggleDealBreaker: (featureName: string) => void
}

export default function CompareView({
  nestedListings, localMustHaves, localDealBreakers, analyzedIds,
  onSelectListing, onToggleMustHave, onToggleDealBreaker,
}: Props) {
  const [compareSelected, setCompareSelected] = useState<Set<number>>(new Set())
  const [compareResult, setCompareResult] = useState<{
    listings: CompareEntry[]; must_haves: string[]; deal_breakers: string[];
  } | null>(null)
  const [compareLoading, setCompareLoading] = useState(false)

  const handleToggleSelection = (listingId: number) => {
    setCompareSelected(previous => {
      const updated = new Set(previous)
      if (updated.has(listingId)) {
        updated.delete(listingId)
      } else if (updated.size < 3) {
        updated.add(listingId)
      } else {
        toast.info("Maximum 3 listings for comparison")
      }
      return updated
    })
  }

  const handleRunComparison = async () => {
    setCompareLoading(true)
    try {
      const result = await api.compareListings(Array.from(compareSelected))
      setCompareResult(result)
    } catch { toast.error("Compare failed") }
    finally { setCompareLoading(false) }
  }

  const handleClose = () => {
    setCompareResult(null)
    setCompareSelected(new Set())
  }

  // Auto-refresh when selection changes
  if (compareResult && compareSelected.size >= 2) {
    const resultIds = compareResult.listings.map(entry => (entry.listing as Record<string, unknown>).id as number)
    const selectedIds = Array.from(compareSelected)
    const selectionChanged = selectedIds.length !== resultIds.length || selectedIds.some(selectedId => !resultIds.includes(selectedId))
    if (selectionChanged && !compareLoading) {
      setCompareLoading(true)
      api.compareListings(selectedIds)
        .then(result => setCompareResult(result))
        .catch(() => toast.error("Compare failed"))
        .finally(() => setCompareLoading(false))
    }
  }

  return (
    <div>
      {/* Compare action bar */}
      {compareSelected.size >= 2 && !compareResult && (
        <div className="mb-3 p-3 bg-purple-50 rounded-xl flex items-center justify-between">
          <span className="text-xs text-purple-700">{compareSelected.size} listings selected</span>
          <Button size="sm" className="bg-purple-600 hover:bg-purple-700 text-white"
            onClick={handleRunComparison} disabled={compareLoading}>
            {compareLoading ? "Comparing..." : "Compare now"}
          </Button>
        </div>
      )}

      {/* Compare results */}
      {compareResult && (
        <div className="mb-6 rounded-2xl bg-white border shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-purple-600 uppercase tracking-wider">Comparison</h3>
            <button onClick={handleClose}
              className="text-xs px-3 py-1 rounded-lg bg-gray-100 text-gray-500 hover:bg-gray-200 border border-gray-200">Close</button>
          </div>
          <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${compareResult.listings.length}, 1fr)` }}>
            {compareResult.listings.map((entry) => {
              const entryListing = entry.listing as Record<string, unknown>
              const entryRedFlags = (entry as Record<string, unknown>).red_flags as string[] || []
              const entryGreenLights = (entry as Record<string, unknown>).green_lights as string[] || []
              const isAnalyzed = (entry as Record<string, unknown>).is_analyzed as boolean

              return (
                <div key={entryListing.id as number} className="border rounded-2xl overflow-hidden">
                  {/* Header */}
                  <div className={`p-4 ${
                    entry.score == null ? "bg-gray-50" :
                    entry.score >= 75 ? "bg-green-50" :
                    entry.score >= 50 ? "bg-yellow-50" : "bg-red-50"
                  }`}>
                    <div className="flex items-center gap-3">
                      <div className={`w-14 h-14 rounded-xl flex items-center justify-center text-lg font-bold ${
                        entry.score == null ? "bg-white text-gray-400 border border-gray-200" :
                        entry.score >= 75 ? "bg-white text-green-700 border border-green-200" :
                        entry.score >= 50 ? "bg-white text-yellow-700 border border-yellow-200" :
                        "bg-white text-red-700 border border-red-200"
                      }`}>{entry.score != null ? entry.score : "—"}</div>
                      <div className="min-w-0">
                        <h4 className="text-sm font-semibold text-gray-800 truncate">{entryListing.title as string}</h4>
                        <p className="text-xs text-gray-500 truncate">{entryListing.address as string}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-sm font-bold text-gray-800">${((entryListing.price as number) || 0).toLocaleString()}/mo</span>
                          {entry.price_verdict && (
                            <span className={`text-[9px] px-1.5 py-0.5 rounded-full font-medium ${
                              entry.price_verdict === "below_market" ? "bg-green-100 text-green-700" :
                              entry.price_verdict === "overpriced" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"
                            }`}>
                              {entry.price_verdict === "below_market" ? "Below Market" :
                               entry.price_verdict === "overpriced" ? "Overpriced" : "Fair"}
                            </span>
                          )}
                          {isAnalyzed && <span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-100 text-purple-600 font-medium">🔬</span>}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Content */}
                  <div className="p-4 min-h-[60vh] max-h-[100vh] overflow-y-auto space-y-3 flex flex-col">
                    <div className="flex gap-3 text-xs text-gray-500">
                      {entryListing.bedrooms != null && <span>🛏 {(entryListing.bedrooms as number) === 0 ? "Studio" : `${entryListing.bedrooms}BR`}</span>}
                      {entryListing.bathrooms != null && <span>🚿 {entryListing.bathrooms}BA</span>}
                      {entryListing.sqft != null && <span>📐 {(entryListing.sqft as number).toLocaleString()} sqft</span>}
                    </div>

                    {/* Strengths */}
                    {entryGreenLights.length > 0 && (
                      <div className="flex-1">
                        <p className="text-xs text-green-600 font-medium">Strengths</p>
                        {entryGreenLights.map((item, index) => (
                          <button key={`g${index}`}
                            onClick={() => onToggleMustHave(item, "insight")}
                            className={`text-sm block w-full text-left whitespace-nowrap overflow-hidden text-ellipsis py-0.5 ${
                              localMustHaves.has(item) ? "text-purple-700 font-medium" : "text-gray-600 hover:text-green-700"
                            }`}>
                            {localMustHaves.has(item) ? "✓ " : "＋ "}{item.replace(/^(Has |Includes |Features |Offers )/i, "")}
                          </button>
                        ))}
                      </div>
                    )}

                    {/* Concerns */}
                    {entryRedFlags.length > 0 && (
                      <div className="flex-1">
                        <p className="text-xs text-red-600 font-medium">Concerns</p>
                        {entryRedFlags.map((item, index) => (
                          <button key={`r${index}`}
                            onClick={() => onToggleDealBreaker(item)}
                            className={`text-sm block w-full text-left whitespace-nowrap overflow-hidden text-ellipsis py-0.5 ${
                              localDealBreakers.has(item) ? "text-red-700 font-medium" : "text-gray-600 hover:text-red-600"
                            }`}>
                            {localDealBreakers.has(item) ? "✗ " : "⚑ "}{item.replace(/^(No |Lacks |Missing |Limited )/i, "")}
                          </button>
                        ))}
                      </div>
                    )}

                    {/* Preferences matched */}
                    {entry.matched_must_haves.length > 0 && (
                      <div>{entry.matched_must_haves.map(feature => (
                        <p key={feature} className="text-sm text-purple-600 truncate py-0.5">✓ {feature}</p>
                      ))}</div>
                    )}
                    {entry.matched_deal_breakers.length > 0 && (
                      <div>{entry.matched_deal_breakers.map(feature => (
                        <p key={feature} className="text-sm text-red-600 truncate py-0.5">✗ {feature}</p>
                      ))}</div>
                    )}

                    {/* Q&A */}
                    {(() => {
                      const qaSummary = (entry as Record<string, unknown>).qa_summary as Array<{ question: string; answer: string }> || []
                      if (qaSummary.length === 0) return null
                      return (
                        <div className="border-t border-gray-100 pt-2 flex-1">
                          <p className="text-xs text-purple-500 font-medium mb-1">You asked</p>
                          {qaSummary.map((qa, qaIndex) => {
                            const topic = shortenQuestion(qa.question)
                            const summary = summarizeAnswer(qa.answer)
                            return (
                              <div key={qaIndex} className="py-0.5">
                                <p className="text-sm font-medium text-gray-800">{topic}</p>
                                {summary && <p className="text-sm text-gray-500 leading-snug">{summary}</p>}
                              </div>
                            )
                          })}
                        </div>
                      )
                    })()}

                    {!isAnalyzed && <p className="text-sm text-gray-400 italic">Not analyzed</p>}

                    {/* Open in Lab */}
                    <div className="pt-2 mt-auto border-t border-gray-100">
                      <button onClick={() => { handleClose(); onSelectListing(entryListing.id as number) }}
                        className="text-sm text-purple-600 hover:text-purple-800 font-medium">
                        Open in Lab →
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
          {compareResult.listings.length >= 2 && (
            <p className="text-xs text-gray-400 mt-3 text-center">
              {compareResult.listings[0].score != null
                ? `Scores: ${compareResult.listings.map(entry => entry.score ?? "—").join(" vs ")} — based on AI analysis + your feature preferences`
                : "Run AI analysis and set feature preferences to get comparison scores"}
            </p>
          )}
        </div>
      )}

      {/* Listing selection grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {nestedListings.map((listing) => {
          const isSelectedForCompare = compareSelected.has(listing.id)
          return (
            <button key={listing.id}
              onClick={() => handleToggleSelection(listing.id)}
              className={`flex items-start gap-4 p-4 rounded-xl bg-white border shadow-sm transition-all text-left ${
                isSelectedForCompare ? "ring-2 ring-purple-400 border-purple-300" : "hover:shadow-md hover:border-purple-300"
              }`}>
              <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 mt-2 ${
                isSelectedForCompare ? "bg-purple-600 border-purple-600 text-white" : "border-gray-300"
              }`}>
                {isSelectedForCompare && <span className="text-[10px]">✓</span>}
              </div>
              <div className="w-20 h-20 rounded-lg bg-gray-100 flex-shrink-0 overflow-hidden">
                {listing.images?.[0] ? (
                  <img src={listing.images[0]} alt={listing.title} className="w-full h-full object-cover" loading="lazy" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center"><span className="text-2xl text-gray-200">🏠</span></div>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5">
                  <h4 className="font-medium text-sm text-gray-800 truncate">{listing.title}</h4>
                  {analyzedIds.has(listing.id) && (
                    <span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-100 text-purple-600 font-medium flex-shrink-0">🔬</span>
                  )}
                </div>
                <p className="text-xs text-gray-400 truncate mt-0.5">{listing.address}</p>
                <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                  {listing.price != null && <span className="font-semibold text-gray-700">${listing.price.toLocaleString()}/mo</span>}
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
