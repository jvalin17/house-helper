/**
 * VisitPhotoGallery — photo management component for apartment visit photos.
 *
 * Displays uploaded photos in a grid, supports upload, room tagging,
 * inline label editing, deletion, and AI analysis trigger.
 * Embedded in ApartmentCardExpanded.
 */

import { useState, useEffect, useCallback, useRef } from "react"
import { api } from "@/api/client"
import type { VisitPhoto } from "@/types"
import PhotoAnalysisCard from "@/components/apartment/dashboard/PhotoAnalysisCard"

interface VisitPhotoGalleryProps {
  listingId: number
}

const ROOM_TAG_OPTIONS = [
  { value: "", label: "No tag" },
  { value: "kitchen", label: "Kitchen" },
  { value: "bedroom", label: "Bedroom" },
  { value: "bathroom", label: "Bathroom" },
  { value: "living", label: "Living" },
  { value: "exterior", label: "Exterior" },
  { value: "other", label: "Other" },
]

const ROOM_TAG_COLORS: Record<string, string> = {
  kitchen: "bg-amber-100 text-amber-700",
  bedroom: "bg-indigo-100 text-indigo-700",
  bathroom: "bg-cyan-100 text-cyan-700",
  living: "bg-emerald-100 text-emerald-700",
  exterior: "bg-purple-100 text-purple-700",
  other: "bg-gray-100 text-gray-600",
}

export default function VisitPhotoGallery({ listingId }: VisitPhotoGalleryProps) {
  const [photos, setPhotos] = useState<VisitPhoto[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [deletingPhotoId, setDeletingPhotoId] = useState<number | null>(null)
  const [editingLabelId, setEditingLabelId] = useState<number | null>(null)
  const [editingLabelText, setEditingLabelText] = useState("")
  const [analysisResult, setAnalysisResult] = useState<Record<string, unknown> | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

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
      // Generate file metadata for each selected file
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

      // Reload photos to get the full list with IDs
      const updatedPhotos = await api.getPhotos(listingId)
      setPhotos(updatedPhotos)
    } catch {
      // Upload failed — silently handle
    } finally {
      setUploading(false)
      // Reset file input so the same file can be re-selected
      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }
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

  const handleLabelSave = useCallback(async (photoId: number) => {
    try {
      await api.updatePhoto(photoId, { label: editingLabelText })
      setPhotos(previousPhotos =>
        previousPhotos.map(photo =>
          photo.id === photoId
            ? { ...photo, label: editingLabelText || null }
            : photo
        )
      )
    } catch {
      // Label update failed
    } finally {
      setEditingLabelId(null)
      setEditingLabelText("")
    }
  }, [editingLabelText])

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
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            onChange={handleFileUpload}
            className="hidden"
            id={`photo-upload-${listingId}`}
          />
          <label
            htmlFor={`photo-upload-${listingId}`}
            className={`text-[11px] font-medium px-2.5 py-1.5 rounded-lg border border-indigo-200 text-indigo-600 hover:bg-indigo-50 transition-colors cursor-pointer ${
              uploading ? "opacity-50 pointer-events-none" : ""
            }`}
          >
            {uploading ? "Uploading..." : "Upload Photos"}
          </label>
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

      {/* Photo grid */}
      {photos.length > 0 && (
        <div className="space-y-3">
          <div className="grid grid-cols-3 gap-2">
            {photos.map(photo => (
              <div
                key={photo.id}
                className="relative group rounded-lg border border-gray-200 overflow-hidden bg-gray-100"
              >
                {/* Thumbnail */}
                <div className="aspect-square bg-gray-100 flex items-center justify-center">
                  <svg className="w-6 h-6 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z" />
                  </svg>
                </div>

                {/* Room tag overlay */}
                {photo.room_tag && (
                  <span
                    className={`absolute top-1 left-1 text-[10px] font-medium px-1.5 py-0.5 rounded ${
                      ROOM_TAG_COLORS[photo.room_tag] || ROOM_TAG_COLORS.other
                    }`}
                  >
                    {photo.room_tag}
                  </span>
                )}

                {/* Delete button */}
                <button
                  onClick={() => handleDeletePhoto(photo.id)}
                  disabled={deletingPhotoId === photo.id}
                  className="absolute top-1 right-1 w-5 h-5 rounded-full bg-red-500/80 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600 cursor-pointer disabled:opacity-50"
                  title="Delete photo"
                >
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                  </svg>
                </button>

                {/* Label + room tag controls */}
                <div className="px-1.5 py-1.5 space-y-1 bg-white">
                  {/* Editable label */}
                  {editingLabelId === photo.id ? (
                    <input
                      type="text"
                      value={editingLabelText}
                      onChange={(event) => setEditingLabelText(event.target.value)}
                      onBlur={() => handleLabelSave(photo.id)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") handleLabelSave(photo.id)
                        if (event.key === "Escape") {
                          setEditingLabelId(null)
                          setEditingLabelText("")
                        }
                      }}
                      className="w-full text-[10px] px-1 py-0.5 rounded border border-indigo-200 focus:outline-none focus:ring-1 focus:ring-indigo-300"
                      autoFocus
                    />
                  ) : (
                    <button
                      onClick={() => {
                        setEditingLabelId(photo.id)
                        setEditingLabelText(photo.label || "")
                      }}
                      className="w-full text-left text-[10px] text-gray-500 hover:text-gray-700 truncate cursor-pointer px-0.5"
                      title="Click to edit label"
                    >
                      {photo.label || "Add label..."}
                    </button>
                  )}

                  {/* Room tag dropdown */}
                  <select
                    value={photo.room_tag || ""}
                    onChange={(event) => handleRoomTagChange(photo.id, event.target.value)}
                    className="w-full text-[10px] rounded border border-gray-100 px-0.5 py-0.5 bg-white text-gray-500 focus:outline-none focus:ring-1 focus:ring-indigo-200 cursor-pointer"
                  >
                    {ROOM_TAG_OPTIONS.map(option => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            ))}
          </div>

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
    </div>
  )
}
