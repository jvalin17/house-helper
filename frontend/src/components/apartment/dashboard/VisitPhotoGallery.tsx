/**
 * VisitPhotoGallery — photo management orchestrator for apartment visit photos.
 *
 * Coordinates photo loading, upload, deletion, room tagging, label editing,
 * AI analysis, and lightbox viewing. Delegates rendering to PhotoGrid,
 * PhotoUploadButton, PhotoLightbox, and PhotoAnalysisCard.
 */

import { useState, useEffect, useCallback } from "react"
import { api } from "@/api/client"
import type { VisitPhoto } from "@/types"
import PhotoGrid from "@/components/apartment/dashboard/PhotoGrid"
import PhotoUploadButton from "@/components/apartment/dashboard/PhotoUploadButton"
import PhotoLightbox from "@/components/apartment/dashboard/PhotoLightbox"
import PhotoAnalysisCard from "@/components/apartment/dashboard/PhotoAnalysisCard"

interface VisitPhotoGalleryProps {
  listingId: number
}

export default function VisitPhotoGallery({ listingId }: VisitPhotoGalleryProps) {
  const [photos, setPhotos] = useState<VisitPhoto[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [deletingPhotoId, setDeletingPhotoId] = useState<number | null>(null)
  const [analysisResult, setAnalysisResult] = useState<Record<string, unknown> | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null)

  // Load photos on mount
  useEffect(() => {
    let cancelled = false
    async function loadPhotos() {
      try {
        const fetchedPhotos = await api.getPhotos(listingId)
        if (!cancelled) {
          setPhotos(fetchedPhotos)
        }
      } catch {
        // Failed to load photos — show empty state
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    loadPhotos()
    return () => { cancelled = true }
  }, [listingId])

  const handleFileUpload = useCallback(async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = event.target.files
    if (!selectedFiles || selectedFiles.length === 0) return

    setUploading(true)
    try {
      const photoEntries: Array<{ file_path: string; label?: string; room_tag?: string }> = []
      for (let fileIndex = 0; fileIndex < selectedFiles.length; fileIndex++) {
        const file = selectedFiles[fileIndex]
        const fileExtension = file.name.split(".").pop()?.toLowerCase() || "jpg"
        const validExtension = ["jpg", "jpeg", "png", "webp"].includes(fileExtension) ? fileExtension : "jpg"
        const uniqueId = crypto.randomUUID()
        const filePath = `photos/${listingId}/${uniqueId}.${validExtension}`
        photoEntries.push({
          file_path: filePath,
          label: file.name.replace(/\.[^/.]+$/, ""),
        })
      }

      await api.savePhotos(listingId, photoEntries)
      const updatedPhotos = await api.getPhotos(listingId)
      setPhotos(updatedPhotos)
    } catch {
      // Upload failed — silently handle
    } finally {
      setUploading(false)
    }
  }, [listingId])

  const handleDeletePhoto = useCallback(async (photoId: number) => {
    setDeletingPhotoId(photoId)
    try {
      await api.deletePhoto(photoId)
      setPhotos(previousPhotos => previousPhotos.filter(photo => photo.id !== photoId))
    } catch {
      // Delete failed
    } finally {
      setDeletingPhotoId(null)
    }
  }, [])

  const handleRoomTagChange = useCallback(async (photoId: number, newRoomTag: string) => {
    try {
      await api.updatePhoto(photoId, { room_tag: newRoomTag || undefined })
      setPhotos(previousPhotos =>
        previousPhotos.map(photo =>
          photo.id === photoId
            ? { ...photo, room_tag: newRoomTag || null }
            : photo
        )
      )
    } catch {
      // Tag update failed
    }
  }, [])

  const handleLabelSave = useCallback(async (photoId: number, labelText: string) => {
    try {
      await api.updatePhoto(photoId, { label: labelText })
      setPhotos(previousPhotos =>
        previousPhotos.map(photo =>
          photo.id === photoId
            ? { ...photo, label: labelText || null }
            : photo
        )
      )
    } catch {
      // Label update failed
    }
  }, [])

  const handleAnalyzePhotos = useCallback(async () => {
    setAnalyzing(true)
    setAnalysisError(null)
    try {
      const result = await api.analyzePhotos(listingId)
      setAnalysisResult(result)
    } catch (error) {
      setAnalysisError(
        error instanceof Error ? error.message : "Analysis failed. Please try again."
      )
    } finally {
      setAnalyzing(false)
    }
  }, [listingId])

  const handlePhotoClick = useCallback((photoIndex: number) => {
    setLightboxIndex(photoIndex)
  }, [])

  const handleCloseLightbox = useCallback(() => {
    setLightboxIndex(null)
  }, [])

  const handleNavigateLightbox = useCallback((newIndex: number) => {
    setLightboxIndex(newIndex)
  }, [])

  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="h-20 rounded-lg bg-gray-100" />
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-2">
        <label className="text-xs font-medium text-gray-500">Visit Photos</label>
        <div className="flex items-center gap-2">
          <PhotoUploadButton
            listingId={listingId}
            uploading={uploading}
            onFilesSelected={handleFileUpload}
          />
        </div>
      </div>

      {/* Empty state */}
      {photos.length === 0 && (
        <div className="rounded-lg border border-dashed border-gray-200 bg-gray-50/50 px-4 py-6 text-center">
          <svg className="w-8 h-8 mx-auto text-gray-300 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z" />
          </svg>
          <p className="text-xs text-gray-400">
            No visit photos yet — upload photos from your apartment tour
          </p>
        </div>
      )}

      {/* Photo grid + analysis */}
      {photos.length > 0 && (
        <div className="space-y-3">
          <PhotoGrid
            photos={photos}
            deletingPhotoId={deletingPhotoId}
            onDeletePhoto={handleDeletePhoto}
            onRoomTagChange={handleRoomTagChange}
            onLabelSave={handleLabelSave}
            onPhotoClick={handlePhotoClick}
          />

          {/* Analyze button */}
          <div className="flex flex-col items-stretch gap-2">
            <button
              onClick={handleAnalyzePhotos}
              disabled={photos.length === 0 || analyzing}
              className="w-full text-xs font-medium px-3 py-2 rounded-lg bg-indigo-500 text-white hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors cursor-pointer flex items-center justify-center gap-2"
            >
              {analyzing && (
                <div className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              )}
              {analyzing ? "Analyzing..." : "Analyze My Photos"}
            </button>

            {analysisError && (
              <p className="text-[11px] text-red-500 text-center">{analysisError}</p>
            )}
          </div>

          {/* Analysis results */}
          <PhotoAnalysisCard analysis={analysisResult} loading={analyzing} />
        </div>
      )}

      {/* Lightbox overlay */}
      {lightboxIndex !== null && (
        <PhotoLightbox
          photos={photos}
          currentIndex={lightboxIndex}
          onClose={handleCloseLightbox}
          onNavigate={handleNavigateLightbox}
        />
      )}
    </div>
  )
}
