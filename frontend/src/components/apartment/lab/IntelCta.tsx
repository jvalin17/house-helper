import { useEffect, useState } from "react"
import { api } from "@/api/client"

interface IntelEstimate {
  available_sources: Array<{ name: string; label: string; estimated_cost: number }>
  unavailable_sources: Array<{ name: string; label: string; reason: string }>
  estimated_cost: number
  can_proceed: boolean
  budget_warning: string | null
  already_gathered: boolean
  daily_remaining: number
  daily_budget: number
}

interface StepStatus {
  status: "pending" | "running" | "complete" | "error"
  detail?: string
}

interface Props {
  listingId: number
  onGatherComplete: () => void
}

export default function IntelCta({ listingId, onGatherComplete }: Props) {
  const [estimate, setEstimate] = useState<IntelEstimate | null>(null)
  const [loading, setLoading] = useState(true)
  const [gathering, setGathering] = useState(false)
  const [stepStatuses, setStepStatuses] = useState<Record<string, StepStatus>>({})
  const [gatherProgress, setGatherProgress] = useState("")
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api.getIntelEstimate(listingId)
      .then(data => setEstimate(data))
      .catch(() => setEstimate(null))
      .finally(() => setLoading(false))
  }, [listingId])

  const handleGather = () => {
    setGathering(true)
    setError(null)
    setGatherProgress("Connecting to Intel pipeline...")

    const initialStatuses: Record<string, StepStatus> = {}
    for (const source of estimate?.available_sources || []) {
      initialStatuses[source.name] = { status: "pending" }
    }
    setStepStatuses(initialStatuses)

    const streamUrl = api.getIntelStreamUrl(listingId)
    const eventSource = new EventSource(streamUrl)

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        if (data.type === "progress") {
          setStepStatuses(previous => ({
            ...previous,
            [data.step]: { status: data.status, detail: data.detail },
          }))
          setGatherProgress(data.detail || `${data.status} ${data.step}`)
        }

        if (data.type === "done") {
          eventSource.close()
          setGathering(false)
          onGatherComplete()
        }

        if (data.type === "error") {
          eventSource.close()
          setError(data.message || "Intel gathering failed")
          setGathering(false)
        }
      } catch { /* ignore parse errors */ }
    }

    eventSource.onerror = () => {
      eventSource.close()
      const hasCompletedSteps = Object.values(stepStatuses).some(step => step.status === "complete")
      if (hasCompletedSteps) {
        onGatherComplete()
      } else {
        setError("Connection lost during Intel gathering")
      }
      setGathering(false)
    }
  }

  if (loading) {
    return (
      <div className="rounded-2xl border-2 border-dashed border-purple-200 bg-purple-50/50 p-6 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-5 h-5 border-2 border-purple-300 border-t-purple-600 rounded-full animate-spin" />
          <span className="text-sm text-purple-500">Checking available Intel sources...</span>
        </div>
      </div>
    )
  }

  if (!estimate || estimate.available_sources.length === 0) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-gray-50 p-6 mb-6">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gray-200 flex items-center justify-center text-gray-400 text-sm">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-500">Nest Intel</h3>
            <p className="text-xs text-gray-400">No data sources configured — connect APIs in Settings</p>
          </div>
        </div>
      </div>
    )
  }

  // ── Gathering progress view ────────────────────────
  if (gathering) {
    return (
      <div className="rounded-2xl border border-indigo-200 bg-gradient-to-br from-indigo-50 via-purple-50 to-white p-6 mb-6 relative overflow-hidden">
        {/* Animated scan lines */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute h-px w-full bg-gradient-to-r from-transparent via-indigo-300/50 to-transparent animate-pulse" style={{ top: "25%" }} />
          <div className="absolute h-px w-full bg-gradient-to-r from-transparent via-purple-300/30 to-transparent animate-pulse" style={{ top: "55%", animationDelay: "0.5s" }} />
          <div className="absolute h-px w-full bg-gradient-to-r from-transparent via-indigo-200/30 to-transparent animate-pulse" style={{ top: "80%", animationDelay: "1s" }} />
        </div>

        <div className="relative">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-indigo-100 border border-indigo-200 flex items-center justify-center">
              <div className="w-5 h-5 border-2 border-indigo-300 border-t-indigo-600 rounded-full animate-spin" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-indigo-800 tracking-wide uppercase">Intel Gathering</h3>
              <p className="text-xs text-indigo-500 font-mono">{gatherProgress}</p>
            </div>
          </div>

          {/* Per-step status */}
          <div className="grid grid-cols-1 gap-1.5">
            {(estimate?.available_sources || []).map(source => {
              const stepStatus = stepStatuses[source.name]
              const status = stepStatus?.status || "pending"

              return (
                <div key={source.name} className={`flex items-center gap-3 px-3 py-2.5 rounded-xl border transition-all duration-300 ${
                  status === "complete" ? "bg-emerald-50 border-emerald-200" :
                  status === "running" ? "bg-indigo-50 border-indigo-300 shadow-sm" :
                  status === "error" ? "bg-red-50 border-red-200" :
                  "bg-white/60 border-gray-200"
                }`}>
                  {status === "running" && <div className="w-2.5 h-2.5 rounded-full bg-indigo-500 animate-pulse flex-shrink-0" />}
                  {status === "complete" && <span className="text-emerald-600 text-sm flex-shrink-0 font-bold">✓</span>}
                  {status === "error" && <span className="text-red-500 text-sm flex-shrink-0">✗</span>}
                  {status === "pending" && <div className="w-2.5 h-2.5 rounded-full bg-gray-300 flex-shrink-0" />}

                  <span className={`text-sm flex-1 ${
                    status === "complete" ? "text-emerald-700 font-medium" :
                    status === "running" ? "text-indigo-700 font-medium" :
                    status === "error" ? "text-red-600" :
                    "text-gray-400"
                  }`}>{source.label}</span>

                  {status === "error" && stepStatus?.detail && (
                    <span className="text-[10px] text-red-400 truncate max-w-[150px]">{stepStatus.detail}</span>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </div>
    )
  }

  // ── Default CTA view ──────────────────────────────
  return (
    <div className="rounded-2xl border border-indigo-200 bg-gradient-to-br from-indigo-50 via-purple-50 to-white p-6 mb-6 relative overflow-hidden">
      {/* Subtle grid pattern */}
      <div className="absolute inset-0 opacity-[0.04]" style={{
        backgroundImage: "linear-gradient(rgba(99,102,241,.5) 1px, transparent 1px), linear-gradient(90deg, rgba(99,102,241,.5) 1px, transparent 1px)",
        backgroundSize: "20px 20px",
      }} />

      <div className="relative">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-100 to-purple-100 border border-indigo-200 flex items-center justify-center">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-indigo-600">
                <circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/><path d="M11 8v6M8 11h6"/>
              </svg>
            </div>
            <div>
              <h3 className="text-sm font-bold text-indigo-800 tracking-wide uppercase">Nest Intel</h3>
              <p className="text-xs text-indigo-500">Verified data from connected sources</p>
            </div>
          </div>
          <div className="text-right">
            <p className="text-lg font-bold text-indigo-600 font-mono">
              ~${estimate.estimated_cost < 0.01 ? "0.00" : estimate.estimated_cost.toFixed(2)}
            </p>
            <p className="text-[10px] text-indigo-400">estimated cost</p>
          </div>
        </div>

        {/* Available sources */}
        <div className="grid grid-cols-2 gap-2 mb-4">
          {estimate.available_sources.map(source => (
            <div key={source.name} className="flex items-center gap-2 px-3 py-2 rounded-xl bg-white border border-indigo-100 shadow-sm">
              <div className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-sm text-gray-700">{source.label}</span>
              {source.estimated_cost > 0 && (
                <span className="text-[10px] text-indigo-400 ml-auto font-mono">${source.estimated_cost.toFixed(3)}</span>
              )}
            </div>
          ))}
        </div>

        {/* Unavailable sources */}
        {estimate.unavailable_sources.length > 0 && (
          <div className="mb-4">
            {estimate.unavailable_sources.map(source => (
              <div key={source.name} className="flex items-center gap-2 px-3 py-1 text-xs text-gray-400">
                <div className="w-2 h-2 rounded-full bg-gray-200" />
                <span>{source.label}</span>
                <span className="text-gray-300">— {source.reason}</span>
              </div>
            ))}
          </div>
        )}

        {/* Budget warning */}
        {estimate.budget_warning && (
          <div className="px-3 py-2 rounded-xl bg-amber-50 border border-amber-200 mb-4">
            <p className="text-xs text-amber-700">{estimate.budget_warning}</p>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="px-3 py-2 rounded-xl bg-red-50 border border-red-200 mb-4">
            <p className="text-xs text-red-600">{error}</p>
          </div>
        )}

        {/* Action button */}
        <button
          onClick={handleGather}
          disabled={!estimate.can_proceed}
          className="w-full py-3 rounded-xl font-semibold text-sm tracking-wide transition-all
            bg-gradient-to-r from-indigo-600 to-purple-600
            hover:from-indigo-500 hover:to-purple-500
            active:from-indigo-700 active:to-purple-700
            text-white shadow-lg shadow-indigo-200
            disabled:opacity-40 disabled:cursor-not-allowed disabled:shadow-none
            border border-indigo-400/20"
        >
          {estimate.already_gathered ? "Re-gather Intel" : "Get Intel"}
        </button>

        {/* Budget footer */}
        <div className="flex justify-between mt-3 text-[10px] text-indigo-400 font-mono">
          <span>Budget: ${estimate.daily_remaining.toFixed(2)} / ${estimate.daily_budget.toFixed(2)} today</span>
          <span>{estimate.available_sources.length} source{estimate.available_sources.length !== 1 ? "s" : ""} ready</span>
        </div>
      </div>
    </div>
  )
}
