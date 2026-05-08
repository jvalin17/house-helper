/**
 * RoomAnalysisSection — room-by-room collapsible sections for photo analysis.
 *
 * Renders a list of rooms with expand/collapse, condition scores,
 * positives, and concerns for each room.
 */

import { useState } from "react"

interface RoomAnalysis {
  room_type: string
  observations: string
  condition_score: number
  positives: string[]
  concerns: string[]
}

const ROOM_TYPE_LABELS: Record<string, string> = {
  kitchen: "Kitchen",
  bedroom: "Bedroom",
  bathroom: "Bathroom",
  living: "Living Room",
  exterior: "Exterior",
  other: "Other",
}

function RoomSection({ room }: { room: RoomAnalysis }) {
  const [isExpanded, setIsExpanded] = useState(false)
  const roomLabel = ROOM_TYPE_LABELS[room.room_type] || room.room_type

  const scoreColor =
    room.condition_score >= 7
      ? "text-emerald-600"
      : room.condition_score >= 4
        ? "text-amber-600"
        : "text-red-600"

  return (
    <div className="border border-gray-100 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between px-3 py-2.5 bg-gray-50/50 hover:bg-gray-100/50 transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-gray-700">{roomLabel}</span>
          <span className={`text-xs font-semibold ${scoreColor}`}>
            {room.condition_score}/10
          </span>
        </div>
        <svg
          className={`w-3.5 h-3.5 text-gray-400 transition-transform duration-200 ${isExpanded ? "rotate-180" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m19 9-7 7-7-7" />
        </svg>
      </button>

      {isExpanded && (
        <div className="px-3 py-2.5 space-y-2 border-t border-gray-100">
          <p className="text-xs text-gray-600 leading-relaxed">{room.observations}</p>

          {room.positives && room.positives.length > 0 && (
            <div>
              <span className="text-[11px] font-medium text-emerald-600">Positives</span>
              <ul className="mt-0.5 space-y-0.5">
                {room.positives.map((positive, index) => (
                  <li key={index} className="text-[11px] text-gray-500 flex items-start gap-1.5">
                    <span className="text-emerald-400 mt-0.5 flex-shrink-0">+</span>
                    <span>{positive}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {room.concerns && room.concerns.length > 0 && (
            <div>
              <span className="text-[11px] font-medium text-amber-600">Concerns</span>
              <ul className="mt-0.5 space-y-0.5">
                {room.concerns.map((concern, index) => (
                  <li key={index} className="text-[11px] text-gray-500 flex items-start gap-1.5">
                    <span className="text-amber-400 mt-0.5 flex-shrink-0">!</span>
                    <span>{concern}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

interface RoomAnalysisSectionProps {
  rooms: RoomAnalysis[]
}

export default function RoomAnalysisSection({ rooms }: RoomAnalysisSectionProps) {
  if (rooms.length === 0) return null

  return (
    <div>
      <label className="text-[11px] font-medium text-gray-500 mb-1.5 block">
        Room-by-Room
      </label>
      <div className="space-y-1.5">
        {rooms.map((room, index) => (
          <RoomSection key={index} room={room} />
        ))}
      </div>
    </div>
  )
}
