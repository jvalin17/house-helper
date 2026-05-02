import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { api } from "@/api/client"

interface ApartmentListing {
  id: number
  title: string
  address: string | null
  price: number | null
  bedrooms: number | null
  bathrooms: number | null
  sqft: number | null
  amenities: string[]
  images: string[]
  source_url: string | null
  is_saved: number
  parsed_data?: Record<string, unknown>
}

const AMENITY_OPTIONS = [
  { label: "Elevator", icon: "🛗" },
  { label: "Pool", icon: "🏊" },
  { label: "Gym", icon: "💪" },
  { label: "Parking", icon: "🅿️" },
  { label: "In-unit W/D", icon: "🧺" },
  { label: "Dishwasher", icon: "🍽️" },
  { label: "Balcony", icon: "🌇" },
  { label: "Pet Friendly", icon: "🐾" },
  { label: "Doorman", icon: "🚪" },
  { label: "Rooftop", icon: "🌆" },
  { label: "EV Charging", icon: "⚡" },
  { label: "Storage", icon: "📦" },
  { label: "Waterfront", icon: "🌊" },
  { label: "City View", icon: "🏙️" },
  { label: "Garden", icon: "🌿" },
  { label: "Concierge", icon: "🛎️" },
]

const BED_OPTIONS = ["Studio", "1", "2", "3", "4+"]

