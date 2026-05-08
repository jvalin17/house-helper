/**
 * PhotoUploadButton — file input trigger + upload label for visit photos.
 *
 * Renders a hidden file input and a styled label that triggers it.
 * Accepts multiple image files. Shows "Uploading..." state when active.
 */

import { useRef, useCallback } from "react"

interface PhotoUploadButtonProps {
  listingId: number
  uploading: boolean
  onFilesSelected: (event: React.ChangeEvent<HTMLInputElement>) => void
}

export default function PhotoUploadButton({
  listingId,
  uploading,
  onFilesSelected,
}: PhotoUploadButtonProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      onFilesSelected(event)
      // Reset file input so the same file can be re-selected
      if (fileInputRef.current) {
        fileInputRef.current.value = ""
      }
    },
    [onFilesSelected],
  )

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        multiple
        onChange={handleChange}
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
    </>
  )
}
