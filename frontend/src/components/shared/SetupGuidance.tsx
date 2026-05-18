/**
 * SetupGuidance — shared empty-state component shown when an agent
 * lacks API keys or has exhausted its quota. Displays sources to
 * connect with free-tier info and a direct link to Settings.
 */

import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import type { SourceUsage } from "@/types"

interface SourceInfo {
  displayName: string
  freeTier: string | null
  unlocks: string
  signupUrl: string | null
}

interface SetupGuidanceProps {
  title: string
  description: string
  sources: SourceInfo[]
  exhaustedSources?: SourceUsage[]
}

export default function SetupGuidance({ title, description, sources, exhaustedSources }: SetupGuidanceProps) {
  const navigate = useNavigate()
  const isExhaustedMode = exhaustedSources && exhaustedSources.length > 0

  return (
    <div className="rounded-2xl bg-white border shadow-sm p-8">
      <div className="text-center max-w-lg mx-auto">
        <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4 ${
          isExhaustedMode ? "bg-amber-50" : "bg-indigo-50"
        }`}>
          {isExhaustedMode ? (
            <svg className="w-7 h-7 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
          ) : (
            <svg className="w-7 h-7 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 5.25a3 3 0 013 3m3 0a6 6 0 01-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1121.75 8.25z" />
            </svg>
          )}
        </div>

        <h2 className="text-lg font-semibold text-gray-800 mb-1">{title}</h2>
        <p className="text-sm text-gray-500 mb-6">{description}</p>

        {/* Exhausted sources with reset timeline */}
        {isExhaustedMode && (
          <div className="space-y-2 mb-6 text-left">
            {exhaustedSources.map((source) => {
              const resetDate = new Date(source.resets_at)
              const resetLabel = source.period === "day"
                ? "Resets tomorrow"
                : `Resets ${resetDate.toLocaleDateString("en-US", { month: "long", day: "numeric" })}`
              return (
                <div key={source.service_name} className="flex items-start gap-3 p-3 rounded-lg bg-amber-50 border border-amber-100">
                  <div className="w-2 h-2 rounded-full bg-amber-400 mt-1.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-800">{source.display_name}</span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded bg-red-50 text-red-700">
                        {source.used}/{source.limit} used
                      </span>
                    </div>
                    <p className="text-xs text-amber-700 mt-0.5">{resetLabel}</p>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* Alternative sources to connect */}
        {sources.length > 0 && (
          <>
            {isExhaustedMode && (
              <p className="text-xs font-medium text-gray-500 mb-3 text-left">Try another source:</p>
            )}
            <div className="space-y-2 mb-6 text-left">
              {sources.map((source) => (
                <div key={source.displayName} className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 border border-gray-100">
                  <div className="w-2 h-2 rounded-full bg-gray-300 mt-1.5 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-gray-800">{source.displayName}</span>
                      {source.freeTier && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-700">{source.freeTier}</span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">{source.unlocks}</p>
                    {source.signupUrl && (
                      <a href={source.signupUrl} target="_blank" rel="noreferrer"
                        className="text-xs text-indigo-600 hover:underline mt-1 inline-block">
                        Get free key
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        <Button
          onClick={() => navigate("/settings")}
          className="bg-indigo-600 hover:bg-indigo-700 text-white"
        >
          Go to Settings
        </Button>
      </div>
    </div>
  )
}
