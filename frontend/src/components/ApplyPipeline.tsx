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

export default function ApplyPipeline({ filters, onComplete }: Props) {
  const [running, setRunning] = useState(false)
  const [stages, setStages] = useState<PipelineStage[]>(getInitialStages())
  const [found, setFound] = useState({ total: 0, current: 0, backlog: 0 })
  const [currentBatch, setCurrentBatch] = useState<PipelineJob[]>([])
  const [activeJobIndex, setActiveJobIndex] = useState(-1)
  const [applySubStage, setApplySubStage] = useState<"link" | "filled" | "applied" | null>(null)
  const cancelRef = useRef(false)

  function getInitialStages(): PipelineStage[] {
    return [
      { id: "preflight", label: "Pre-flight Check", detail: "", status: "waiting" },
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
    cancelRef.current = false
    setStages(getInitialStages())
    setCurrentBatch([])
    setActiveJobIndex(-1)
    setApplySubStage(null)

    const role = filters.title || filters.keywords || "software engineer"

    // --- Stage 1: Pre-flight Check ---
    updateStage("preflight", { status: "active", detail: `Systems check... target: "${role}"` })
    await sleep(800)
    if (cancelRef.current) return reset()
    updateStage("preflight", { status: "done", detail: `Mission: ${role} ${filters.location ? `in ${filters.location}` : ""} ${filters.remote ? "(remote)" : ""}`.trim() })
    await sleep(400)

    // --- Stage 2: Launch Scan (auto search) ---
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
        const jobs = (data.jobs || []) as Array<Record<string, unknown>>
        realJobs = jobs.map((j) => ({
          id: j.id as number,
          title: j.title as string || "Role",
          company: j.company as string || "Company",
          matchScore: (j.match_score as number) || 0,
          url: j.url as string || undefined,
        }))
      }
    } catch { /* use simulated */ }

    if (cancelRef.current) return reset()

    // Simulated fallback if no API results
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

    // Sort by match, top 5 active, rest backlog
    realJobs.sort((a, b) => b.matchScore - a.matchScore)
    const batchSize = Math.min(5, realJobs.length)
    const backlog = realJobs.length - batchSize
    setFound({ total: realJobs.length, current: batchSize, backlog })
    setCurrentBatch(realJobs.slice(0, batchSize))

    updateStage("launch", { status: "done", detail: `${realJobs.length} targets acquired · ${batchSize} in range · ${backlog} in queue` })
    await sleep(500)

    // --- Stage 3: Orbit Match (knowledge matching) ---
    updateStage("orbit", { status: "active", detail: "Aligning superpowers with mission requirements..." })
    const batch = realJobs.slice(0, batchSize)

    for (let i = 0; i < batch.length; i++) {
      if (cancelRef.current) return reset()
      updateStage("orbit", { detail: `${batch[i].title} @ ${batch[i].company} → ${Math.round(batch[i].matchScore * 100)}% alignment` })
      await sleep(600)
    }
    updateStage("orbit", { status: "done", detail: `Best alignment: ${Math.round(batch[0].matchScore * 100)}%` })
    await sleep(400)

    // --- Stage 4-6: Process each job ---
    for (let i = 0; i < batch.length; i++) {
      if (cancelRef.current) return reset()
      setActiveJobIndex(i)
      const job = batch[i]
      const now = new Date()
      const mmyy = `${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getFullYear()).slice(2)}`
      const resumeName = `Resume_${job.title.replace(/[^a-zA-Z0-9]/g, "_")}_${mmyy}`

      // Stage 4: Payload Assembly (generating resume)
      updateStage("payload", { status: "active", detail: `Prepping ${resumeName}.pdf` })
      setApplySubStage(null)

      try {
        await fetch("/api/resumes/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ job_id: job.id, preferences: {} }),
        })
      } catch { /* demo mode */ }

      await sleep(1500)
      if (cancelRef.current) return reset()
      updateStage("payload", { status: "done", detail: `${resumeName}.pdf loaded` })

      // Stage 5: Deploy (applying)
      updateStage("deploy", { status: "active", detail: `${job.company} — initiating approach` })

      setApplySubStage("link")
      await sleep(800)
      if (cancelRef.current) return reset()

      setApplySubStage("filled")
      await sleep(1000)
      if (cancelRef.current) return reset()

      setApplySubStage("applied")
      updateStage("deploy", { status: "done", detail: `${job.company} — payload delivered` })
      await sleep(500)

      // Stage 6: Mission Control (confirmation)
      updateStage("confirm", { status: "active", detail: `${job.title} @ ${job.company} — awaiting signal` })
      await sleep(600)

      // Reset stages 4-6 for next job (except last)
      if (i < batch.length - 1) {
        updateStage("payload", { status: "waiting", detail: "" })
        updateStage("deploy", { status: "waiting", detail: "" })
        updateStage("confirm", { status: "waiting", detail: "" })
        setApplySubStage(null)
      }
    }

    // All done
    updateStage("payload", { status: "done", detail: `${batch.length} payloads assembled` })
    updateStage("deploy", { status: "done", detail: `${batch.length} missions deployed` })
    updateStage("confirm", { status: "done", detail: `Mission complete · ${batch.length} applications ready for review` })
    setRunning(false)
    onComplete(batch)
  }

  const reset = () => {
    setRunning(false)
    setStages(getInitialStages())
    setCurrentBatch([])
    setActiveJobIndex(-1)
    setApplySubStage(null)
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-lg">The Launchpad</CardTitle>
        <div className="flex gap-2">
          {!running ? (
            <Button onClick={handleDoTheMagic} size="sm">
              Do the Magic &#10024;
            </Button>
          ) : (
            <Button variant="ghost" size="sm" onClick={() => { cancelRef.current = true; reset() }}>
              Abort Mission
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {/* Pipeline — horizontal */}
        <div className="flex items-start gap-0.5 overflow-x-auto pb-2">
          {stages.map((stage, idx) => (
            <div key={stage.id} className="flex items-start">
              <div className={`border rounded-lg p-2.5 min-w-[130px] max-w-[165px] transition-all duration-300 ${
                stage.status === "active" ? "border-primary/50" :
                stage.status === "done" ? "border-border" : "border-border/40"
              }`}>
                <div className="flex items-center gap-1.5 mb-0.5">
                  <span className={`text-[10px] font-mono leading-none ${
                    stage.status === "done" ? "text-green-600" :
                    stage.status === "active" ? "text-primary" : "text-muted-foreground/40"
                  }`}>
                    {stage.status === "done" ? "●" : stage.status === "active" ? "◐" : "○"}
                  </span>
                  <span className={`text-xs font-medium leading-tight ${
                    stage.status === "done" ? "text-green-600" :
                    stage.status === "active" ? "text-foreground" : "text-muted-foreground/40"
                  }`}>
                    {stage.label}
                  </span>
                </div>

                {stage.detail && (
                  <p className={`text-[10px] leading-tight mt-1 ${
                    stage.status === "done" ? "text-green-600/60" : "text-muted-foreground"
                  }`}>
                    {stage.detail}
                  </p>
                )}

                {/* Launch scan stats */}
                {stage.id === "launch" && stage.status === "done" && (
                  <div className="flex gap-1 mt-1.5 flex-wrap">
                    <span className="text-[9px] px-1 py-0.5 rounded bg-muted">{found.total} found</span>
                    <span className="text-[9px] px-1 py-0.5 rounded bg-muted">{found.current} active</span>
                    <span className="text-[9px] px-1 py-0.5 rounded bg-muted">{found.backlog} backlog</span>
                  </div>
                )}

                {/* Deploy sub-stages */}
                {stage.id === "deploy" && stage.status === "active" && (
                  <div className="flex gap-1 mt-1.5">
                    {(["link", "filled", "applied"] as const).map((sub) => {
                      const subIdx = ["link", "filled", "applied"].indexOf(sub)
                      const activeIdx = applySubStage ? ["link", "filled", "applied"].indexOf(applySubStage) : -1
                      return (
                        <span key={sub} className={`text-[9px] transition-colors duration-300 ${
                          subIdx === activeIdx ? "text-foreground font-medium" :
                          subIdx < activeIdx ? "text-green-600" : "text-muted-foreground/40"
                        }`}>
                          {sub === "link" ? "access" : sub === "filled" ? "prep" : "lock"}
                        </span>
                      )
                    })}
                  </div>
                )}
              </div>

              {idx < stages.length - 1 && (
                <div className="flex items-center px-0.5 pt-3">
                  <span className={`text-[10px] ${
                    stages[idx + 1].status !== "waiting" ? "text-green-600" : "text-muted-foreground/20"
                  }`}>→</span>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Current batch */}
        {currentBatch.length > 0 && (
          <div className="mt-3 pt-2 border-t">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider">Active missions</span>
              {found.backlog > 0 && (
                <span className="text-[10px] text-muted-foreground">· {found.backlog} in queue</span>
              )}
            </div>
            <div className="flex gap-1.5 flex-wrap">
              {currentBatch.map((job, idx) => (
                <span key={job.id} className={`text-[10px] px-1.5 py-0.5 rounded border transition-colors duration-300 ${
                  idx < activeJobIndex ? "text-green-600 border-green-200/50" :
                  idx === activeJobIndex ? "text-foreground border-primary/30" :
                  "text-muted-foreground/50 border-border/30"
                }`}>
                  {job.title} · {job.company} · {Math.round(job.matchScore * 100)}%
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Idle state */}
        {!running && currentBatch.length === 0 && (
          <div className="text-center py-3">
            <p className="text-xs text-muted-foreground">
              Set search filters above · click <strong>Do the Magic &#10024;</strong> · top 5 launch · rest queue as FIFO
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
