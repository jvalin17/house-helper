/**
 * PhotoGrid — renders a 3-column grid of photo thumbnails with room tag overlays.
 *
 * Each photo shows: thumbnail placeholder, room tag badge, delete button (on hover),
 * editable label, and room tag dropdown selector.
 */

import { useState, useCallback } from "react"
import type { VisitPhoto } from "@/types"

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

interface PhotoGridProps {
  photos: VisitPhoto[]
  deletingPhotoId: number | null
  onDeletePhoto: (photoId: number) => void
  onRoomTagChange: (photoId: number, newRoomTag: string) => void
  onLabelSave: (photoId: number, labelText: string) => void
  onPhotoClick: (photoIndex: number) => void
}

export default function PhotoGrid({
  photos,
  deletingPhotoId,
  onDeletePhoto,
  onRoomTagChange,
  onLabelSave,
  onPhotoClick,
}: PhotoGridProps) {
  const [editingLabelId, setEditingLabelId] = useState<number | null>(null)
  const [editingLabelText, setEditingLabelText] = useState("")

  const handleStartEditing = useCallback((photoId: number, currentLabel: string) => {
    setEditingLabelId(photoId)
    setEditingLabelText(currentLabel)
  }, [])

  const handleFinishEditing = useCallback(
    (photoId: number) => {
      onLabelSave(photoId, editingLabelText)
      setEditingLabelId(null)
      setEditingLabelText("")
    },
    [editingLabelText, onLabelSave],
  )

  const handleCancelEditing = useCallback(() => {
    setEditingLabelId(null)
    setEditingLabelText("")
  }, [])

  return (
    <div className="grid grid-cols-3 gap-2">
      {photos.map((photo, photoIndex) => (
        <div
          key={photo.id}
          className="relative group rounded-lg border border-gray-200 overflow-hidden bg-gray-100"
        >
          {/* Thumbnail */}
          <button
            type="button"
            onClick={() => onPhotoClick(photoIndex)}
            className="aspect-square bg-gray-100 flex items-center justify-center w-full cursor-pointer"
          >
            <svg className="w-6 h-6 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z" />
            </svg>
          </button>

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
            onClick={() => onDeletePhoto(photo.id)}
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
                onBlur={() => handleFinishEditing(photo.id)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") handleFinishEditing(photo.id)
                  if (event.key === "Escape") handleCancelEditing()
                }}
                className="w-full text-[10px] px-1 py-0.5 rounded border border-indigo-200 focus:outline-none focus:ring-1 focus:ring-indigo-300"
                autoFocus
              />
            ) : (
              <button
                onClick={() => handleStartEditing(photo.id, photo.label || "")}
                className="w-full text-left text-[10px] text-gray-500 hover:text-gray-700 truncate cursor-pointer px-0.5"
                title="Click to edit label"
              >
                {photo.label || "Add label..."}
              </button>
            )}

            {/* Room tag dropdown */}
            <select
              value={photo.room_tag || ""}
              onChange={(event) => onRoomTagChange(photo.id, event.target.value)}
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
  )
}
