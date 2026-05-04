import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { api } from "@/api/client"
import { summarizeAnswer, shortenQuestion } from "@/utils/textSummarizer"

interface NestedListing {
  id: number
  title: string
  address: string | null
  price: number | null
  bedrooms: number | null
  bathrooms: number | null
  images: string[]
  amenities: string[]
}

interface LabAnalysis {
  overview?: string
  price_verdict?: string
  price_reasoning?: string
  neighborhood?: Record<string, unknown>
  red_flags?: string[]
  green_lights?: string[]
  questions_to_ask?: string[]
  match_score?: number
  match_reasoning?: string
}


export default function NestLabTab() {
  const [nestedListings, setNestedListings] = useState<NestedListing[]>([])
  const [selectedListingId, setSelectedListingId] = useState<number | null>(null)
  const [pasteUrl, setPasteUrl] = useState("")
  const [isPasting, setIsPasting] = useState(false)
  const [loading, setLoading] = useState(true)
  const [analyzedIds, setAnalyzedIds] = useState<Set<number>>(new Set())

  // Lab analysis state
  const [labData, setLabData] = useState<Record<string, unknown> | null>(null)
  const [analysisText, setAnalysisText] = useState("")
  const [analysisProgress, setAnalysisProgress] = useState("")
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisComplete, setAnalysisComplete] = useState(false)
  const [structuredAnalysis, setStructuredAnalysis] = useState<LabAnalysis | null>(null)

  // Reload nested listings every time the picker is visible (catches nests from Search tab)
  useEffect(() => {
    if (!selectedListingId) {
      loadNestedListings()
    }
  }, [selectedListingId])


  const loadNestedListings = async () => {
    try {
      const [listingsData, analyzedIdsData] = await Promise.all([
        api.listApartments(true),
        api.getAnalyzedListingIds(),
      ])
      setNestedListings(Array.isArray(listingsData) ? listingsData : [])
      setAnalyzedIds(new Set(Array.isArray(analyzedIdsData) ? analyzedIdsData : []))
    } catch { /* silent */ }
    finally { setLoading(false) }
  }

  const handlePasteUrl = async () => {
    if (!pasteUrl.trim()) return
    setIsPasting(true)
    try {
      const result = await api.createApartmentFromUrl(pasteUrl.trim())
      const newListingId = (result as { id: number }).id
      // Auto-nest the listing so it appears in Lab picker
      await api.saveApartmentToShortlist(newListingId).catch(() => {})
      toast.success("Listing extracted and nested — opening in Lab")
      setPasteUrl("")
      await loadNestedListings()
      handleSelectListing(newListingId)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to extract listing")
    } finally {
      setIsPasting(false)
    }
  }

  const handleSelectListing = async (listingId: number) => {
    setSelectedListingId(listingId)
    setAnalysisText("")
    setAnalysisProgress("")
    setAnalysisComplete(false)
    setStructuredAnalysis(null)

    // Load lab data (gathered, no LLM call)
    try {
      const data = await api.getLabData(listingId)
      setLabData(data)

      // If cached analysis exists, use it
      const analyses = data.analyses as Record<string, Record<string, unknown>> | undefined
      if (analyses?.overview) {
        const cachedOverview: LabAnalysis = {
          overview: analyses.overview.overview as string | undefined,
          price_verdict: analyses.overview.price_verdict as string | undefined,
          price_reasoning: analyses.overview.price_reasoning as string | undefined,
          neighborhood: analyses.overview.neighborhood as Record<string, unknown> | undefined,
          red_flags: analyses.overview.red_flags as string[] | undefined,
          green_lights: analyses.overview.green_lights as string[] | undefined,
          questions_to_ask: analyses.overview.questions_to_ask as string[] | undefined,
          match_score: analyses.overview.match_score as number | undefined,
          match_reasoning: analyses.overview.match_reasoning as string | undefined,
        }
        setStructuredAnalysis(cachedOverview)
        setAnalysisComplete(true)
      }
      // Load cost, price context, and Q&A history in parallel
      const [costResult, priceResult, qaResult] = await Promise.all([
        api.getListingCost(listingId).catch(() => null),
        api.getPriceContext(listingId).catch(() => null),
        api.getQaHistory(listingId).catch(() => []),
      ])
      if (costResult) setCostData(costResult as Record<string, number | string>)
      if (priceResult) setPriceContext(priceResult)
      if (qaResult && Array.isArray(qaResult)) setQaHistory(qaResult)
    } catch {
      toast.error("Failed to load lab data")
    }
  }

  const handleRunAnalysis = () => {
    if (!selectedListingId) return
    setIsAnalyzing(true)
    setAnalysisText("")
    setAnalysisProgress("Connecting...")
    setAnalysisComplete(false)
    setStructuredAnalysis(null)

    const streamUrl = api.getLabStreamUrl(selectedListingId)
    const eventSource = new EventSource(streamUrl)

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.type === "progress") {
        setAnalysisProgress(data.detail || data.status)
      }
      if (data.type === "chunk") {
        setAnalysisProgress("Generating insights...")
        setAnalysisText(previous => previous + data.text)
      }
      if (data.type === "done") {
        setIsAnalyzing(false)
        setAnalysisComplete(true)
        // Mark as analyzed for badge display
        if (selectedListingId) {
          setAnalyzedIds(previous => new Set([...previous, selectedListingId]))
        }
        // Try to parse structured result from full text
        try {
          let fullText = data.full_text || ""
          if (fullText.startsWith("```")) {
            fullText = fullText.replace(/^```json?\n?/, "").replace(/\n?```$/, "")
          }
          const parsed = JSON.parse(fullText)
          setStructuredAnalysis(parsed)
          setAnalysisText("")  // Clear raw text, show structured
        } catch {
          // Keep raw text if not parseable as JSON
        }
        eventSource.close()
      }
      if (data.type === "error") {
        setIsAnalyzing(false)
        setAnalysisProgress("")
        toast.error(data.message)
        eventSource.close()
      }
    }

    eventSource.onerror = () => {
      setIsAnalyzing(false)
      setAnalysisProgress("")
      eventSource.close()
    }
  }

  const handleAskQuestion = async () => {
    if (!selectedListingId || !qaInput.trim()) return
    setQaLoading(true)
    const questionText = qaInput.trim()
    setQaInput("")
    try {
      const result = await api.askAboutListing(selectedListingId, questionText)
      setQaHistory(previous => [...previous, { question: result.question, answer: result.answer }])
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to get answer")
      setQaInput(questionText) // Restore question on failure
    } finally {
      setQaLoading(false)
    }
  }

  const handleBackToPicker = () => {
    setSelectedListingId(null)
    setLabData(null)
    setAnalysisText("")
    setStructuredAnalysis(null)
    setAnalysisComplete(false)
    setCostData({})
    setPriceContext(null)
    setQaHistory([])
    setQaInput("")
  }

  // Compare state
  const [compareMode, setCompareMode] = useState(false)
  const [compareSelected, setCompareSelected] = useState<Set<number>>(new Set())
  const [compareResult, setCompareResult] = useState<{
    listings: Array<{
      listing: Record<string, unknown>; score: number;
      matched_must_haves: string[]; matched_deal_breakers: string[];
      analysis_summary: string | null; price_verdict: string | null;
    }>;
  } | null>(null)
  const [compareLoading, setCompareLoading] = useState(false)

  // Lightbox state
  const [lightboxOpen, setLightboxOpen] = useState(false)
  const [lightboxIndex, setLightboxIndex] = useState(0)

  // Q&A state
  const [qaHistory, setQaHistory] = useState<Array<{ question: string; answer: string }>>([])
  const [qaInput, setQaInput] = useState("")
  const [qaLoading, setQaLoading] = useState(false)

  // Cost calculator state
  const [costData, setCostData] = useState<Record<string, number | string>>({})
  const [priceContext, setPriceContext] = useState<{
    listing_price: number; area_median: number | null;
    percentile: number | null; comparable_count: number;
    price_vs_median: number | null;
  } | null>(null)
  const [costSaving, setCostSaving] = useState(false)

  // Track local preference state for instant UI feedback
  const [localMustHaves, setLocalMustHaves] = useState<Set<string>>(new Set())
  const [localDealBreakers, setLocalDealBreakers] = useState<Set<string>>(new Set())

  // Sync from server data when lab loads
  useEffect(() => {
    if (labData) {
      setLocalMustHaves(new Set((labData.must_haves as string[]) || []))
      setLocalDealBreakers(new Set((labData.deal_breakers as string[]) || []))
    }
  }, [labData])

  const handleFeatureTagClick = async (featureName: string, category: string = "general") => {
    const currentlyMustHave = localMustHaves.has(featureName)
    const currentlyDealBreaker = localDealBreakers.has(featureName)

    // Cycle: neutral → must_have → deal_breaker → neutral
    let nextPreference: string
    if (!currentlyMustHave && !currentlyDealBreaker) {
      nextPreference = "must_have"
    } else if (currentlyMustHave) {
      nextPreference = "deal_breaker"
    } else {
      nextPreference = "neutral"
    }

    // Instant UI update
    const updatedMustHaves = new Set(localMustHaves)
    const updatedDealBreakers = new Set(localDealBreakers)
    updatedMustHaves.delete(featureName)
    updatedDealBreakers.delete(featureName)
    if (nextPreference === "must_have") updatedMustHaves.add(featureName)
    if (nextPreference === "deal_breaker") updatedDealBreakers.add(featureName)
    setLocalMustHaves(updatedMustHaves)
    setLocalDealBreakers(updatedDealBreakers)

    // Persist to server
    try {
      if (nextPreference === "neutral") {
        await api.resetFeaturePreference(featureName)
      } else {
        await api.setFeaturePreference(featureName, category, nextPreference)
      }
    } catch {
      toast.error("Failed to save preference")
    }
  }

  // Auto-refresh comparison when selection changes (if results already showing)
  useEffect(() => {
    if (compareResult && compareSelected.size >= 2) {
      const selectedIds = Array.from(compareSelected)
      const resultIds = compareResult.listings.map(entry => (entry.listing as Record<string, unknown>).id as number)
      const selectionChanged = selectedIds.length !== resultIds.length || selectedIds.some(id => !resultIds.includes(id))
      if (selectionChanged) {
        setCompareLoading(true)
        api.compareListings(selectedIds)
          .then(result => setCompareResult(result))
          .catch(() => toast.error("Compare failed"))
          .finally(() => setCompareLoading(false))
      }
    }
  }, [compareSelected])

  const selectedListing = nestedListings.find(listing => listing.id === selectedListingId)

  // ── Listing picker view ─────────────────────────────────
  if (!selectedListingId) {
    return (
      <div className="space-y-6">
        {/* Paste URL */}
        <div className="rounded-2xl bg-white border shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-1">Analyze a listing</h2>
          <p className="text-xs text-gray-400 mb-4">Paste a URL or select a nested listing below</p>
          <div className="flex gap-2">
            <Input
              placeholder="Paste listing URL (Zillow, Apartments.com, etc.)"
              value={pasteUrl}
              onChange={(event) => setPasteUrl(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && handlePasteUrl()}
            />
            <Button
              className="bg-purple-600 hover:bg-purple-700 text-white px-6"
              onClick={handlePasteUrl}
              disabled={isPasting || !pasteUrl.trim()}
            >
              {isPasting ? "Extracting..." : "Analyze"}
            </Button>
          </div>
        </div>

        {/* Nested listings + Compare */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">
              Your nested listings ({nestedListings.length})
            </h3>
            {nestedListings.length >= 2 && (
              <button
                onClick={() => {
                  if (compareMode) {
                    setCompareMode(false)
                    setCompareSelected(new Set())
                    setCompareResult(null)
                  } else {
                    setCompareMode(true)
                  }
                }}
                className={`text-xs px-3 py-1.5 rounded-full font-medium transition-all ${
                  compareMode
                    ? "bg-purple-100 text-purple-700 ring-1 ring-purple-300"
                    : "text-purple-600 hover:bg-purple-50 border border-purple-200"
                }`}
              >
                {compareMode ? "Cancel compare" : "⚖️ Compare"}
              </button>
            )}
          </div>

          {/* Compare action bar */}
          {compareMode && compareSelected.size >= 2 && !compareResult && (
            <div className="mb-3 p-3 bg-purple-50 rounded-xl flex items-center justify-between">
              <span className="text-xs text-purple-700">{compareSelected.size} listings selected</span>
              <Button
                size="sm"
                className="bg-purple-600 hover:bg-purple-700 text-white"
                onClick={async () => {
                  setCompareLoading(true)
                  try {
                    const result = await api.compareListings(Array.from(compareSelected))
                    setCompareResult(result)
                  } catch { toast.error("Compare failed") }
                  finally { setCompareLoading(false) }
                }}
                disabled={compareLoading}
              >
                {compareLoading ? "Comparing..." : "Compare now"}
              </Button>
            </div>
          )}

          {/* Compare results */}
          {compareResult && (
            <div className="mb-6 rounded-2xl bg-white border shadow-sm p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-medium text-purple-600 uppercase tracking-wider">Comparison</h3>
                <button onClick={() => { setCompareResult(null); setCompareMode(false); setCompareSelected(new Set()) }}
                  className="text-xs px-3 py-1 rounded-lg bg-gray-100 text-gray-500 hover:bg-gray-200 border border-gray-200">Close</button>
              </div>
              <div className="grid gap-4" style={{ gridTemplateColumns: `repeat(${compareResult.listings.length}, 1fr)` }}>
                {compareResult.listings.map((entry) => {
                  const entryListing = entry.listing as Record<string, unknown>
                  const entryRedFlags = (entry as Record<string, unknown>).red_flags as string[] || []
                  const entryGreenLights = (entry as Record<string, unknown>).green_lights as string[] || []
                  const entryNeighborhood = (entry as Record<string, unknown>).neighborhood_summary as string | null
                  const entryQuestions = (entry as Record<string, unknown>).questions_to_ask as string[] || []
                  const isAnalyzed = (entry as Record<string, unknown>).is_analyzed as boolean

                  return (
                    <div key={entryListing.id as number} className="border rounded-2xl overflow-hidden">
                      {/* Header with score */}
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
                                  entry.price_verdict === "overpriced" ? "bg-red-100 text-red-700" :
                                  "bg-yellow-100 text-yellow-700"
                                }`}>
                                  {entry.price_verdict === "below_market" ? "Below Market" :
                                   entry.price_verdict === "overpriced" ? "Overpriced" : "Fair"}
                                </span>
                              )}
                              {isAnalyzed && (
                                <span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-100 text-purple-600 font-medium">🔬</span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Scrollable content — smartphone height */}
                      <div className="p-4 min-h-[60vh] max-h-[100vh] overflow-y-auto space-y-3 flex flex-col">
                        {/* Stats */}
                        <div className="flex gap-3 text-xs text-gray-500">
                          {entryListing.bedrooms != null && <span>🛏 {(entryListing.bedrooms as number) === 0 ? "Studio" : `${entryListing.bedrooms}BR`}</span>}
                          {entryListing.bathrooms != null && <span>🚿 {entryListing.bathrooms}BA</span>}
                          {entryListing.sqft != null && <span>📐 {(entryListing.sqft as number).toLocaleString()} sqft</span>}
                        </div>

                        {/* Strengths + Concerns — single line each, flex-1 to fill space */}
                        {entryGreenLights.length > 0 && (
                          <div className="flex-1">
                            <p className="text-xs text-green-600 font-medium">Strengths</p>
                            {entryGreenLights.map((item, index) => {
                              const shortItem = item.replace(/^(Has |Includes |Features |Offers )/i, "")
                              return (
                                <button key={`g${index}`}
                                  onClick={() => handleFeatureTagClick(item, "insight")}
                                  className={`text-sm block w-full text-left whitespace-nowrap overflow-hidden text-ellipsis py-0.5 ${
                                    localMustHaves.has(item) ? "text-purple-700 font-medium" : "text-gray-600 hover:text-green-700"
                                  }`}
                                >
                                  {localMustHaves.has(item) ? "✓ " : "＋ "}{shortItem}
                                </button>
                              )
                            })}
                          </div>
                        )}
                        {entryRedFlags.length > 0 && (
                          <div className="flex-1">
                            <p className="text-xs text-red-600 font-medium">Concerns</p>
                            {entryRedFlags.map((item, index) => {
                              const shortItem = item.replace(/^(No |Lacks |Missing |Limited )/i, "")
                              return (
                                <button key={`r${index}`}
                                  onClick={() => {
                                    const isMarked = localDealBreakers.has(item)
                                    if (isMarked) {
                                      const updated = new Set(localDealBreakers); updated.delete(item); setLocalDealBreakers(updated)
                                      api.resetFeaturePreference(item).catch(() => {})
                                    } else {
                                      const updated = new Set(localDealBreakers); updated.add(item); setLocalDealBreakers(updated)
                                      const updatedMh = new Set(localMustHaves); updatedMh.delete(item); setLocalMustHaves(updatedMh)
                                      api.setFeaturePreference(item, "insight", "deal_breaker").catch(() => {})
                                    }
                                  }}
                                  className={`text-sm block w-full text-left whitespace-nowrap overflow-hidden text-ellipsis py-0.5 ${
                                    localDealBreakers.has(item) ? "text-red-700 font-medium" : "text-gray-600 hover:text-red-600"
                                  }`}
                                >
                                  {localDealBreakers.has(item) ? "✗ " : "⚑ "}{shortItem}
                                </button>
                              )
                            })}
                          </div>
                        )}

                        {/* Preferences matched */}
                        {entry.matched_must_haves.length > 0 && (
                          <div>
                            {entry.matched_must_haves.map(feature => (
                              <p key={feature} className="text-sm text-purple-600 truncate py-0.5">✓ {feature}</p>
                            ))}
                          </div>
                        )}
                        {entry.matched_deal_breakers.length > 0 && (
                          <div>
                            {entry.matched_deal_breakers.map(feature => (
                              <p key={feature} className="text-sm text-red-600 truncate py-0.5">✗ {feature}</p>
                            ))}
                          </div>
                        )}

                        {/* Q&A — question as topic, answer summarized */}
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
                                    <p className="text-sm text-gray-700">
                                      <span className="font-medium">{topic}</span>
                                      {summary && <span className="text-gray-500"> — {summary}</span>}
                                    </p>
                                  </div>
                                )
                              })}
                            </div>
                          )
                        })()}

                        {!isAnalyzed && (
                          <p className="text-sm text-gray-400 italic">Not analyzed</p>
                        )}

                        {/* Open full analysis */}
                        <div className="pt-2 mt-auto border-t border-gray-100">
                          <button
                            onClick={() => {
                              setCompareResult(null)
                              setCompareMode(false)
                              setCompareSelected(new Set())
                              handleSelectListing(entryListing.id as number)
                            }}
                            className="text-sm text-purple-600 hover:text-purple-800 font-medium"
                          >
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
                    : "Run AI analysis and set feature preferences to get comparison scores"
                  }
                </p>
              )}
            </div>
          )}

          {loading ? (
            <p className="text-sm text-gray-400">Loading...</p>
          ) : nestedListings.length === 0 ? (
            <div className="text-center py-16">
              <div className="text-4xl mb-3">🪹</div>
              <p className="text-sm font-medium text-gray-500">No nested listings yet</p>
              <p className="text-xs text-gray-400 mt-1">Search for apartments and click 🪹 to nest them here</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {nestedListings.map((listing) => {
                const isSelectedForCompare = compareSelected.has(listing.id)
                return (
                  <button
                    key={listing.id}
                    onClick={() => {
                      if (compareMode) {
                        setCompareSelected(previous => {
                          const updated = new Set(previous)
                          if (updated.has(listing.id)) {
                            updated.delete(listing.id)
                          } else if (updated.size < 3) {
                            updated.add(listing.id)
                          } else {
                            toast.info("Maximum 3 listings for comparison")
                          }
                          return updated
                        })
                      } else {
                        handleSelectListing(listing.id)
                      }
                    }}
                    className={`flex items-start gap-4 p-4 rounded-xl bg-white border shadow-sm transition-all text-left ${
                      isSelectedForCompare
                        ? "ring-2 ring-purple-400 border-purple-300"
                        : "hover:shadow-md hover:border-purple-300"
                    }`}
                  >
                    {/* Compare checkbox */}
                    {compareMode && (
                      <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center flex-shrink-0 mt-2 ${
                        isSelectedForCompare ? "bg-purple-600 border-purple-600 text-white" : "border-gray-300"
                      }`}>
                        {isSelectedForCompare && <span className="text-[10px]">✓</span>}
                      </div>
                    )}
                    {/* Thumbnail */}
                    <div className="w-20 h-20 rounded-lg bg-gray-100 flex-shrink-0 overflow-hidden">
                      {listing.images?.[0] ? (
                        <img src={listing.images[0]} alt={listing.title}
                          className="w-full h-full object-cover" loading="lazy" />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          <span className="text-2xl text-gray-200">🏠</span>
                        </div>
                      )}
                    </div>
                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <h4 className="font-medium text-sm text-gray-800 truncate">{listing.title}</h4>
                        {analyzedIds.has(listing.id) && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-100 text-purple-600 font-medium flex-shrink-0">
                            🔬 Analyzed
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-400 truncate mt-0.5">{listing.address}</p>
                      <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                        {listing.price != null && <span className="font-semibold text-gray-700">${listing.price.toLocaleString()}/mo</span>}
                        {listing.bedrooms != null && <span>{listing.bedrooms === 0 ? "Studio" : `${listing.bedrooms}BR`}</span>}
                        {listing.bathrooms != null && <span>{listing.bathrooms}BA</span>}
                      </div>
                    </div>
                    {/* Unnest button */}
                    {!compareMode && (
                      <div className="flex flex-col items-center gap-2 mt-1 flex-shrink-0">
                        <button
                          onClick={(event) => {
                            event.stopPropagation()
                            api.unsaveApartment(listing.id).then(() => {
                              setNestedListings(previous => previous.filter(prevListing => prevListing.id !== listing.id))
                              toast.success("Removed from nest")
                            }).catch(() => toast.error("Failed to unnest"))
                          }}
                          className="text-[10px] px-2 py-1 rounded bg-gray-100 text-gray-500 hover:bg-red-50 hover:text-red-600 transition-colors border border-gray-200"
                        >
                          🪹 Unnest
                        </button>
                      </div>
                    )}
                  </button>
                )
              })}
            </div>
          )}
        </div>
      </div>
    )
  }

  // ── Lab analysis view ────────────────────────────────────
  const listing = labData?.listing as Record<string, unknown> | undefined
  const images = (listing?.images as string[]) || selectedListing?.images || []
  const analyses = labData?.analyses as Record<string, unknown> || {}
  const mustHaves = (labData?.must_haves as string[]) || []
  const dealBreakers = (labData?.deal_breakers as string[]) || []

  return (
    <div className="space-y-0">
      {/* Back button + unnest */}
      <div className="flex items-center justify-between mb-4">
        <button onClick={handleBackToPicker}
          className="text-sm text-gray-400 hover:text-purple-600 transition-colors">
          ← Nested listings
        </button>
        {selectedListingId && (
          <button
            onClick={() => {
              api.unsaveApartment(selectedListingId).then(() => {
                toast.success("Removed from nest")
                handleBackToPicker()
              }).catch(() => toast.error("Failed to unnest"))
            }}
            className="text-xs px-3 py-1.5 rounded-lg bg-gray-100 text-gray-500 hover:bg-red-50 hover:text-red-600 transition-colors border border-gray-200"
          >
            🪹 Unnest
          </button>
        )}
      </div>

      {/* Hero Gallery */}
      {images.length > 0 && (
        <div className="relative -mx-6 mb-6">
          <div className="flex gap-1 overflow-x-auto pb-2">
            {images.slice(0, 8).map((imageUrl, imageIndex) => (
              <img
                key={imageIndex}
                src={imageUrl}
                alt={`Photo ${imageIndex + 1}`}
                className="h-64 rounded-lg object-cover flex-shrink-0 cursor-pointer hover:opacity-90 transition-opacity"
                loading="lazy"
                onClick={() => { setLightboxIndex(imageIndex); setLightboxOpen(true) }}
              />
            ))}
          </div>
          {images.length > 8 && (
            <button
              onClick={() => { setLightboxIndex(0); setLightboxOpen(true) }}
              className="absolute bottom-4 right-2 bg-black/60 text-white text-xs px-3 py-1.5 rounded-full hover:bg-black/80 transition-colors cursor-pointer"
            >
              📷 View all {images.length} photos
            </button>
          )}
        </div>
      )}

      {/* Lightbox */}
      {lightboxOpen && images.length > 0 && (
        <div className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center"
          onClick={() => setLightboxOpen(false)}>
          {/* Close button */}
          <button
            onClick={() => setLightboxOpen(false)}
            className="absolute top-4 right-4 text-white/70 hover:text-white text-2xl z-10 w-10 h-10 flex items-center justify-center"
          >✕</button>

          {/* Counter */}
          <div className="absolute top-4 left-4 text-white/70 text-sm">
            {lightboxIndex + 1} / {images.length}
          </div>

          {/* Previous */}
          {lightboxIndex > 0 && (
            <button
              onClick={(event) => { event.stopPropagation(); setLightboxIndex(lightboxIndex - 1) }}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-white/70 hover:text-white text-3xl w-12 h-12 flex items-center justify-center rounded-full bg-black/30 hover:bg-black/50"
            >‹</button>
          )}

          {/* Image */}
          <img
            src={images[lightboxIndex]}
            alt={`Photo ${lightboxIndex + 1}`}
            className="max-h-[85vh] max-w-[90vw] object-contain rounded-lg"
            onClick={(event) => event.stopPropagation()}
          />

          {/* Next */}
          {lightboxIndex < images.length - 1 && (
            <button
              onClick={(event) => { event.stopPropagation(); setLightboxIndex(lightboxIndex + 1) }}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-white/70 hover:text-white text-3xl w-12 h-12 flex items-center justify-center rounded-full bg-black/30 hover:bg-black/50"
            >›</button>
          )}

          {/* Thumbnail strip */}
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-1 max-w-[80vw] overflow-x-auto px-2">
            {images.map((thumbnailUrl, thumbnailIndex) => (
              <img
                key={thumbnailIndex}
                src={thumbnailUrl}
                alt={`Thumb ${thumbnailIndex + 1}`}
                className={`h-12 w-16 object-cover rounded cursor-pointer flex-shrink-0 transition-all ${
                  thumbnailIndex === lightboxIndex ? "ring-2 ring-white opacity-100" : "opacity-50 hover:opacity-75"
                }`}
                onClick={(event) => { event.stopPropagation(); setLightboxIndex(thumbnailIndex) }}
              />
            ))}
          </div>
        </div>
      )}

      {/* Key Facts Bar */}
      <div className="sticky top-0 z-10 bg-white/95 backdrop-blur-sm border-b py-3 -mx-6 px-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-800">
              {(listing?.title as string) || selectedListing?.title}
            </h2>
            <p className="text-sm text-gray-400">
              {(listing?.address as string) || selectedListing?.address}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-right">
              {(listing?.price ?? selectedListing?.price) != null && (
                <span className="text-2xl font-bold text-gray-800">
                  ${((listing?.price as number) || selectedListing?.price || 0).toLocaleString()}
                  <span className="text-sm text-gray-400 font-normal">/mo</span>
                </span>
              )}
            </div>
            <div className="flex items-center gap-3 text-sm text-gray-500">
              {(listing?.bedrooms ?? selectedListing?.bedrooms) != null && (
                <span>🛏 {(listing?.bedrooms as number) === 0 ? "Studio" : `${listing?.bedrooms || selectedListing?.bedrooms}`}</span>
              )}
              {(listing?.bathrooms ?? selectedListing?.bathrooms) != null && (
                <span>🚿 {(listing?.bathrooms as number) || selectedListing?.bathrooms}</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* AI Overview Section */}
      <div className="rounded-2xl bg-white border shadow-sm p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-purple-600 uppercase tracking-wider">AI Analysis</h3>
          {!isAnalyzing && !analysisComplete && (
            <Button size="sm" className="bg-purple-600 hover:bg-purple-700 text-white"
              onClick={handleRunAnalysis}>
              🔬 Analyze
            </Button>
          )}
          {isAnalyzing && (
            <span className="text-xs text-gray-400 animate-pulse">{analysisProgress || "Analyzing..."}</span>
          )}
        </div>

        {/* Structured analysis result */}
        {structuredAnalysis && (
          <div className="space-y-4">
            {/* Overview */}
            {structuredAnalysis.overview && (
              <p className="text-sm text-gray-700 leading-relaxed">{structuredAnalysis.overview}</p>
            )}

            {/* Price verdict badge */}
            {structuredAnalysis.price_verdict && (
              <div className="flex items-center gap-2">
                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                  structuredAnalysis.price_verdict === "below_market" ? "bg-green-100 text-green-700" :
                  structuredAnalysis.price_verdict === "overpriced" ? "bg-red-100 text-red-700" :
                  "bg-yellow-100 text-yellow-700"
                }`}>
                  {structuredAnalysis.price_verdict === "below_market" ? "Below Market ✓" :
                   structuredAnalysis.price_verdict === "overpriced" ? "Overpriced ✗" :
                   "Fair Price"}
                </span>
                {structuredAnalysis.price_reasoning && (
                  <span className="text-xs text-gray-500">{structuredAnalysis.price_reasoning}</span>
                )}
              </div>
            )}

            {/* Match score */}
            {structuredAnalysis.match_score != null && (
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full flex items-center justify-center text-sm font-bold border-2
                  border-purple-200 text-purple-700 bg-purple-50">
                  {structuredAnalysis.match_score}
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-700">Match Score</p>
                  {structuredAnalysis.match_reasoning && (
                    <p className="text-xs text-gray-400">{structuredAnalysis.match_reasoning}</p>
                  )}
                </div>
              </div>
            )}

            {/* Red flags + green lights — clickable to save as preference */}
            <div className="grid grid-cols-2 gap-4">
              {structuredAnalysis.green_lights && structuredAnalysis.green_lights.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-green-600 mb-1.5">Strengths <span className="text-gray-400 font-normal">(click to mark as must-have)</span></p>
                  {structuredAnalysis.green_lights.map((item, index) => {
                    const isMarked = localMustHaves.has(item)
                    return (
                      <button
                        key={index}
                        onClick={() => handleFeatureTagClick(item, "insight")}
                        className={`text-xs py-0.5 px-1 -ml-1 rounded transition-colors text-left block ${
                          isMarked ? "bg-purple-100 text-purple-700" : "text-gray-600 hover:bg-green-50"
                        }`}
                      >
                        {isMarked ? "✓ " : "＋ "}{item}
                      </button>
                    )
                  })}
                </div>
              )}
              {structuredAnalysis.red_flags && structuredAnalysis.red_flags.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-red-600 mb-1.5">Concerns <span className="text-gray-400 font-normal">(click to mark as deal-breaker)</span></p>
                  {structuredAnalysis.red_flags.map((item, index) => {
                    const isMarked = localDealBreakers.has(item)
                    return (
                      <button
                        key={index}
                        onClick={() => {
                          // For red flags, toggle directly to deal_breaker (skip must_have)
                          const currentlyDealBreaker = localDealBreakers.has(item)
                          if (currentlyDealBreaker) {
                            // Reset
                            const updated = new Set(localDealBreakers)
                            updated.delete(item)
                            setLocalDealBreakers(updated)
                            api.resetFeaturePreference(item).catch(() => {})
                          } else {
                            // Set as deal-breaker
                            const updated = new Set(localDealBreakers)
                            updated.add(item)
                            setLocalDealBreakers(updated)
                            const updatedMustHaves = new Set(localMustHaves)
                            updatedMustHaves.delete(item)
                            setLocalMustHaves(updatedMustHaves)
                            api.setFeaturePreference(item, "insight", "deal_breaker").catch(() => {})
                          }
                        }}
                        className={`text-xs py-0.5 px-1 -ml-1 rounded transition-colors text-left block ${
                          isMarked ? "bg-red-100 text-red-700" : "text-gray-600 hover:bg-red-50"
                        }`}
                      >
                        {isMarked ? "✗ " : "⚑ "}{item}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Neighborhood intel */}
            {structuredAnalysis.neighborhood && (
              <div className="border-t pt-4">
                <p className="text-xs font-medium text-purple-600 uppercase tracking-wider mb-2">Neighborhood</p>
                {(structuredAnalysis.neighborhood as Record<string, unknown>).summary && (
                  <p className="text-xs text-gray-600 mb-3">
                    {(structuredAnalysis.neighborhood as Record<string, unknown>).summary as string}
                  </p>
                )}
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { key: "nearby_grocery", label: "Grocery", icon: "🛒" },
                    { key: "ethnic_grocery", label: "Specialty / Ethnic Grocery", icon: "🌍" },
                    { key: "farmers_markets", label: "Farmers Markets", icon: "🥬" },
                    { key: "nearby_restaurants", label: "Restaurants", icon: "🍽️" },
                    { key: "nearby_parks", label: "Parks & Recreation", icon: "🌳" },
                    { key: "weekend_activities", label: "Weekend Activities", icon: "🎯" },
                  ].map(({ key, label, icon }) => {
                    const items = (structuredAnalysis.neighborhood as Record<string, string[]>)?.[key]
                    if (!items || items.length === 0) return null
                    return (
                      <div key={key}>
                        <p className="text-[10px] text-gray-400 uppercase">{icon} {label}</p>
                        {items.slice(0, 4).map((item, index) => (
                          <p key={index} className="text-xs text-gray-600 truncate">{item}</p>
                        ))}
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* Questions to ask */}
            {structuredAnalysis.questions_to_ask && structuredAnalysis.questions_to_ask.length > 0 && (
              <div className="border-t pt-4">
                <p className="text-xs font-medium text-purple-600 uppercase tracking-wider mb-2">Questions to ask on tour</p>
                {structuredAnalysis.questions_to_ask.map((question, index) => (
                  <p key={index} className="text-xs text-gray-600 py-0.5">• {question}</p>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Streaming indicator — don't show raw JSON */}
        {!structuredAnalysis && isAnalyzing && (
          <div className="flex items-center gap-3 py-4">
            <div className="w-5 h-5 border-2 border-purple-300 border-t-purple-600 rounded-full animate-spin" />
            <span className="text-sm text-gray-500">{analysisProgress || "Analyzing..."}</span>
          </div>
        )}

        {/* Show raw text only if it's NOT JSON (i.e., LLM returned prose, not structured) */}
        {!structuredAnalysis && !isAnalyzing && analysisText && !analysisText.trimStart().startsWith("{") && !analysisText.trimStart().startsWith("```") && (
          <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
            {analysisText}
          </div>
        )}

        {/* Empty state */}
        {!structuredAnalysis && !analysisText && !isAnalyzing && (
          <p className="text-sm text-gray-400">
            Click "Analyze" to get AI-powered insights about this property — price verdict, neighborhood intel, red flags, and questions to ask.
          </p>
        )}
      </div>

      {/* Feature tags — tap to cycle: neutral → must have → deal breaker */}
      {((listing?.amenities as string[]) || selectedListing?.amenities || []).length > 0 && (
        <div className="rounded-2xl bg-white border shadow-sm p-6 mb-6">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-purple-600 uppercase tracking-wider">Features</h3>
            <p className="text-[10px] text-gray-400">Click any feature below to mark as must-have or deal-breaker</p>
          </div>
          <div className="flex flex-wrap gap-2">
            {((listing?.amenities as string[]) || selectedListing?.amenities || []).map((amenity) => {
              const isMustHave = localMustHaves.has(amenity)
              const isDealBreaker = localDealBreakers.has(amenity)
              return (
                <button
                  key={amenity}
                  onClick={() => handleFeatureTagClick(amenity)}
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
              <span>
                <span className="inline-block w-2 h-2 rounded-full bg-purple-400 mr-1" />
                Must have ({localMustHaves.size})
              </span>
              <span>
                <span className="inline-block w-2 h-2 rounded-full bg-red-400 mr-1" />
                Deal breaker ({localDealBreakers.size})
              </span>
              <span>
                <span className="inline-block w-2 h-2 rounded-full bg-gray-300 mr-1" />
                Neutral (tap to cycle)
              </span>
            </div>
          )}
        </div>
      )}

      {/* Price Intelligence */}
      {priceContext && priceContext.area_median != null && (
        <div className="rounded-2xl bg-white border shadow-sm p-6 mb-6">
          <h3 className="text-sm font-medium text-purple-600 uppercase tracking-wider mb-4">Price Intelligence</h3>
          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="bg-gray-50 rounded-xl p-3 text-center">
              <p className="text-[10px] text-gray-400 uppercase">This listing</p>
              <p className="text-lg font-bold text-gray-800">${priceContext.listing_price.toLocaleString()}</p>
            </div>
            <div className="bg-gray-50 rounded-xl p-3 text-center">
              <p className="text-[10px] text-gray-400 uppercase">Area median</p>
              <p className="text-lg font-bold text-gray-800">${priceContext.area_median.toLocaleString()}</p>
            </div>
            <div className="bg-gray-50 rounded-xl p-3 text-center">
              <p className="text-[10px] text-gray-400 uppercase">Percentile</p>
              <p className="text-lg font-bold text-gray-800">{priceContext.percentile}th</p>
              <p className="text-[10px] text-gray-400">{priceContext.comparable_count} comparables</p>
            </div>
          </div>
          {/* Price bar — visual position */}
          <div className="relative h-3 bg-gray-100 rounded-full overflow-hidden mb-2">
            <div
              className="absolute h-full bg-purple-200 rounded-full"
              style={{ width: `${Math.min(priceContext.percentile || 0, 100)}%` }}
            />
            <div
              className="absolute h-full w-1 bg-purple-600 rounded-full"
              style={{ left: `${Math.min(priceContext.percentile || 0, 100)}%` }}
            />
          </div>
          <div className="flex justify-between text-[10px] text-gray-400">
            <span>Cheapest</span>
            <span>{(priceContext.price_vs_median || 0) < 0
              ? `$${Math.abs(priceContext.price_vs_median || 0).toLocaleString()} below median`
              : (priceContext.price_vs_median || 0) > 0
                ? `$${(priceContext.price_vs_median || 0).toLocaleString()} above median`
                : "At median"
            }</span>
            <span>Most expensive</span>
          </div>
        </div>
      )}

      {/* Cost Calculator */}
      {(() => {
        const baseRent = Number(costData.base_rent) || 0
        const parkingFee = Number(costData.parking_fee) || 0
        const petFee = Number(costData.pet_fee) || 0
        const utilitiesEstimate = Number(costData.utilities_estimate) || 0
        const leaseMonths = Number(costData.lease_months) || 12
        const specialDiscount = Number(costData.special_discount) || 0
        const effectiveRent = leaseMonths > 0 ? Math.round((baseRent * leaseMonths - specialDiscount) / leaseMonths) : baseRent
        const monthlyTotal = effectiveRent + parkingFee + petFee + utilitiesEstimate

        return (
          <div className="rounded-2xl bg-white border shadow-sm p-6 mb-6">
            <h3 className="text-sm font-medium text-purple-600 uppercase tracking-wider mb-4">Monthly Cost Calculator</h3>
            <div className="space-y-3">
              {/* Base rent — readonly if from listing, editable if $0 (URL paste) */}
              <div className="flex items-center justify-between">
                <label className="text-xs text-gray-600">Base rent</label>
                {baseRent > 0 ? (
                  <span className="text-sm font-medium text-gray-800">${baseRent.toLocaleString()}/mo</span>
                ) : (
                  <div className="relative">
                    <span className="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-gray-400">$</span>
                    <input
                      type="number"
                      className="w-24 pl-5 pr-2 py-1.5 text-sm text-right border rounded-lg bg-white"
                      placeholder="Enter rent"
                      value={costData.base_rent || ""}
                      onChange={(event) => setCostData(previous => ({
                        ...previous, base_rent: parseFloat(event.target.value) || 0,
                      }))}
                    />
                  </div>
                )}
              </div>

              {/* Editable fees */}
              {[
                { key: "parking_fee", label: "Parking" },
                { key: "pet_fee", label: "Pet fee" },
                { key: "utilities_estimate", label: "Utilities (est.)" },
              ].map(({ key, label }) => (
                <div key={key} className="flex items-center justify-between">
                  <label className="text-xs text-gray-600">{label}</label>
                  <div className="relative">
                    <span className="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-gray-400">$</span>
                    <input
                      type="number"
                      className="w-24 pl-5 pr-2 py-1.5 text-sm text-right border rounded-lg bg-white"
                      value={costData[key] || ""}
                      placeholder="0"
                      onChange={(event) => setCostData(previous => ({
                        ...previous, [key]: parseFloat(event.target.value) || 0,
                      }))}
                    />
                  </div>
                </div>
              ))}

              {/* Concession — quick select */}
              <div className="pt-2 border-t border-gray-100">
                <p className="text-xs text-gray-600 mb-2">Move-in special</p>
                <div className="flex flex-wrap gap-1.5">
                  {[
                    { label: "None", months: 0 },
                    { label: "1 month free", months: 1 },
                    { label: "2 months free", months: 2 },
                    { label: "3 months free", months: 3 },
                    { label: "Half month", months: 0.5 },
                  ].map(({ label, months }) => {
                    const discountAmount = Math.round(baseRent * months)
                    const isSelected = specialDiscount === discountAmount
                    return (
                      <button
                        key={label}
                        onClick={() => setCostData(previous => ({
                          ...previous,
                          special_discount: discountAmount,
                          special_description: months > 0 ? label : "",
                        }))}
                        className={`text-[11px] px-2.5 py-1 rounded-full transition-all border ${
                          isSelected
                            ? "bg-purple-100 text-purple-700 border-purple-300"
                            : "bg-gray-50 text-gray-500 border-gray-200 hover:border-purple-200"
                        }`}
                      >
                        {label}
                      </button>
                    )
                  })}
                </div>
                {/* Lease length */}
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-[11px] text-gray-400">Lease:</span>
                  {[12, 14, 15, 18].map((months) => (
                    <button
                      key={months}
                      onClick={() => setCostData(previous => ({ ...previous, lease_months: months }))}
                      className={`text-[11px] px-2 py-0.5 rounded transition-all ${
                        leaseMonths === months
                          ? "bg-purple-100 text-purple-700"
                          : "text-gray-400 hover:text-purple-600"
                      }`}
                    >
                      {months}mo
                    </button>
                  ))}
                </div>
              </div>

              {/* Effective rent if concession */}
              {specialDiscount > 0 && (
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-500">
                    Effective rent ({costData.special_description || "with discount"})
                  </span>
                  <span className="text-green-600 font-medium">${effectiveRent.toLocaleString()}/mo</span>
                </div>
              )}

              {/* Total */}
              <div className="flex items-center justify-between pt-3 border-t border-gray-200">
                <span className="text-sm font-semibold text-gray-800">Monthly total</span>
                <span className="text-lg font-bold text-purple-700">
                  ${monthlyTotal.toLocaleString()}/mo
                </span>
              </div>

              {/* Save */}
              <button
                onClick={async () => {
                  if (!selectedListingId) return
                  setCostSaving(true)
                  try {
                    const costPayload = {
                      base_rent: Number(costData.base_rent) || 0,
                      parking_fee: Number(costData.parking_fee) || 0,
                      pet_fee: Number(costData.pet_fee) || 0,
                      utilities_estimate: Number(costData.utilities_estimate) || 0,
                      lease_months: Number(costData.lease_months) || 12,
                      special_discount: Number(costData.special_discount) || 0,
                      special_description: costData.special_description || "",
                    }
                    const saved = await api.saveListingCost(selectedListingId, costPayload)
                    setCostData(saved as Record<string, number | string>)
                    toast.success("Cost breakdown saved")
                  } catch { toast.error("Failed to save") }
                  finally { setCostSaving(false) }
                }}
                className="text-xs text-purple-600 hover:text-purple-800 font-medium"
                disabled={costSaving}
              >
                {costSaving ? "Saving..." : "Save cost breakdown"}
              </button>
            </div>
          </div>
        )
      })()}

      {/* AI Q&A Bar */}
      <div className="rounded-2xl bg-white border shadow-sm p-6 mb-6">
        <h3 className="text-sm font-medium text-purple-600 uppercase tracking-wider mb-3">Ask about this property</h3>

        {/* Q&A History */}
        {qaHistory.length > 0 && (
          <div className="space-y-4 mb-4 max-h-96 overflow-y-auto">
            {qaHistory.map((entry, index) => (
              <div key={index}>
                <div className="flex items-start gap-2 mb-1.5">
                  <span className="w-5 h-5 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5">Q</span>
                  <p className="text-sm font-medium text-gray-800">{entry.question}</p>
                </div>
                <div className="ml-7 bg-gray-50 rounded-xl p-3 border border-gray-100">
                  <div className="text-sm text-gray-700 leading-relaxed [&_strong]:font-semibold [&_strong]:text-gray-800"
                    dangerouslySetInnerHTML={{
                      __html: entry.answer
                        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                        .replace(/^- (.+)$/gm, '{{BULLET}}$1{{/BULLET}}')
                        .replace(/\n*{{BULLET}}/g, '<div class="flex items-start gap-2 py-0.5 ml-1"><span class="w-1.5 h-1.5 rounded-full bg-purple-400 flex-shrink-0 mt-1.5"></span><span>')
                        .replace(/{{\/BULLET}}\n*/g, '</span></div>')
                        .replace(/\n\n/g, '<div class="h-2.5"></div>')
                        .replace(/\n/g, ' ')
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Quick insight buttons — always visible, dim ones already asked */}
        {!qaLoading && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {[
              "How far is the nearest Indian grocery store?",
              "Is this good for someone with a large dog?",
              "How is the commute to downtown?",
              "Are there good restaurants nearby?",
              "How safe is this neighborhood at night?",
              "Are there parks or playgrounds nearby?",
              "What are the schools like nearby?",
              "Is there a farmers market nearby?",
            ].map((suggestion) => {
              const alreadyAsked = qaHistory.some(entry => entry.question === suggestion)
              return (
                <button
                  key={suggestion}
                  onClick={() => { if (!alreadyAsked) setQaInput(suggestion) }}
                  className={`text-[11px] px-2.5 py-1 rounded-full transition-colors ${
                    alreadyAsked
                      ? "bg-gray-100 text-gray-400 cursor-default line-through"
                      : "bg-purple-50 text-purple-600 hover:bg-purple-100 cursor-pointer"
                  }`}
                >
                  {suggestion.length > 40 ? suggestion.slice(0, 40) + "..." : suggestion}
                </button>
              )
            })}
          </div>
        )}

        {/* Loading indicator */}
        {qaLoading && (
          <div className="flex items-center gap-3 py-3 mb-2">
            <div className="w-5 h-5 border-2 border-purple-300 border-t-purple-600 rounded-full animate-spin" />
            <span className="text-sm text-gray-500">Thinking about your question...</span>
          </div>
        )}

        {/* Input */}
        <div className="flex gap-2">
          <Input
            placeholder="Is this good for a dog owner? How far is the nearest Indian grocery?"
            value={qaInput}
            onChange={(event) => setQaInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && qaInput.trim() && !qaLoading) {
                event.preventDefault()
                handleAskQuestion()
              }
            }}
            disabled={qaLoading}
          />
          <Button
            className="bg-purple-600 hover:bg-purple-700 text-white px-4 flex-shrink-0"
            onClick={handleAskQuestion}
            disabled={qaLoading || !qaInput.trim()}
          >
            {qaLoading ? "..." : "Ask"}
          </Button>
        </div>
        {!qaLoading && qaHistory.length === 0 && (
          <p className="text-[10px] text-gray-400 mt-2">AI answers using listing data, analysis, and your preferences as context.</p>
        )}
      </div>
    </div>
  )
}