export default function NestSearchTab() {
  const [city, setCity] = useState("")
  const [zipCode, setZipCode] = useState("")
  const [selectedBeds, setSelectedBeds] = useState<Set<string>>(new Set())
  const [maxRent, setMaxRent] = useState("")
  const [selectedAmenities, setSelectedAmenities] = useState<Set<string>>(new Set())
  const [naturalLanguageQuery, setNaturalLanguageQuery] = useState("")
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [minBaths, setMinBaths] = useState("")
  const [minSqft, setMinSqft] = useState("")

  const [listings, setListings] = useState<ApartmentListing[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [flippedCardId, setFlippedCardId] = useState<number | null>(null)

  useEffect(() => { loadListings() }, [])

  const loadListings = async () => {
    try {
      const data = await api.listApartments()
      setListings(Array.isArray(data) ? data : [])
    } catch { /* silent */ }
  }

  const toggleAmenity = (amenity: string) => {
    setSelectedAmenities(previous => {
      const updated = new Set(previous)
      updated.has(amenity) ? updated.delete(amenity) : updated.add(amenity)
      return updated
    })
  }

  const handleSearch = async () => {
    setIsSearching(true)
    setVisibleCount(20)
    try {
      const searchResult = await api.searchApartments({
        query: naturalLanguageQuery || "",
        city: city || undefined,
        zip_code: zipCode || undefined,
        bedrooms: selectedBeds.size > 0 ? Array.from(selectedBeds).map(bed => bed === "Studio" ? 0 : bed === "4+" ? 4 : parseInt(bed)) : undefined,
        max_rent: maxRent ? parseFloat(maxRent) : undefined,
        min_bathrooms: minBaths ? parseInt(minBaths) : undefined,
        min_sqft: minSqft ? parseInt(minSqft) : undefined,
        amenities: selectedAmenities.size > 0 ? Array.from(selectedAmenities) : undefined,
      })
      const sourceNames = searchResult.sources?.join(", ") || ""
      const failedSources = searchResult.sources_failed || []

      if (searchResult.results?.length > 0) {
        const successMessage = `Found ${searchResult.results.length} apartments via ${sourceNames}`
        if (failedSources.length > 0) {
          toast.success(`${successMessage} (${failedSources.join(", ")} failed — still showing results from other sources)`)
        } else {
          toast.success(successMessage)
        }
      } else if (failedSources.length > 0) {
        toast.error(`${failedSources.join(", ")} failed. Check your API keys in Settings.`)
      } else {
        toast.info(searchResult.message || "No results. Check your API key in Settings.")
      }
      loadListings()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Search failed")
    } finally {
      setIsSearching(false)
    }
  }

  const [visibleCount, setVisibleCount] = useState(20)

  const handleShortlist = async (listingId: number) => {
    try {
      await api.saveApartmentToShortlist(listingId)
      setListings(previous => previous.map(listing =>
        listing.id === listingId ? { ...listing, is_saved: 1 } : listing
      ))
      toast.success("🪺 Nested! Find it in Dashboard")
    } catch { toast.error("Failed to save") }
  }

  const handleUnnest = async (listingId: number) => {
    try {
      await api.unsaveApartment(listingId)
      setListings(previous => previous.map(listing =>
        listing.id === listingId ? { ...listing, is_saved: 0 } : listing
      ))
      toast.success("Removed from nest")
    } catch { toast.error("Failed to unsave") }
  }

  const activeFilterCount = [city, zipCode, maxRent, minBaths, minSqft].filter(Boolean).length + selectedBeds.size + selectedAmenities.size

  return (
    <div className="space-y-6">
      {/* Search Panel */}
      <div className="rounded-2xl bg-white border shadow-sm p-6">
        <h2 className="text-lg font-semibold text-gray-800 mb-1">Where do you want to live?</h2>
        <p className="text-xs text-gray-400 mb-5">Find apartments across your connected sources</p>

        {/* Location + Budget */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-5">
          <Input placeholder="City (e.g., Dallas)" value={city}
            onChange={(event) => setCity(event.target.value)} />
          <Input placeholder="Zip code" value={zipCode}
            onChange={(event) => setZipCode(event.target.value)} />
          <div className="relative">
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">$</span>
            <Input placeholder="Max rent/mo" type="number" value={maxRent}
              onChange={(event) => setMaxRent(event.target.value)} className="pl-7" />
          </div>
        </div>

        {/* Bedrooms — multi select */}
        <div className="mb-5">
          <p className="text-xs text-gray-500 mb-2 font-medium uppercase tracking-wider">Bedrooms</p>
          <div className="flex gap-2">
            {BED_OPTIONS.map((option) => (
              <button
                key={option}
                onClick={() => {
                  setSelectedBeds(previous => {
                    const updated = new Set(previous)
                    updated.has(option) ? updated.delete(option) : updated.add(option)
                    return updated
                  })
                }}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all border ${
                  selectedBeds.has(option)
                    ? "bg-purple-600 text-white border-purple-600 shadow-sm"
                    : "bg-gray-50 text-gray-600 border-gray-200 hover:border-purple-300 hover:text-purple-600"
                }`}
              >
                {option === "Studio" ? "Studio" : `${option} BR`}
              </button>
            ))}
          </div>
        </div>

        {/* Amenities */}
        <div className="mb-5">
          <p className="text-xs text-gray-500 mb-2 font-medium uppercase tracking-wider">Must-haves</p>
          <div className="flex flex-wrap gap-2">
            {AMENITY_OPTIONS.map(({ label, icon }) => (
              <button
                key={label}
                onClick={() => toggleAmenity(label)}
                className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all flex items-center gap-1.5 border ${
                  selectedAmenities.has(label)
                    ? "bg-purple-600 text-white border-purple-600 shadow-sm"
                    : "bg-gray-50 text-gray-600 border-gray-200 hover:border-purple-300 hover:text-purple-600"
                }`}
              >
                <span>{icon}</span> {label}
              </button>
            ))}
          </div>
        </div>

        {/* Refine */}
        <div className="mt-5">
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-xs text-gray-400 hover:text-purple-600 transition-colors flex items-center gap-1.5 mb-3"
          >
            <span className="w-5 h-5 rounded-full border border-gray-300 flex items-center justify-center text-[10px]">
              {showAdvanced ? "−" : "+"}
            </span>
            {showAdvanced ? "Less options" : "Refine with AI, baths, sqft"}
          </button>

          {showAdvanced && (
            <div className="rounded-xl bg-gray-50/80 border border-gray-100 p-4 space-y-3 mb-4">
              <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Refine your search</p>
              <div className="grid grid-cols-2 gap-3">
                <Input placeholder="Min bathrooms" type="number" value={minBaths}
                  onChange={(event) => setMinBaths(event.target.value)} className="bg-white" />
                <Input placeholder="Min sqft" type="number" value={minSqft}
                  onChange={(event) => setMinSqft(event.target.value)} className="bg-white" />
              </div>
              <div>
                <p className="text-xs text-gray-400 mb-1.5">Describe your dream apartment</p>
                <Input
                  placeholder="e.g., quiet area, near Indian grocery, good sunlight, no shared walls"
                  value={naturalLanguageQuery}
                  onChange={(event) => setNaturalLanguageQuery(event.target.value)}
                  className="bg-white"
                />
              </div>
            </div>
          )}
        </div>

        {/* Search */}
        <div className="mt-4">
          <Button
            className="bg-orange-500 hover:bg-orange-600 text-white font-medium px-6 py-2.5 rounded-lg transition-all shadow-sm hover:shadow-md"
            onClick={handleSearch}
            disabled={isSearching || (!city && !zipCode && !naturalLanguageQuery)}
          >
            {isSearching ? "⏳ Searching..." : <><span className="mr-1.5">⚡</span>Search{activeFilterCount > 0 ? ` (${activeFilterCount})` : ""}</>}
          </Button>
        </div>
      </div>

      {/* ── Continuous Feed ── */}
      {listings.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-800 mb-4">{listings.length} apartments found</h3>
          <div className="space-y-4">
            {listings.slice(0, visibleCount).map((listing) => {
              const images = listing.images || []
              const firstImage = images[0]
              const matchedFeatures = listing.amenities?.filter(amenity => selectedAmenities.has(amenity)) || []
              const isFlipped = flippedCardId === listing.id
              const parsedData = listing.parsed_data || {}

              return (
                <div key={listing.id} className="rounded-xl bg-white border shadow-sm hover:shadow-md transition-all overflow-hidden">
                  {!isFlipped ? (
                    /* ── FRONT ── */
                    <div className="flex flex-col md:flex-row cursor-pointer" onClick={() => setFlippedCardId(listing.id)}>
                      {/* Image */}
                      <div className="md:w-72 h-48 md:h-auto bg-gray-100 relative flex-shrink-0 overflow-hidden">
                        {firstImage ? (
                          <img src={firstImage} alt={listing.title}
                            className="w-full h-full object-cover" loading="lazy" />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center min-h-[180px]">
                            <span className="text-5xl text-gray-200">🏠</span>
                          </div>
                        )}
                        {images.length > 1 && (
                          <div className="absolute bottom-2 left-2 bg-black/60 text-white text-[10px] px-2 py-0.5 rounded-full">
                            📷 {images.length} photos
                          </div>
                        )}
                        {/* Nest/unnest on image */}
                        <div className="absolute top-2 right-2" onClick={(event) => event.stopPropagation()}>
                          <button
                            onClick={() => listing.is_saved ? handleUnnest(listing.id) : handleShortlist(listing.id)}
                            className={`w-8 h-8 rounded-full flex items-center justify-center transition-all shadow-sm ${
                              listing.is_saved
                                ? "bg-purple-600 text-white hover:bg-purple-700"
                                : "bg-white/80 backdrop-blur-sm text-gray-400 hover:text-purple-600 hover:bg-white"
                            }`}
                          >
                            {listing.is_saved ? "🪺" : "🪹"}
                          </button>
                        </div>
                      </div>

                      {/* Content */}
                      <div className="flex-1 p-5 flex flex-col">
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <h4 className="font-semibold text-base text-gray-800 truncate">{listing.title}</h4>
                            {listing.address && (
                              <p className="text-sm text-gray-400 mt-0.5 truncate">{listing.address}</p>
                            )}
                          </div>
                          <div className="text-right ml-4 flex-shrink-0">
                            {listing.price != null && (
                              <div>
                                <span className="text-2xl font-bold text-gray-800">${listing.price.toLocaleString()}</span>
                                <span className="text-sm text-gray-400">/mo</span>
                              </div>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-6 mt-3 text-sm text-gray-500">
                          {listing.bedrooms != null && <span>🛏 {listing.bedrooms === 0 ? "Studio" : `${listing.bedrooms} bed`}</span>}
                          {listing.bathrooms != null && <span>🚿 {listing.bathrooms} bath</span>}
                          {listing.sqft != null && <span>📐 {listing.sqft.toLocaleString()} sqft</span>}
                        </div>

                        <div className="flex-1" />

                        {/* Features at bottom */}
                        {listing.amenities?.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mt-4 pt-3 border-t border-gray-100">
                            {listing.amenities.map((amenity) => (
                              <span key={amenity} className={`text-[11px] px-2 py-0.5 rounded-full font-medium ${
                                matchedFeatures.includes(amenity)
                                  ? "bg-purple-100 text-purple-700 ring-1 ring-purple-300"
                                  : "bg-gray-100 text-gray-500"
                              }`}>
                                {matchedFeatures.includes(amenity) ? "✓ " : ""}{amenity}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ) : (
                    /* ── BACK — non-repetitive details only ── */
                    <div className="p-5 cursor-pointer" onClick={() => setFlippedCardId(null)}>
                      <div className="flex items-center justify-between mb-4">
                        <span className="text-xs text-purple-500 font-medium uppercase tracking-wider">Details & Photos</span>
                        <span className="text-xs text-gray-400 hover:text-gray-600">click to flip back</span>
                      </div>

                      {/* Photo gallery */}
                      {images.length > 0 && (
                        <div className="flex gap-2 overflow-x-auto pb-3 mb-4 -mx-1 px-1">
                          {images.map((imageUrl, imageIndex) => (
                            <img key={imageIndex} src={imageUrl} alt={`Photo ${imageIndex + 1}`}
                              className="w-44 h-32 rounded-lg object-cover flex-shrink-0 border border-gray-100" loading="lazy" />
                          ))}
                        </div>
                      )}

                      {/* All features as tags — highlighted matches */}
                      {listing.amenities?.length > 0 && (
                        <div className="mb-4">
                          <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">Features</p>
                          <div className="flex flex-wrap gap-1.5">
                            {listing.amenities.map((amenity) => (
                              <span key={amenity} className={`text-[11px] px-2.5 py-1 rounded-full font-medium ${
                                matchedFeatures.includes(amenity)
                                  ? "bg-purple-100 text-purple-700 ring-1 ring-purple-300"
                                  : "bg-gray-100 text-gray-500"
                              }`}>
                                {matchedFeatures.includes(amenity) ? "✓ " : ""}{amenity}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Extra details from parsed_data — only fields NOT on front */}
                      {(() => {
                        const extraDetails: { label: string; value: string }[] = []
                        if (parsedData.propertyType) extraDetails.push({ label: "Type", value: String(parsedData.propertyType) })
                        if (parsedData.yearBuilt) extraDetails.push({ label: "Year Built", value: String(parsedData.yearBuilt) })
                        if (parsedData.daysOnMarket) extraDetails.push({ label: "Days Listed", value: `${parsedData.daysOnMarket} days` })
                        if (parsedData.dateAvailable) extraDetails.push({ label: "Available", value: String(parsedData.dateAvailable) })
                        if (parsedData.lastSeen) extraDetails.push({ label: "Last Seen", value: String(parsedData.lastSeen) })
                        if (parsedData.listedDate) extraDetails.push({ label: "Listed", value: String(parsedData.listedDate) })
                        if (parsedData.county) extraDetails.push({ label: "County", value: String(parsedData.county) })
                        if (parsedData.lotSize) extraDetails.push({ label: "Lot Size", value: `${parsedData.lotSize} sqft` })

                        return extraDetails.length > 0 ? (
                          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-4">
                            {extraDetails.map(({ label, value }) => (
                              <div key={label} className="bg-gray-50 rounded-lg px-3 py-2">
                                <p className="text-[10px] text-gray-400 uppercase tracking-wider">{label}</p>
                                <p className="text-sm font-medium text-gray-700">{value}</p>
                              </div>
                            ))}
                          </div>
                        ) : null
                      })()}

                      {/* Actions */}
                      <div className="flex items-center gap-3 pt-3 border-t border-gray-100" onClick={(event) => event.stopPropagation()}>
                        {listing.source_url && (
                          <a href={listing.source_url} target="_blank" rel="noreferrer"
                            className="text-xs text-purple-600 hover:underline">
                            View original listing →
                          </a>
                        )}
                        <div className="flex-1" />
                        <button
                          onClick={() => listing.is_saved ? handleUnnest(listing.id) : handleShortlist(listing.id)}
                          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all border ${
                            listing.is_saved
                              ? "bg-purple-50 text-purple-700 border-purple-200 hover:bg-purple-100"
                              : "text-gray-600 hover:text-purple-700 border-gray-200 hover:border-purple-300"
                          }`}
                        >
                          {listing.is_saved ? "🪺 Unnest" : "🪹 Nest this"}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Load more */}
          {listings.length > visibleCount && (
            <div className="text-center mt-6">
              <Button
                variant="outline"
                className="text-purple-600 border-purple-200 hover:bg-purple-50 hover:border-purple-300"
                onClick={() => setVisibleCount(previous => previous + 20)}
              >
                Show more ({listings.length - visibleCount} remaining)
              </Button>
            </div>
          )}
        </div>
      )}

      {listings.length === 0 && !isSearching && (
        <div className="text-center py-16 text-muted-foreground">
          <div className="text-4xl mb-3">🏠</div>
          <p className="text-sm font-medium">Ready to find your next nest</p>
          <p className="text-xs mt-1">Set your filters above and search. Connect a source in Settings first.</p>
        </div>
      )}
    </div>
  )
}
