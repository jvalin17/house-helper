/**
 * VisitNotesEditor — debounced auto-save textarea for visit notes.
 *
 * Loads existing notes on mount, then auto-saves with 800ms debounce.
 * Shows "Saving..." / "Saved" indicator.
 */

import { useEffect, useState, useRef, useCallback } from "react"
import { api } from "@/api/client"

interface VisitNotesEditorProps {
  listingId: number
}

export default function VisitNotesEditor({ listingId }: VisitNotesEditorProps) {
  const [notesContent, setNotesContent] = useState("")
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved">("idle")
  const [loading, setLoading] = useState(true)
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const latestNotesRef = useRef("")

  // Load existing notes on mount
  useEffect(() => {
    let cancelled = false
    async function loadNotes() {
      try {
        const existingNotes = await api.getDashboardNotes(listingId)
        if (!cancelled && existingNotes) {
          setNotesContent(existingNotes.notes)
          latestNotesRef.current = existingNotes.notes
        }
      } catch {
        // No existing notes — that's fine
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    loadNotes()
    return () => { cancelled = true }
  }, [listingId])

  const saveNotes = useCallback(async (content: string) => {
    setSaveStatus("saving")
    try {
      await api.saveDashboardNotes(listingId, content)
      setSaveStatus("saved")
      // Clear "Saved" indicator after 2 seconds
      setTimeout(() => setSaveStatus("idle"), 2000)
    } catch {
      setSaveStatus("idle")
    }
  }, [listingId])

  const handleNotesChange = useCallback((event: React.ChangeEvent<HTMLTextAreaElement>) => {
    const updatedContent = event.target.value
    setNotesContent(updatedContent)
    latestNotesRef.current = updatedContent

    // Clear existing debounce timer
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current)
    }

    // Set new debounce timer (800ms)
    debounceTimerRef.current = setTimeout(() => {
      saveNotes(latestNotesRef.current)
    }, 800)
  }, [saveNotes])

  // Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current)
      }
    }
  }, [])

  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="h-24 rounded-lg bg-gray-100" />
      </div>
    )
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <label className="text-xs font-medium text-gray-500">Visit Notes</label>
        {saveStatus === "saving" && (
          <span className="text-[10px] text-indigo-500 font-medium">Saving...</span>
        )}
        {saveStatus === "saved" && (
          <span className="text-[10px] text-emerald-500 font-medium">Saved</span>
        )}
      </div>
      <textarea
        value={notesContent}
        onChange={handleNotesChange}
        placeholder="Add visit notes..."
        className="w-full min-h-24 resize-y rounded-lg border border-gray-200 px-3 py-2 text-sm text-gray-700 placeholder:text-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-200 focus:border-indigo-300 transition-shadow"
      />
    </div>
  )
}
