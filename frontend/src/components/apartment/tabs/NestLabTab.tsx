import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { api } from "@/api/client"

import ImageLightbox from "@/components/apartment/lab/ImageLightbox"
import CompareView from "@/components/apartment/lab/CompareView"
import HeroGallery from "@/components/apartment/lab/HeroGallery"
import KeyFactsBar from "@/components/apartment/lab/KeyFactsBar"
import FeatureTagsSection from "@/components/apartment/lab/FeatureTagsSection"
import PriceIntelligence from "@/components/apartment/lab/PriceIntelligence"
import CostCalculator from "@/components/apartment/lab/CostCalculator"
import AiQaBar from "@/components/apartment/lab/AiQaBar"

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

  // Q&A state
  const [qaHistory, setQaHistory] = useState<Array<{ question: string; answer: string }>>([])

  // Neighborhood enrichment state
  const [neighborhoodData, setNeighborhoodData] = useState<Record<string, unknown> | null>(null)
  const [neighborhoodLoading, setNeighborhoodLoading] = useState(false)

  // Cost calculator state
  const [costData, setCostData] = useState<Record<string, number | string>>({})
  const [priceContext, setPriceContext] = useState<{
    listing_price: number; area_median: number | null;
    percentile: number | null; comparable_count: number;
    price_vs_median: number | null;
  } | null>(null)

  // Feature preferences
  const [localMustHaves, setLocalMustHaves] = useState<Set<string>>(new Set())
  const [localDealBreakers, setLocalDealBreakers] = useState<Set<string>>(new Set())

  // Compare & lightbox
  const [compareMode, setCompareMode] = useState(false)
  const [lightboxOpen, setLightboxOpen] = useState(false)
  const [lightboxIndex, setLightboxIndex] = useState(0)

  // Sync preferences from server
  useEffect(() => {
    if (labData) {
      setLocalMustHaves(new Set((labData.must_haves as string[]) || []))
      setLocalDealBreakers(new Set((labData.deal_breakers as string[]) || []))
    }
  }, [labData])

  // Reload nested listings when picker is visible
  useEffect(() => {
    if (!selectedListingId) loadNestedListings()
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
      await api.saveApartmentToShortlist(newListingId).catch(() => {})
      toast.success("Listing extracted and nested — opening in Lab")
      setPasteUrl("")
      await loadNestedListings()
      handleSelectListing(newListingId)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to extract listing")
    } finally { setIsPasting(false) }
  }

  const handleSelectListing = async (listingId: number) => {
    setSelectedListingId(listingId)
    setAnalysisText(""); setAnalysisProgress(""); setAnalysisComplete(false)
    setStructuredAnalysis(null); setNeighborhoodData(null)
    try {
      const data = await api.getLabData(listingId)
      setLabData(data)
      const analyses = data.analyses as Record<string, Record<string, unknown>> | undefined
      if (analyses?.overview) {
        setStructuredAnalysis({
          overview: analyses.overview.overview as string | undefined,
          price_verdict: analyses.overview.price_verdict as string | undefined,
          price_reasoning: analyses.overview.price_reasoning as string | undefined,
          neighborhood: analyses.overview.neighborhood as Record<string, unknown> | undefined,
          red_flags: analyses.overview.red_flags as string[] | undefined,
          green_lights: analyses.overview.green_lights as string[] | undefined,
          questions_to_ask: analyses.overview.questions_to_ask as string[] | undefined,
          match_score: analyses.overview.match_score as number | undefined,
          match_reasoning: analyses.overview.match_reasoning as string | undefined,
        })
        setAnalysisComplete(true)
      }
      const [costResult, priceResult, qaResult] = await Promise.all([
        api.getListingCost(listingId).catch(() => null),
        api.getPriceContext(listingId).catch(() => null),
        api.getQaHistory(listingId).catch(() => []),
      ])
      if (costResult) setCostData(costResult as Record<string, number | string>)
      if (priceResult) setPriceContext(priceResult)
      if (qaResult && Array.isArray(qaResult)) setQaHistory(qaResult)
    } catch { toast.error("Failed to load lab data") }
  }

  const handleRunAnalysis = () => {
    if (!selectedListingId) return
    setIsAnalyzing(true); setAnalysisText(""); setAnalysisProgress("Connecting...")
    setAnalysisComplete(false); setStructuredAnalysis(null)
    const eventSource = new EventSource(api.getLabStreamUrl(selectedListingId))
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === "progress") setAnalysisProgress(data.detail || data.status)
      if (data.type === "chunk") { setAnalysisProgress("Generating insights..."); setAnalysisText(previous => previous + data.text) }
      if (data.type === "done") {
        setIsAnalyzing(false); setAnalysisComplete(true)
        if (selectedListingId) setAnalyzedIds(previous => new Set([...previous, selectedListingId]))
        try {
          let fullText = data.full_text || ""
          if (fullText.startsWith("```")) fullText = fullText.replace(/^```json?\n?/, "").replace(/\n?```$/, "")
          const parsed = JSON.parse(fullText)
          setStructuredAnalysis(parsed); setAnalysisText("")
        } catch { /* keep raw text */ }
        eventSource.close()
      }
      if (data.type === "error") { setIsAnalyzing(false); setAnalysisProgress(""); toast.error(data.message); eventSource.close() }
    }
    eventSource.onerror = () => { setIsAnalyzing(false); setAnalysisProgress(""); eventSource.close() }
  }

  const handleFeatureTagClick = async (featureName: string, category: string = "general") => {
    const currentlyMustHave = localMustHaves.has(featureName)
    const currentlyDealBreaker = localDealBreakers.has(featureName)
    let nextPreference: string
    if (!currentlyMustHave && !currentlyDealBreaker) nextPreference = "must_have"
    else if (currentlyMustHave) nextPreference = "deal_breaker"
    else nextPreference = "neutral"

    const updatedMustHaves = new Set(localMustHaves)
    const updatedDealBreakers = new Set(localDealBreakers)
    updatedMustHaves.delete(featureName); updatedDealBreakers.delete(featureName)
    if (nextPreference === "must_have") updatedMustHaves.add(featureName)
    if (nextPreference === "deal_breaker") updatedDealBreakers.add(featureName)
    setLocalMustHaves(updatedMustHaves); setLocalDealBreakers(updatedDealBreakers)

    try {
      if (nextPreference === "neutral") await api.resetFeaturePreference(featureName)
      else await api.setFeaturePreference(featureName, category, nextPreference)
    } catch { toast.error("Failed to save preference") }
  }

  const handleDealBreakerToggle = (featureName: string) => {
    const isMarked = localDealBreakers.has(featureName)
    if (isMarked) {
      const updated = new Set(localDealBreakers); updated.delete(featureName); setLocalDealBreakers(updated)
      api.resetFeaturePreference(featureName).catch(() => {})
    } else {
      const updated = new Set(localDealBreakers); updated.add(featureName); setLocalDealBreakers(updated)
      const updatedMustHaves = new Set(localMustHaves); updatedMustHaves.delete(featureName); setLocalMustHaves(updatedMustHaves)
      api.setFeaturePreference(featureName, "insight", "deal_breaker").catch(() => {})
    }
  }

  const handleBackToPicker = () => {
    setSelectedListingId(null); setLabData(null); setAnalysisText("")
    setStructuredAnalysis(null); setAnalysisComplete(false)
    setCostData({}); setPriceContext(null); setQaHistory([]); setNeighborhoodData(null)
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
            <Input placeholder="Paste listing URL (Zillow, Apartments.com, etc.)"
              value={pasteUrl} onChange={(event) => setPasteUrl(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && handlePasteUrl()} />
            <Button className="bg-purple-600 hover:bg-purple-700 text-white px-6"
              onClick={handlePasteUrl} disabled={isPasting || !pasteUrl.trim()}>
              {isPasting ? "Extracting..." : "Analyze"}
            </Button>
          </div>
        </div>

        {/* Nested listings header */}
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">
            Your nested listings ({nestedListings.length})
          </h3>
          {nestedListings.length >= 2 && (
            <button onClick={() => setCompareMode(!compareMode)}
              className={`text-xs px-3 py-1.5 rounded-full font-medium transition-all ${
                compareMode ? "bg-purple-100 text-purple-700 ring-1 ring-purple-300" : "text-purple-600 hover:bg-purple-50 border border-purple-200"
              }`}>
              {compareMode ? "Cancel compare" : "⚖️ Compare"}
            </button>
          )}
        </div>

        {/* Compare view or regular listing grid */}
        {compareMode ? (
          <CompareView
            nestedListings={nestedListings}
            localMustHaves={localMustHaves}
            localDealBreakers={localDealBreakers}
            analyzedIds={analyzedIds}
            onSelectListing={handleSelectListing}
            onToggleMustHave={handleFeatureTagClick}
            onToggleDealBreaker={handleDealBreakerToggle}
          />
        ) : (
          <>
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
                  <button key={listing.id}
                    onClick={() => handleSelectListing(listing.id)}
                    className="flex items-start gap-4 p-4 rounded-xl bg-white border shadow-sm hover:shadow-md hover:border-purple-300 transition-all text-left">
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
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-purple-100 text-purple-600 font-medium flex-shrink-0">🔬 Analyzed</span>
                        )}
                      </div>
                      <p className="text-xs text-gray-400 truncate mt-0.5">{listing.address}</p>
                      <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
                        {listing.price != null && <span className="font-semibold text-gray-700">${listing.price.toLocaleString()}/mo</span>}
                        {listing.bedrooms != null && <span>{listing.bedrooms === 0 ? "Studio" : `${listing.bedrooms}BR`}</span>}
                        {listing.bathrooms != null && <span>{listing.bathrooms}BA</span>}
                      </div>
                    </div>
                    <div className="flex flex-col items-center gap-2 mt-1 flex-shrink-0">
                      <button onClick={(event) => { event.stopPropagation()
                        api.unsaveApartment(listing.id).then(() => {
                          setNestedListings(previous => previous.filter(prevListing => prevListing.id !== listing.id))
                          toast.success("Removed from nest")
                        }).catch(() => toast.error("Failed to unnest"))
                      }} className="text-[10px] px-2 py-1 rounded bg-gray-100 text-gray-500 hover:bg-red-50 hover:text-red-600 transition-colors border border-gray-200">
                        🪹 Unnest
                      </button>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    )
  }

  // ── Lab analysis view ────────────────────────────────────
  const listing = labData?.listing as Record<string, unknown> | undefined
  const images = (listing?.images as string[]) || selectedListing?.images || []
  const amenities = (listing?.amenities as string[]) || selectedListing?.amenities || []
  const listingTitle = (listing?.title as string) || selectedListing?.title || ""
  const listingAddress = (listing?.address as string) || selectedListing?.address || null
  const listingPrice = (listing?.price as number) ?? selectedListing?.price ?? null
  const listingBedrooms = (listing?.bedrooms as number) ?? selectedListing?.bedrooms ?? null
  const listingBathrooms = (listing?.bathrooms as number) ?? selectedListing?.bathrooms ?? null

  return (
    <div className="space-y-0">
      {/* Back + unnest */}
      <div className="flex items-center justify-between mb-4">
        <button onClick={handleBackToPicker} className="text-sm text-gray-400 hover:text-purple-600 transition-colors">← Nested listings</button>
        <button onClick={() => {
          api.unsaveApartment(selectedListingId).then(() => { toast.success("Removed from nest"); handleBackToPicker() }).catch(() => toast.error("Failed to unnest"))
        }} className="text-xs px-3 py-1.5 rounded-lg bg-gray-100 text-gray-500 hover:bg-red-50 hover:text-red-600 transition-colors border border-gray-200">
          🪹 Unnest
        </button>
      </div>

      <HeroGallery images={images} onPhotoClick={(index) => { setLightboxIndex(index); setLightboxOpen(true) }} />
      {lightboxOpen && <ImageLightbox images={images} initialIndex={lightboxIndex} onClose={() => setLightboxOpen(false)} />}
      <KeyFactsBar title={listingTitle} address={listingAddress} price={listingPrice} bedrooms={listingBedrooms} bathrooms={listingBathrooms} />

      {/* AI Analysis */}
      <div className="rounded-2xl bg-white border shadow-sm p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-purple-600 uppercase tracking-wider">AI Analysis</h3>
          {!isAnalyzing && !analysisComplete && (
            <Button size="sm" className="bg-purple-600 hover:bg-purple-700 text-white" onClick={handleRunAnalysis}>🔬 Analyze</Button>
          )}
          {isAnalyzing && <span className="text-xs text-gray-400 animate-pulse">{analysisProgress || "Analyzing..."}</span>}
        </div>

        {structuredAnalysis && (
          <div className="space-y-4">
            {structuredAnalysis.overview && <p className="text-sm text-gray-700 leading-relaxed">{structuredAnalysis.overview}</p>}
            {structuredAnalysis.price_verdict && (
              <div className="flex items-center gap-2">
                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                  structuredAnalysis.price_verdict === "below_market" ? "bg-green-100 text-green-700" :
                  structuredAnalysis.price_verdict === "overpriced" ? "bg-red-100 text-red-700" : "bg-yellow-100 text-yellow-700"
                }`}>{structuredAnalysis.price_verdict === "below_market" ? "Below Market ✓" : structuredAnalysis.price_verdict === "overpriced" ? "Overpriced ✗" : "Fair Price"}</span>
                {structuredAnalysis.price_reasoning && <span className="text-xs text-gray-500">{structuredAnalysis.price_reasoning}</span>}
              </div>
            )}
            {structuredAnalysis.match_score != null && (
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full flex items-center justify-center text-sm font-bold border-2 border-purple-200 text-purple-700 bg-purple-50">{structuredAnalysis.match_score}</div>
                <div>
                  <p className="text-xs font-medium text-gray-700">Match Score</p>
                  {structuredAnalysis.match_reasoning && <p className="text-xs text-gray-400">{structuredAnalysis.match_reasoning}</p>}
                </div>
              </div>
            )}
            {/* Strengths + Concerns */}
            <div className="grid grid-cols-2 gap-4">
              {structuredAnalysis.green_lights && structuredAnalysis.green_lights.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-green-600 mb-1.5">Strengths <span className="text-gray-400 font-normal">(click to mark)</span></p>
                  {structuredAnalysis.green_lights.map((item, index) => (
                    <button key={index} onClick={() => handleFeatureTagClick(item, "insight")}
                      className={`text-xs py-0.5 px-1 -ml-1 rounded transition-colors text-left block ${
                        localMustHaves.has(item) ? "bg-purple-100 text-purple-700" : "text-gray-600 hover:bg-green-50"
                      }`}>{localMustHaves.has(item) ? "✓ " : "＋ "}{item}</button>
                  ))}
                </div>
              )}
              {structuredAnalysis.red_flags && structuredAnalysis.red_flags.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-red-600 mb-1.5">Concerns <span className="text-gray-400 font-normal">(click to mark)</span></p>
                  {structuredAnalysis.red_flags.map((item, index) => (
                    <button key={index} onClick={() => handleDealBreakerToggle(item)}
                      className={`text-xs py-0.5 px-1 -ml-1 rounded transition-colors text-left block ${
                        localDealBreakers.has(item) ? "bg-red-100 text-red-700" : "text-gray-600 hover:bg-red-50"
                      }`}>{localDealBreakers.has(item) ? "✗ " : "⚑ "}{item}</button>
                  ))}
                </div>
              )}
            </div>
            {/* Neighborhood */}
            {structuredAnalysis.neighborhood && (
              <div className="border-t pt-4">
                <p className="text-xs font-medium text-purple-600 uppercase tracking-wider mb-2">Neighborhood</p>
                {(structuredAnalysis.neighborhood as Record<string, unknown>).summary && (
                  <p className="text-xs text-gray-600 mb-3">{(structuredAnalysis.neighborhood as Record<string, unknown>).summary as string}</p>
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
            {/* Get more info */}
            <div className="border-t pt-4">
              {neighborhoodData ? (
                <div className="space-y-2">
                  {(neighborhoodData.walk_scores as Record<string, unknown>) && (
                    <div className="flex gap-4">
                      {["walk_score", "transit_score", "bike_score"].map(scoreKey => {
                        const scoreValue = (neighborhoodData.walk_scores as Record<string, unknown>)?.[scoreKey] as number | null
                        const label = scoreKey.replace("_score", "")
                        return scoreValue != null ? (
                          <div key={scoreKey} className="text-center">
                            <div className={`text-lg font-bold ${scoreValue >= 70 ? "text-green-600" : scoreValue >= 40 ? "text-yellow-600" : "text-red-600"}`}>{scoreValue}</div>
                            <div className="text-[10px] text-gray-400 capitalize">{label}</div>
                          </div>
                        ) : null
                      })}
                    </div>
                  )}
                  {(neighborhoodData.airport_distance as Record<string, unknown>) && (
                    <p className="text-xs text-gray-600">✈️ Airport: {(neighborhoodData.airport_distance as Record<string, unknown>).airport_distance_text as string} ({(neighborhoodData.airport_distance as Record<string, unknown>).airport_drive_text as string} drive)</p>
                  )}
                  {neighborhoodData.sources_skipped && (neighborhoodData.sources_skipped as string[]).length > 0 && (
                    <p className="text-[10px] text-gray-400">Connect {(neighborhoodData.sources_skipped as string[]).join(", ")} in Settings for more data</p>
                  )}
                </div>
              ) : (
                <button onClick={async () => {
                  if (!selectedListingId) return; setNeighborhoodLoading(true)
                  try { setNeighborhoodData(await api.getLabNeighborhood(selectedListingId, true)) }
                  catch { toast.error("Failed to fetch neighborhood data") }
                  finally { setNeighborhoodLoading(false) }
                }} disabled={neighborhoodLoading} className="text-xs text-purple-600 hover:text-purple-800 font-medium">
                  {neighborhoodLoading ? "Fetching Walk Score, distances..." : "📍 Get live neighborhood data (Walk Score, airport distance)"}
                </button>
              )}
            </div>
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

        {!structuredAnalysis && isAnalyzing && (
          <div className="flex items-center gap-3 py-4">
            <div className="w-5 h-5 border-2 border-purple-300 border-t-purple-600 rounded-full animate-spin" />
            <span className="text-sm text-gray-500">{analysisProgress || "Analyzing..."}</span>
          </div>
        )}
        {!structuredAnalysis && !isAnalyzing && analysisText && !analysisText.trimStart().startsWith("{") && !analysisText.trimStart().startsWith("```") && (
          <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{analysisText}</div>
        )}
        {!structuredAnalysis && !analysisText && !isAnalyzing && (
          <p className="text-sm text-gray-400">Click "Analyze" to get AI-powered insights about this property.</p>
        )}
      </div>

      <FeatureTagsSection amenities={amenities} localMustHaves={localMustHaves} localDealBreakers={localDealBreakers} onTagClick={handleFeatureTagClick} />
      {priceContext && <PriceIntelligence priceContext={priceContext} />}
      <CostCalculator listingId={selectedListingId} costData={costData} setCostData={setCostData} />
      <AiQaBar listingId={selectedListingId} qaHistory={qaHistory} onQaUpdate={setQaHistory} />
    </div>
  )
}
