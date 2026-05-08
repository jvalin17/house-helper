/**
 * PhotoAnalysisCard — displays AI vision analysis results for visit photos.
 *
 * Shows overall condition score, room-by-room observations (via RoomAnalysisSection),
 * natural light assessment, questions for landlord, and move-in readiness badge.
 * Embedded inside VisitPhotoGallery after "Analyze My Photos" completes.
 */

import ScoreRing from "@/components/apartment/dashboard/ScoreRing"
import RoomAnalysisSection from "@/components/apartment/dashboard/RoomAnalysisSection"

interface PhotoAnalysis {
  rooms?: Array<{
    room_type: string
    observations: string
    condition_score: number
    positives: string[]
    concerns: string[]
  }>
  overall_condition?: { score: number; explanation: string }
  natural_light?: string
  storage_adequacy?: string
  questions_for_landlord?: string[]
  move_in_readiness?: string
  summary?: string
  parse_error?: boolean
}

interface PhotoAnalysisCardProps {
  analysis: Record<string, unknown> | null
  loading: boolean
}

const READINESS_STYLES: Record<string, { label: string; className: string }> = {
  ready: {
    label: "Move-In Ready",
    className: "bg-emerald-50 text-emerald-700 border-emerald-200",
  },
  needs_work: {
    label: "Needs Work",
    className: "bg-amber-50 text-amber-700 border-amber-200",
  },
  needs_discussion: {
    label: "Needs Discussion",
    className: "bg-indigo-50 text-indigo-700 border-indigo-200",
  },
}

export default function PhotoAnalysisCard({ analysis, loading }: PhotoAnalysisCardProps) {
  if (loading) {
    return (
      <div className="rounded-lg border border-indigo-100 bg-indigo-50/30 p-4">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-indigo-300 border-t-transparent rounded-full animate-spin" />
          <div>
            <p className="text-xs font-medium text-indigo-700">Analyzing your photos...</p>
            <p className="text-[11px] text-indigo-400 mt-0.5">
              This may take a moment depending on photo count
            </p>
          </div>
        </div>
      </div>
    )
  }

  if (!analysis) {
    return null
  }

  const typedAnalysis = analysis as unknown as PhotoAnalysis

  // Handle parse error fallback
  if (typedAnalysis.parse_error && typedAnalysis.summary) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <label className="text-xs font-medium text-gray-500 mb-2 block">Photo Analysis</label>
        <p className="text-xs text-gray-600 leading-relaxed">{typedAnalysis.summary}</p>
      </div>
    )
  }

  const overallScore = typedAnalysis.overall_condition?.score
  const readinessKey = typedAnalysis.move_in_readiness || ""
  const readinessStyle = READINESS_STYLES[readinessKey]
  const rooms = typedAnalysis.rooms || []
  const questions = typedAnalysis.questions_for_landlord || []

  // Map score to ring color
  const ringColor =
    overallScore !== undefined && overallScore >= 7
      ? "#059669"
      : overallScore !== undefined && overallScore >= 4
        ? "#d97706"
        : "#dc2626"

  return (
    <div className="rounded-lg border border-indigo-100 bg-white overflow-hidden">
      <div className="px-3 py-2.5 bg-gradient-to-r from-indigo-50/60 to-purple-50/30 border-b border-indigo-100/50">
        <label className="text-xs font-medium text-indigo-700">AI Photo Analysis</label>
      </div>

      <div className="p-3 space-y-3">
        {/* Overall score + readiness badge */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {overallScore !== undefined && (
              <ScoreRing
                score={overallScore * 10}
                size={44}
                strokeWidth={3.5}
                color={ringColor}
              />
            )}
            <div>
              <p className="text-xs font-semibold text-gray-700">
                Overall Condition
                {overallScore !== undefined && (
                  <span className="ml-1.5 text-gray-400 font-normal">{overallScore}/10</span>
                )}
              </p>
              {typedAnalysis.overall_condition?.explanation && (
                <p className="text-[11px] text-gray-500 mt-0.5 max-w-[240px]">
                  {typedAnalysis.overall_condition.explanation}
                </p>
              )}
            </div>
          </div>

          {readinessStyle && (
            <span
              className={`text-[11px] font-medium px-2 py-1 rounded-full border ${readinessStyle.className}`}
            >
              {readinessStyle.label}
            </span>
          )}
        </div>

        {/* Summary */}
        {typedAnalysis.summary && (
          <p className="text-xs text-gray-600 leading-relaxed bg-gray-50/50 rounded-lg px-3 py-2">
            {typedAnalysis.summary}
          </p>
        )}

        {/* Room-by-room observations */}
        <RoomAnalysisSection rooms={rooms} />

        {/* Natural light */}
        {typedAnalysis.natural_light && (
          <div>
            <label className="text-[11px] font-medium text-gray-500 mb-0.5 block">
              Natural Light
            </label>
            <p className="text-xs text-gray-600">{typedAnalysis.natural_light}</p>
          </div>
        )}

        {/* Storage */}
        {typedAnalysis.storage_adequacy && (
          <div>
            <label className="text-[11px] font-medium text-gray-500 mb-0.5 block">
              Storage
            </label>
            <p className="text-xs text-gray-600">{typedAnalysis.storage_adequacy}</p>
          </div>
        )}

        {/* Questions for landlord */}
        {questions.length > 0 && (
          <div>
            <label className="text-[11px] font-medium text-gray-500 mb-1 block">
              Questions for Landlord
            </label>
            <ul className="space-y-1">
              {questions.map((question, index) => (
                <li key={index} className="text-xs text-gray-600 flex items-start gap-1.5">
                  <span className="text-indigo-400 mt-0.5 flex-shrink-0">&bull;</span>
                  <span>{question}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
