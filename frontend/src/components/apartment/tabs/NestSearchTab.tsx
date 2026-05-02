import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
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
  source_url: string | null
  is_saved: number
}

export default function NestSearchTab() {
  const [urlInput, setUrlInput] = useState("")
  const [isExtracting, setIsExtracting] = useState(false)
  const [listings, setListings] = useState<ApartmentListing[]>([])
  const [selectedListingIds, setSelectedListingIds] = useState<Set<number>>(new Set())

  useEffect(() => { loadListings() }, [])

  const loadListings = async () => {
    try {
      const data = await api.listApartments()
      setListings(Array.isArray(data) ? data : [])
    } catch {
      /* silent on initial load */
    }
  }

  const handlePasteUrl = async () => {
    if (!urlInput.trim()) return
    setIsExtracting(true)
    try {
      const result = await api.createApartmentFromUrl(urlInput.trim()) as Record<string, string>
      toast.success(`Extracted: ${result.title || "listing"}`)
      setUrlInput("")
      loadListings()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Extraction failed")
    } finally {
      setIsExtracting(false)
    }
  }

  const handleSaveToShortlist = async (listingId: number) => {
    try {
      await api.saveApartmentToShortlist(listingId)
      toast.success("Saved to shortlist")
      loadListings()
    } catch {
      toast.error("Failed to save")
    }
  }

  const toggleSelectListing = (listingId: number) => {
    setSelectedListingIds(previous => {
      const updated = new Set(previous)
      if (updated.has(listingId)) {
        updated.delete(listingId)
      } else {
        updated.add(listingId)
      }
      return updated
    })
  }

  // Load listings on mount
  useState(() => { loadListings() })

  return (
    <div className="space-y-6">
      {/* Paste URL */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Find Apartments</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div>
            <Input
              placeholder="Paste an apartment listing URL (Zillow, Apartments.com, etc.)"
              value={urlInput}
              onChange={(event) => setUrlInput(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && handlePasteUrl()}
            />
            <div className="flex gap-2 mt-2">
              <Button size="sm" onClick={handlePasteUrl} disabled={!urlInput.trim() || isExtracting}>
                {isExtracting ? "Extracting..." : "Extract from URL"}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results as slabs */}
      {listings.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium">{listings.length} Listing{listings.length !== 1 ? "s" : ""}</h3>
            {selectedListingIds.size > 0 && (
              <Button size="sm" variant="outline">
                Compare {selectedListingIds.size} Selected
              </Button>
            )}
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {listings.map((listing) => (
              <Card
                key={listing.id}
                className={`transition-all hover:shadow-md ${selectedListingIds.has(listing.id) ? "ring-2 ring-purple-400" : ""}`}
              >
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={selectedListingIds.has(listing.id)}
                          onChange={() => toggleSelectListing(listing.id)}
                          className="rounded"
                        />
                        <h4 className="font-medium text-sm truncate">{listing.title}</h4>
                      </div>
                      {listing.address && (
                        <p className="text-xs text-muted-foreground mt-1 truncate">{listing.address}</p>
                      )}
                      <div className="flex items-center gap-3 mt-2">
                        {listing.price && (
                          <span className="text-lg font-bold text-purple-700">${listing.price.toLocaleString()}/mo</span>
                        )}
                        {listing.bedrooms != null && (
                          <span className="text-sm text-muted-foreground">{listing.bedrooms} bed</span>
                        )}
                        {listing.bathrooms != null && (
                          <span className="text-sm text-muted-foreground">{listing.bathrooms} bath</span>
                        )}
                        {listing.sqft && (
                          <span className="text-sm text-muted-foreground">{listing.sqft.toLocaleString()} sqft</span>
                        )}
                      </div>
                      {listing.amenities && listing.amenities.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {listing.amenities.slice(0, 5).map((amenity) => (
                            <Badge key={amenity} variant="outline" className="text-[10px]">
                              {amenity}
                            </Badge>
                          ))}
                          {listing.amenities.length > 5 && (
                            <Badge variant="outline" className="text-[10px]">+{listing.amenities.length - 5}</Badge>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 mt-3 pt-3 border-t">
                    {listing.source_url && (
                      <a href={listing.source_url} target="_blank" rel="noreferrer">
                        <Button size="sm" variant="ghost" className="text-xs">View Listing</Button>
                      </a>
                    )}
                    {!listing.is_saved ? (
                      <Button size="sm" variant="outline" className="text-xs" onClick={() => handleSaveToShortlist(listing.id)}>
                        Save to Shortlist
                      </Button>
                    ) : (
                      <Badge className="bg-green-50 text-green-700 text-[10px]">Shortlisted</Badge>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {listings.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <p className="text-sm">No apartments yet. Paste a listing URL above to get started.</p>
        </div>
      )}
    </div>
  )
}
