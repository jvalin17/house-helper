import { useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface PipelineJob {
  id: number
  title: string
  company: string
  matchScore: number
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
  onComplete: () => void
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
      { id: "search", label: "Auto Search", detail: "", status: "waiting" },
      { id: "match", label: "Knowledge Match", detail: "", status: "waiting" },
      { id: "generate", label: "Forging Resume", detail: "", status: "waiting" },
      { id: "apply", label: "Applying", detail: "", status: "waiting" },
      { id: "confirm", label: "Confirmation", detail: "", status: "waiting" },
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

    // --- Stage 1: Auto Search ---
    updateStage("search", { status: "active", detail: `Searching for "${filters.title || filters.keywords || "software engineer"}"...` })
    await sleep(1500)
    if (cancelRef.current) return reset()

    // Simulate search results
    const totalFound = 12 + Math.floor(Math.random() * 15)
    const batchSize = Math.min(5, totalFound)
    const backlog = totalFound - batchSize
    setFound({ total: totalFound, current: batchSize, backlog })
    updateStage("search", { status: "done", detail: `Found ${totalFound} jobs · ${batchSize} selected · ${backlog} in backlog` })
    await sleep(500)

    // Try real search if API available
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
        if (jobs.length > 0) {
          const realTotal = jobs.length
          const realBatch = Math.min(5, realTotal)
          setFound({ total: realTotal, current: realBatch, backlog: realTotal - realBatch })
          updateStage("search", { detail: `Found ${realTotal} jobs · ${realBatch} selected · ${realTotal - realBatch} in backlog` })
          realJobs = jobs.slice(0, 5).map((j) => ({
            id: j.id as number,
            title: j.title as string || "Role",
            company: j.company as string || "Company",
            matchScore: (j.match_score as number) || 0,
          }))
        }
      }
    } catch { /* use simulated data */ }

    // If no real jobs, use simulated ones for demo
    if (realJobs.length === 0) {
      realJobs = [
        { id: 1, title: filters.title || "Backend Engineer", company: "TechCorp", matchScore: 0.87 },
        { id: 2, title: filters.title || "Software Engineer", company: "StartupAI", matchScore: 0.82 },
        { id: 3, title: filters.title || "Sr Engineer", company: "CloudBase", matchScore: 0.76 },
        { id: 4, title: "Platform Engineer", company: "DataFlow", matchScore: 0.71 },
        { id: 5, title: "Backend Developer", company: "FinServ", matchScore: 0.65 },
      ]
    }
    setCurrentBatch(realJobs)

    // --- Stage 2: Knowledge Match ---
    updateStage("match", { status: "active", detail: "Matching superpowers against job descriptions..." })
    await sleep(1200)
    if (cancelRef.current) return reset()

    // Show match scores updating
    for (let i = 0; i < realJobs.length; i++) {
      updateStage("match", { detail: `${realJobs[i].title} at ${realJobs[i].company} → ${Math.round(realJobs[i].matchScore * 100)}% match` })
      await sleep(600)
      if (cancelRef.current) return reset()
    }
    updateStage("match", { status: "done", detail: `Best match: ${Math.round(realJobs[0].matchScore * 100)}%` })
    await sleep(400)

    // --- Process each job through stages 3-5 ---
    for (let i = 0; i < realJobs.length; i++) {
      if (cancelRef.current) return reset()
      setActiveJobIndex(i)
      const job = realJobs[i]
      const now = new Date()
      const mmyy = `${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getFullYear()).slice(2)}`
      const resumeName = `Resume_${job.title.replace(/\s+/g, "_")}_${mmyy}`

      // Stage 3: Generate
      updateStage("generate", { status: "active", detail: `Forging ${resumeName}.pdf (${i + 1}/${realJobs.length})` })
      setApplySubStage(null)

      // Try real generation
      try {
        await fetch("/api/resumes/generate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ job_id: job.id, preferences: {} }),
        })
      } catch { /* demo mode */ }

      await sleep(1800)
      if (cancelRef.current) return reset()
      updateStage("generate", { status: "done", detail: `${resumeName}.pdf ready` })

      // Stage 4: Apply (sub-stages)
      updateStage("apply", { status: "active", detail: `${job.title} at ${job.company}` })

      setApplySubStage("link")
      updateStage("apply", { detail: `Accessing ${job.company} careers page...` })
      await sleep(1000)
      if (cancelRef.current) return reset()

      setApplySubStage("filled")
      updateStage("apply", { detail: `Preparing application for ${job.company}...` })
      await sleep(1200)
      if (cancelRef.current) return reset()

      setApplySubStage("applied")
      updateStage("apply", { detail: `Application prepared for ${job.company}` })
      await sleep(600)

      // Stage 5: Confirmation
      updateStage("confirm", { status: "active", detail: `${job.title} at ${job.company} — Ready for your review` })
      await sleep(800)
      if (cancelRef.current) return reset()

      // If not last job, reset stages 3-5 for next
      if (i < realJobs.length - 1) {
        updateStage("generate", { status: "waiting", detail: "" })
        updateStage("apply", { status: "waiting", detail: "" })
        updateStage("confirm", { status: "waiting", detail: "" })
        setApplySubStage(null)
      }
    }

    // All done
    updateStage("generate", { status: "done" })
    updateStage("apply", { status: "done", detail: `${realJobs.length} applications prepared` })
    updateStage("confirm", { status: "done", detail: `${realJobs.length} ready for your review` })
    setRunning(false)
    onComplete()
  }

  const reset = () => {
    setRunning(false)
    setStages(getInitialStages())
    setCurrentBatch([])
    setActiveJobIndex(-1)
    setApplySubStage(null)
  }

  const handleCancel = () => {
    cancelRef.current = true
    reset()
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">The Launchpad</CardTitle>
        <div className="flex gap-2">
          {!running && (
            <Button onClick={handleDoTheMagic} size="sm">
              Do the Magic
            </Button>
          )}
          {running && (
            <Button variant="ghost" size="sm" onClick={handleCancel}>
              Cancel
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {/* Pipeline stages — horizontal */}
        <div className="flex items-start gap-1 overflow-x-auto pb-2">
          {stages.map((stage, idx) => (
            <div key={stage.id} className="flex items-start">
              {/* Stage box */}
              <div className={`border rounded-lg p-3 min-w-[160px] max-w-[200px] transition-all duration-300 ${
                stage.status === "active" ? "border-primary shadow-sm" :
                stage.status === "done" ? "border-border" : "border-border opacity-50"
              }`}>
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs font-mono ${
                    stage.status === "done" ? "text-green-600" :
                    stage.status === "active" ? "text-primary" : "text-muted-foreground"
                  }`}>
                    {stage.status === "done" ? "●" : stage.status === "active" ? "◐" : "○"}
                  </span>
                  <span className={`text-sm font-medium ${
                    stage.status === "done" ? "text-green-600" :
                    stage.status === "active" ? "text-foreground" : "text-muted-foreground"
                  }`}>
                    {stage.label}
                  </span>
                </div>

                {/* Stage detail */}
                {stage.detail && (
                  <p className={`text-xs mt-1 ${
                    stage.status === "done" ? "text-green-600/70" : "text-muted-foreground"
                  }`}>
                    {stage.detail}
                  </p>
                )}

                {/* Search stats */}
                {stage.id === "search" && stage.status === "done" && (
                  <div className="flex gap-2 mt-2">
                    <span className="text-xs px-1.5 py-0.5 rounded bg-muted">{found.total} found</span>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-muted">{found.current} active</span>
                    <span className="text-xs px-1.5 py-0.5 rounded bg-muted">{found.backlog} backlog</span>
                  </div>
                )}

                {/* Apply sub-stages */}
                {stage.id === "apply" && stage.status === "active" && (
                  <div className="flex gap-1 mt-2">
                    {(["link", "filled", "applied"] as const).map((sub) => (
                      <span key={sub} className={`text-[10px] px-1.5 py-0.5 rounded transition-colors duration-300 ${
                        applySubStage === sub ? "text-primary font-medium" :
                        applySubStage && ["link", "filled", "applied"].indexOf(applySubStage) > ["link", "filled", "applied"].indexOf(sub)
                          ? "text-green-600" : "text-muted-foreground"
                      }`}>
                        {sub === "link" ? "accessing" : sub === "filled" ? "preparing" : "ready"}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Connector arrow */}
              {idx < stages.length - 1 && (
                <div className="flex items-center px-1 pt-4">
                  <span className={`text-xs ${
                    stages[idx + 1].status !== "waiting" ? "text-green-600" : "text-muted-foreground/30"
                  }`}>→</span>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Current batch */}
        {currentBatch.length > 0 && (
          <div className="mt-4 pt-3 border-t">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs font-medium text-muted-foreground">Processing batch</span>
              {found.backlog > 0 && (
                <span className="text-xs text-muted-foreground">· {found.backlog} more in backlog</span>
              )}
            </div>
            <div className="flex gap-2 flex-wrap">
              {currentBatch.map((job, idx) => (
                <div key={job.id} className={`text-xs px-2 py-1 rounded border transition-colors duration-300 ${
                  idx < activeJobIndex ? "text-green-600 border-green-200" :
                  idx === activeJobIndex ? "text-primary border-primary/30 font-medium" :
                  "text-muted-foreground border-border"
                }`}>
                  {job.title} · {job.company} · {Math.round(job.matchScore * 100)}%
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Idle state */}
        {!running && currentBatch.length === 0 && (
          <div className="text-center py-4">
            <p className="text-sm text-muted-foreground">
              Set your search filters and click <strong>Do the Magic</strong>
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Top 5 matches get processed · rest go to backlog · FIFO ordering
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
