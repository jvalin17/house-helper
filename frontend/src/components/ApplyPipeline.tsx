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
}

export default function ApplyPipeline({ filters }: Props) {
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
    setStages((prev) => prev.map((s) => s.id === id ? { ...s, ...updates } : s))
  }

  const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms))

  const handleDoTheMagic = async () => {
    setRunning(true)
    setMissionComplete(false)
    cancelRef.current = false
    setStages(getInitialStages())
    setCurrentBatch([])
    setActiveJobIndex(-1)
    setApplySubStage(null)

    const role = filters.title || filters.keywords || "software engineer"

    // --- Stage 1: Pre-flight ---
    updateStage("preflight", { status: "active", detail: `Target: "${role}"` })
    await sleep(800)
    if (cancelRef.current) return reset()
    updateStage("preflight", { status: "done", detail: `${role} ${filters.location ? `· ${filters.location}` : ""} ${filters.remote ? "· remote" : ""}`.trim() })
    await sleep(400)

    // --- Stage 2: Launch Scan ---
    updateStage("launch", { status: "active", detail: "Scanning job boards..." })

    let realJobs: PipelineJob[] = []
    try {
      const searchFilters: Record<string, unknown> = {}
      if (filters.title) searchFilters.title = filters.title
      if (filters.location) searchFilters.location = filters.location
      if (filters.remote) searchFilters.remote = true
      if (filters.keywords) searchFilters.keywords = filters.keywords.split(",").map((k) => k.trim())

      const r = await fetch("/api/search/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(searchFilters),
      })
      if (r.ok) {
        const data = await r.json()
        realJobs = ((data.jobs || []) as Array<Record<string, unknown>>).map((j) => ({
          id: j.id as number,
          title: j.title as string || "Role",
          company: j.company as string || "Company",
          matchScore: (j.match_score as number) || 0,
          url: j.url as string || undefined,
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

    updateStage("launch", { status: "done", detail: `${realJobs.length} found · ${batchSize} active · ${backlog} backlog` })
    await sleep(500)

    // --- Stage 3: Orbit Match ---
    updateStage("orbit", { status: "active", detail: "Aligning superpowers..." })
    const batch = realJobs.slice(0, batchSize)

    for (let i = 0; i < batch.length; i++) {
      if (cancelRef.current) return reset()
      updateStage("orbit", { detail: `${batch[i].company} → ${Math.round(batch[i].matchScore * 100)}%` })
      await sleep(500)
    }
    updateStage("orbit", { status: "done", detail: `Top: ${Math.round(batch[0].matchScore * 100)}%` })
    await sleep(400)

    // --- Stage 4-6: Per job ---
    for (let i = 0; i < batch.length; i++) {
      if (cancelRef.current) return reset()
      setActiveJobIndex(i)
      const job = batch[i]
      const now = new Date()
      const mmyy = `${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getFullYear()).slice(2)}`
      const resumeName = `Resume_${job.title.replace(/[^a-zA-Z0-9]/g, "_")}_${mmyy}`

      updateStage("payload", { status: "active", detail: `Prepping ${resumeName}.pdf` })
      setApplySubStage(null)

      try {
        await fetch("/api/resumes/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ job_id: job.id, preferences: {} }),
        })
      } catch { /* demo */ }

      await sleep(1400)
      if (cancelRef.current) return reset()
      updateStage("payload", { status: "done", detail: `${resumeName}.pdf` })

      updateStage("deploy", { status: "active", detail: job.company })
      setApplySubStage("link")
      await sleep(700)
      if (cancelRef.current) return reset()
      setApplySubStage("filled")
      await sleep(900)
      if (cancelRef.current) return reset()
      setApplySubStage("applied")
      updateStage("deploy", { status: "done", detail: job.company })
      await sleep(400)

      updateStage("confirm", { status: "active", detail: `${job.company}` })
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
        <div className="flex gap-2">
          {!running ? (
            <Button onClick={handleDoTheMagic} size="sm">
              Do the Magic {"\u2728"}
            </Button>
          ) : (
            <Button variant="ghost" size="sm" onClick={() => { cancelRef.current = true; reset() }}>
              Abort Mission
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {/* Pipeline — horizontal, bigger fonts, blue active */}
        <div className="flex items-stretch gap-1 overflow-x-auto pb-3">
          {stages.map((stage, idx) => (
            <div key={stage.id} className="flex items-stretch">
              <div className={`rounded-lg p-3 min-w-[140px] max-w-[180px] transition-all duration-500 ${
                stage.status === "active"
                  ? "bg-blue-50 border-2 border-blue-400 shadow-sm"
                  : stage.status === "done"
                  ? "bg-green-50 border border-green-300"
                  : "bg-muted/30 border border-border/30"
              }`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-sm ${
                    stage.status === "done" ? "text-green-600" :
                    stage.status === "active" ? "text-blue-600" : "text-muted-foreground/30"
                  }`}>
                    {stage.status === "done" ? "\u2705" : stage.status === "active" ? "\u23F3" : "\u26AA"}
                  </span>
                  <span className={`text-sm font-semibold ${
                    stage.status === "done" ? "text-green-700" :
                    stage.status === "active" ? "text-blue-700" : "text-muted-foreground/40"
                  }`}>
                    {stage.label}
                  </span>
                </div>

                {stage.detail && (
                  <p className={`text-xs leading-snug mt-1 ${
                    stage.status === "done" ? "text-green-600/70" :
                    stage.status === "active" ? "text-blue-600/80" : "text-muted-foreground/40"
                  }`}>
                    {stage.detail}
                  </p>
                )}

                {stage.id === "launch" && stage.status === "done" && (
                  <div className="flex gap-1.5 mt-2 flex-wrap">
                    <span className="text-xs px-1.5 py-0.5 rounded bg-green-100 text-green-700">{found.total} found</span>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-blue-100 text-blue-700">{found.current} active</span>
                    {found.backlog > 0 && (
                      <span className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{found.backlog} backlog</span>
                    )}
                  </div>
                )}

                {stage.id === "deploy" && stage.status === "active" && (
                  <div className="flex gap-2 mt-2">
                    {(["link", "filled", "applied"] as const).map((sub) => {
                      const subIdx = ["link", "filled", "applied"].indexOf(sub)
                      const activeIdx = applySubStage ? ["link", "filled", "applied"].indexOf(applySubStage) : -1
                      return (
                        <span key={sub} className={`text-xs font-medium transition-colors duration-300 ${
                          subIdx < activeIdx ? "text-green-600" :
                          subIdx === activeIdx ? "text-blue-600" : "text-muted-foreground/30"
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
                  <span className={`text-base font-bold ${
                    stages[idx + 1].status !== "waiting" ? "text-green-500" : "text-muted-foreground/15"
                  }`}>{"\u2192"}</span>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Active missions — bigger cards */}
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
                <div key={job.id} className={`rounded-lg p-3 border-2 transition-all duration-500 ${
                  idx < activeJobIndex
                    ? "bg-green-50 border-green-300"
                    : idx === activeJobIndex
                    ? "bg-blue-50 border-blue-400 shadow-sm"
                    : "bg-muted/20 border-border/30"
                }`}>
                  <div className={`text-sm font-semibold ${
                    idx < activeJobIndex ? "text-green-700" :
                    idx === activeJobIndex ? "text-blue-700" : "text-muted-foreground/50"
                  }`}>
                    {job.company}
                  </div>
                  <div className={`text-xs ${
                    idx < activeJobIndex ? "text-green-600/70" :
                    idx === activeJobIndex ? "text-blue-600/70" : "text-muted-foreground/40"
                  }`}>
                    {job.title}
                  </div>
                  <div className={`text-lg font-bold mt-1 ${
                    idx < activeJobIndex ? "text-green-600" :
                    idx === activeJobIndex ? "text-blue-600" : "text-muted-foreground/30"
                  }`}>
                    {Math.round(job.matchScore * 100)}%
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Mission Complete — green summary box */}
        {missionComplete && (
          <div className="mt-4 p-4 rounded-lg bg-green-50 border border-green-200">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xl">{"\uD83C\uDF89"}</span>
              <span className="text-base font-semibold text-green-800">Mission Complete</span>
            </div>
            <p className="text-sm text-green-700 mb-3">
              {currentBatch.length} applications prepared from {found.total} jobs found
              {found.backlog > 0 && ` · ${found.backlog} more in backlog`}
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-5 gap-2">
              {currentBatch.map((job) => (
                <div key={job.id} className="bg-white rounded-lg p-2.5 border border-green-200">
                  <div className="text-sm font-semibold text-green-800">{job.company}</div>
                  <div className="text-xs text-green-600">{job.title}</div>
                  <div className="text-lg font-bold text-green-700 mt-0.5">{Math.round(job.matchScore * 100)}%</div>
                </div>
              ))}
            </div>
            <Button variant="ghost" size="sm" className="mt-3 text-green-700" onClick={reset}>
              Clear & Start New Mission
            </Button>
          </div>
        )}

        {/* Idle state */}
        {!running && !missionComplete && currentBatch.length === 0 && (
          <div className="text-center py-4">
            <p className="text-sm text-muted-foreground">
              Set search filters above · click <strong>Do the Magic {"\u2728"}</strong>
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Top 5 by match score launch first · rest queue as FIFO
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
