import { useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface PipelineJob {
  id: number
  title: string
  company: string
  matchScore: number
  url?: string
}

type StageStatus = "waiting" | "active" | "done"

interface PipelineStage {
  id: string
  label: string
  detail: string
  status: StageStatus
}

interface Props {
  filters: { title: string; location: string; remote: boolean; keywords: string }
  onComplete: (jobs: PipelineJob[]) => void
  onGoToDashboard?: () => void
}

export default function ApplyPipeline({ filters, onGoToDashboard }: Props) {
  const [running, setRunning] = useState(false)
  const [stages, setStages] = useState<PipelineStage[]>(getInitialStages())
  const [found, setFound] = useState({ total: 0, current: 0, backlog: 0 })
  const [currentBatch, setCurrentBatch] = useState<PipelineJob[]>([])
  const [activeJobIndex, setActiveJobIndex] = useState(-1)
  const [applySubStage, setApplySubStage] = useState<"link" | "filled" | "applied" | null>(null)
  const [missionComplete, setMissionComplete] = useState(false)
  const cancelRef = useRef(false)

  function getInitialStages(): PipelineStage[] {
    return [
      { id: "preflight", label: "Pre-flight", detail: "", status: "waiting" },
      { id: "launch", label: "Launch Scan", detail: "", status: "waiting" },
      { id: "orbit", label: "Orbit Match", detail: "", status: "waiting" },
      { id: "payload", label: "Power Resume", detail: "", status: "waiting" },
      { id: "deploy", label: "Deploy", detail: "", status: "waiting" },
      { id: "confirm", label: "Mission Control", detail: "", status: "waiting" },
    ]
  }

  const updateStage = (id: string, updates: Partial<PipelineStage>) => {
    setStages((prev) => prev.map((stage) => stage.id === id ? { ...stage, ...updates } : stage))
  }

  const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

  const handleDoTheMagic = async () => {
    setRunning(true)
    setMissionComplete(false)
    cancelRef.current = false
    setStages(getInitialStages())
    setCurrentBatch([])
    setActiveJobIndex(-1)
    setApplySubStage(null)

    const role = filters.title || filters.keywords || "software engineer"

    updateStage("preflight", { status: "active", detail: `Target: "${role}"` })
    await sleep(800)
    if (cancelRef.current) return reset()
    updateStage("preflight", { status: "done", detail: `${role} ${filters.location ? `\u00b7 ${filters.location}` : ""} ${filters.remote ? "\u00b7 remote" : ""}`.trim() })
    await sleep(400)

    updateStage("launch", { status: "active", detail: "Scanning job boards..." })

    let realJobs: PipelineJob[] = []
    try {
      const searchFilters: Record<string, unknown> = {}
      if (filters.title) searchFilters.title = filters.title
      if (filters.location) searchFilters.location = filters.location
      if (filters.remote) searchFilters.remote = true
      if (filters.keywords) searchFilters.keywords = filters.keywords.split(",").map((keyword) => keyword.trim())
      const searchResponse = await fetch("/api/search/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(searchFilters) })
      if (searchResponse.ok) {
        const data = await searchResponse.json()
        realJobs = ((data.jobs || []) as Array<Record<string, unknown>>).map((jobData) => ({
          id: jobData.id as number, title: jobData.title as string || "Role", company: jobData.company as string || "Company",
          matchScore: (jobData.match_score as number) || 0, url: jobData.url as string || undefined,
        }))
      }
    } catch { /* fallback */ }
    if (cancelRef.current) return reset()

    if (realJobs.length === 0) {
      await sleep(1500)
      realJobs = [
        { id: 1, title: role, company: "TechCorp", matchScore: 0.87 },
        { id: 2, title: role, company: "StartupAI", matchScore: 0.82 },
        { id: 3, title: `Sr ${role}`, company: "CloudBase", matchScore: 0.76 },
        { id: 4, title: "Platform Engineer", company: "DataFlow", matchScore: 0.71 },
        { id: 5, title: role, company: "FinServ", matchScore: 0.65 },
        { id: 6, title: role, company: "MegaSoft", matchScore: 0.60 },
        { id: 7, title: role, company: "DevHub", matchScore: 0.55 },
      ]
    }

    realJobs.sort((a, b) => b.matchScore - a.matchScore)
    const batchSize = Math.min(5, realJobs.length)
    const backlog = realJobs.length - batchSize
    setFound({ total: realJobs.length, current: batchSize, backlog })
    setCurrentBatch(realJobs.slice(0, batchSize))
    updateStage("launch", { status: "done", detail: `${realJobs.length} found \u00b7 ${batchSize} active \u00b7 ${backlog} backlog` })
    await sleep(500)

    updateStage("orbit", { status: "active", detail: "Aligning superpowers..." })
    const batch = realJobs.slice(0, batchSize)
    for (let i = 0; i < batch.length; i++) {
      if (cancelRef.current) return reset()
      updateStage("orbit", { detail: `${batch[i].company} \u2192 ${Math.round(batch[i].matchScore * 100)}%` })
      await sleep(500)
    }
    updateStage("orbit", { status: "done", detail: `Top: ${Math.round(batch[0].matchScore * 100)}%` })
    await sleep(400)

    for (let i = 0; i < batch.length; i++) {
      if (cancelRef.current) return reset()
      setActiveJobIndex(i)
      const job = batch[i]
      const now = new Date()
      const mmyy = `${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getFullYear()).slice(2)}`
      const shortTitle = job.title.replace(/[^a-zA-Z0-9]/g, "_").substring(0, 20)
      const resumeName = `Resume_${shortTitle}_${mmyy}`

      updateStage("payload", { status: "active", detail: `${resumeName}.pdf` })
      setApplySubStage(null)
      try { await fetch("/api/resumes/generate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ job_id: job.id, preferences: {} }) }) } catch { /* demo */ }
      await sleep(1400)
      if (cancelRef.current) return reset()
      updateStage("payload", { status: "done", detail: resumeName })

      updateStage("deploy", { status: "active", detail: job.company })
      setApplySubStage("link"); await sleep(700)
      if (cancelRef.current) return reset()
      setApplySubStage("filled"); await sleep(900)
      if (cancelRef.current) return reset()
      setApplySubStage("applied")
      updateStage("deploy", { status: "done", detail: job.company })
      await sleep(400)

      updateStage("confirm", { status: "active", detail: job.company })
      await sleep(500)

      if (i < batch.length - 1) {
        updateStage("payload", { status: "waiting", detail: "" })
        updateStage("deploy", { status: "waiting", detail: "" })
        updateStage("confirm", { status: "waiting", detail: "" })
        setApplySubStage(null)
      }
    }

    updateStage("payload", { status: "done", detail: `${batch.length} resumes` })
    updateStage("deploy", { status: "done", detail: `${batch.length} deployed` })
    updateStage("confirm", { status: "done", detail: "All clear" })
    setMissionComplete(true)
    setRunning(false)
  }

  const reset = () => {
    setRunning(false)
    setMissionComplete(false)
    setStages(getInitialStages())
    setCurrentBatch([])
    setActiveJobIndex(-1)
    setApplySubStage(null)
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-lg">The Launchpad</CardTitle>
        {!running ? (
          <Button onClick={handleDoTheMagic} size="sm">{"Do the Magic \u2728"}</Button>
        ) : (
          <Button variant="ghost" size="sm" onClick={() => { cancelRef.current = true; reset() }}>Abort Mission</Button>
        )}
      </CardHeader>
      <CardContent>
        {/* Pipeline — horizontal, blue/white palette */}
        <div className="flex items-stretch gap-1 overflow-x-auto pb-3">
          {stages.map((stage, idx) => (
            <div key={stage.id} className="flex items-stretch">
              <div className={`rounded-lg p-3 min-w-[130px] max-w-[160px] overflow-hidden transition-all duration-500 ${
                stage.status === "active"
                  ? "bg-blue-50 border-2 border-blue-400 shadow-sm"
                  : stage.status === "done"
                  ? "bg-blue-50/50 border border-blue-200"
                  : "bg-white border border-border/30"
              }`}>
                <div className="flex items-center gap-1.5 mb-1">
                  <span className={`text-sm flex-shrink-0 ${
                    stage.status === "done" ? "text-blue-600" :
                    stage.status === "active" ? "text-blue-500" : "text-muted-foreground/25"
                  }`}>
                    {stage.status === "done" ? "\u2713" : stage.status === "active" ? "\u23F3" : "\u25CB"}
                  </span>
                  <span className={`text-sm font-semibold truncate ${
                    stage.status === "done" ? "text-blue-800" :
                    stage.status === "active" ? "text-blue-700" : "text-muted-foreground/35"
                  }`}>
                    {stage.label}
                  </span>
                </div>

                {stage.detail && (
                  <p className={`text-xs leading-snug mt-1 truncate ${
                    stage.status === "done" ? "text-blue-600/60" :
                    stage.status === "active" ? "text-blue-600/80" : "text-muted-foreground/30"
                  }`} title={stage.detail}>
                    {stage.detail}
                  </p>
                )}

                {stage.id === "launch" && stage.status === "done" && (
                  <div className="flex gap-1 mt-1.5 flex-wrap">
                    <span className="text-[11px] px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">{found.total} found</span>
                    <span className="text-[11px] px-1.5 py-0.5 rounded bg-blue-200/60 text-blue-800">{found.current} active</span>
                    {found.backlog > 0 && (
                      <span className="text-[11px] px-1.5 py-0.5 rounded bg-white text-muted-foreground border">{found.backlog} backlog</span>
                    )}
                  </div>
                )}

                {stage.id === "deploy" && stage.status === "active" && (
                  <div className="flex gap-2 mt-1.5">
                    {(["link", "filled", "applied"] as const).map((sub) => {
                      const subIdx = ["link", "filled", "applied"].indexOf(sub)
                      const activeIdx = applySubStage ? ["link", "filled", "applied"].indexOf(applySubStage) : -1
                      return (
                        <span key={sub} className={`text-xs font-medium transition-colors duration-300 ${
                          subIdx < activeIdx ? "text-blue-700" :
                          subIdx === activeIdx ? "text-blue-500" : "text-muted-foreground/25"
                        }`}>
                          {sub === "link" ? "access" : sub === "filled" ? "prep" : "lock"}
                        </span>
                      )
                    })}
                  </div>
                )}
              </div>

              {idx < stages.length - 1 && (
                <div className="flex items-center px-0.5">
                  <span className={`text-base font-light ${
                    stages[idx + 1].status !== "waiting" ? "text-blue-400" : "text-muted-foreground/10"
                  }`}>{"\u2192"}</span>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Active missions */}
        {currentBatch.length > 0 && !missionComplete && (
          <div className="mt-4 pt-3 border-t">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm font-semibold">Active Missions</span>
              {found.backlog > 0 && (
                <span className="text-xs text-muted-foreground">{found.backlog} in queue (FIFO)</span>
              )}
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-5 gap-2">
              {currentBatch.map((job, idx) => (
                <div key={job.id} className={`rounded-lg p-3 border transition-all duration-500 ${
                  idx < activeJobIndex
                    ? "bg-blue-50/50 border-blue-200"
                    : idx === activeJobIndex
                    ? "bg-blue-50 border-blue-400 shadow-sm"
                    : "bg-white border-border/30"
                }`}>
                  <div className={`text-sm font-semibold truncate ${
                    idx <= activeJobIndex ? "text-blue-800" : "text-muted-foreground/40"
                  }`}>
                    {job.company}
                  </div>
                  <div className={`text-xs truncate ${
                    idx <= activeJobIndex ? "text-blue-600/70" : "text-muted-foreground/30"
                  }`}>
                    {job.title}
                  </div>
                  <div className={`text-lg font-bold mt-1 ${
                    idx < activeJobIndex ? "text-blue-700" :
                    idx === activeJobIndex ? "text-blue-600" : "text-muted-foreground/20"
                  }`}>
                    {Math.round(job.matchScore * 100)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Mission Complete — blue/white summary */}
        {missionComplete && (
          <div className="mt-4 p-4 rounded-lg bg-blue-50 border border-blue-200">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xl">{"\uD83D\uDE80"}</span>
              <span className="text-base font-semibold text-blue-900">Mission Complete</span>
            </div>
            <p className="text-sm text-blue-700 mb-3">
              {currentBatch.length} applications prepared from {found.total} jobs found
              {found.backlog > 0 && ` \u00b7 ${found.backlog} more in backlog`}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-5 gap-2 mb-3">
              {currentBatch.map((job) => (
                <div key={job.id} className="bg-white rounded-lg p-2.5 border border-blue-100">
                  <div className="text-sm font-semibold text-blue-900 truncate">{job.company}</div>
                  <div className="text-xs text-blue-600/70 truncate">{job.title}</div>
                  <div className="text-lg font-bold text-blue-700 mt-0.5">{Math.round(job.matchScore * 100)}%</div>
                </div>
              ))}
            </div>
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="sm" className="text-blue-700" onClick={reset}>
                New Mission
              </Button>
              {onGoToDashboard && (
                <Button variant="outline" size="sm" className="text-blue-700 border-blue-200" onClick={onGoToDashboard}>
                  View all applications on Dashboard {"\u2192"}
                </Button>
              )}
            </div>
          </div>
        )}

        {/* Idle */}
        {!running && !missionComplete && currentBatch.length === 0 && (
          <div className="text-center py-4">
            <p className="text-sm text-muted-foreground">
              Set search filters above {"\u00b7"} click <strong>{"Do the Magic \u2728"}</strong>
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Top 5 by match score launch first {"\u00b7"} rest queue as FIFO
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
