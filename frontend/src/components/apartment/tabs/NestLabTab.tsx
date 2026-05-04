import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { api } from "@/api/client"

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

  // Lab analysis state
  const [labData, setLabData] = useState<Record<string, unknown> | null>(null)
  const [analysisText, setAnalysisText] = useState("")
  const [analysisProgress, setAnalysisProgress] = useState("")
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysisComplete, setAnalysisComplete] = useState(false)
  const [structuredAnalysis, setStructuredAnalysis] = useState<LabAnalysis | null>(null)

  useEffect(() => { loadNestedListings() }, [])

  const loadNestedListings = async () => {
    try {
      const data = await api.listApartments(true)
      setNestedListings(Array.isArray(data) ? data : [])
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

        {/* Nested listings */}
        <div>
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-3">
            Your nested listings ({nestedListings.length})
          </h3>
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
              {nestedListings.map((listing) => (
                <button
                  key={listing.id}
                  onClick={() => handleSelectListing(listing.id)}
                  className="flex items-start gap-4 p-4 rounded-xl bg-white border shadow-sm hover:shadow-md hover:border-purple-300 transition-all text-left"
                >
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
                    <h4 className="font-medium text-sm text-gray-800 truncate">{listing.title}</h4>
                    <p className="text-xs text-gray-400 truncate mt-0.5">{listing.address}</p>
                    <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                      {listing.price != null && <span className="font-semibold text-gray-700">${listing.price.toLocaleString()}/mo</span>}
                      {listing.bedrooms != null && <span>{listing.bedrooms === 0 ? "Studio" : `${listing.bedrooms}BR`}</span>}
                      {listing.bathrooms != null && <span>{listing.bathrooms}BA</span>}
                    </div>
                  </div>
                  {/* Arrow */}
                  <span className="text-gray-300 text-lg mt-2">→</span>
                </button>
              ))}
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
      {/* Back button + title */}
      <div className="flex items-center gap-3 mb-4">
        <button onClick={handleBackToPicker}
          className="text-sm text-gray-400 hover:text-purple-600 transition-colors">
          ← All listings
        </button>
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
                className="h-64 rounded-lg object-cover flex-shrink-0"
                loading="lazy"
              />
            ))}
          </div>
          {images.length > 8 && (
            <div className="absolute bottom-4 right-2 bg-black/60 text-white text-xs px-3 py-1 rounded-full">
              +{images.length - 8} more photos
            </div>
          )}
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

            {/* Red flags + green lights */}
            <div className="grid grid-cols-2 gap-4">
              {structuredAnalysis.green_lights && structuredAnalysis.green_lights.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-green-600 mb-1.5">Strengths</p>
                  {structuredAnalysis.green_lights.map((item, index) => (
                    <p key={index} className="text-xs text-gray-600 py-0.5">✓ {item}</p>
                  ))}
                </div>
              )}
              {structuredAnalysis.red_flags && structuredAnalysis.red_flags.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-red-600 mb-1.5">Concerns</p>
                  {structuredAnalysis.red_flags.map((item, index) => (
                    <p key={index} className="text-xs text-gray-600 py-0.5">✗ {item}</p>
                  ))}
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
            <p className="text-[10px] text-gray-400">Tap to set preference</p>
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
                    const saved = await api.saveListingCost(selectedListingId, costData)
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
          <div className="space-y-3 mb-4 max-h-64 overflow-y-auto">
            {qaHistory.map((entry, index) => (
              <div key={index} className="space-y-1">
                <p className="text-xs font-medium text-gray-700">You: {entry.question}</p>
                <p className="text-xs text-gray-500 bg-gray-50 rounded-lg p-2 leading-relaxed">{entry.answer}</p>
              </div>
            ))}
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
