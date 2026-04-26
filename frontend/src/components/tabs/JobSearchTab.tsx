import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Separator } from "@/components/ui/separator"
import { api } from "@/api/client"
import PreviewModal from "@/components/PreviewModal"
import JobDetail from "@/components/JobDetail"

interface Job {
  id: number; title: string; company: string
  match_score: number | null; source_url: string | null
  parsed_data: string; match_breakdown: string | null
}

interface PipelineEntry {
  id: number; job_id: number; status: string
  resume_id: number | null; cover_letter_id: number | null
  job_title: string; job_company: string; job_url: string | null
  match_score: number | null; apply_method: string | null
}

interface PipelineState {
  stage: "idle" | "searching" | "matching" | "generating" | "ready" | "applying"
  searchRole: string
  currentJob: string
  entries: PipelineEntry[]
  message: string
}

interface Props { onApplied: () => void }

export default function JobSearchTab({ onApplied }: Props) {
  const [jobs, setJobs] = useState<Job[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [pasteInput, setPasteInput] = useState("")
  const [pasteMsg, setPasteMsg] = useState("")
  const [filters, setFilters] = useState({ title: "", location: "", remote: false, keywords: "" })
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [preview, setPreview] = useState<{ jobId: number; title: string; company: string } | null>(null)
  const [detailJob, setDetailJob] = useState<Job | null>(null)
  const [pipeline, setPipeline] = useState<PipelineState>({
    stage: "idle", searchRole: "", currentJob: "", entries: [], message: "",
  })

  useEffect(() => { loadJobs(); loadQueue() }, [])

  const loadJobs = async () => {
    try {
      const data = await api.listJobs() as unknown as Job[]
      setJobs(data)
    } catch { /* silent */ }
  }

  const loadQueue = async () => {
    try {
      const q = await fetch("/api/apply/queue").then((r) => r.json()) as PipelineEntry[]
      if (q.length > 0) {
        setPipeline((prev) => ({ ...prev, entries: q, stage: q.some((e) => e.status === "ready" || e.status === "confirmed") ? "ready" : prev.stage }))
      }
    } catch { /* silent */ }
  }

  const handleSearch = async () => {
    setSearchLoading(true)
    setPasteMsg("")
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
      const data = await r.json()
      setPasteMsg(`Found ${data.count || 0} new jobs`)
      loadJobs()
    } catch {
      setPasteMsg("Search failed — check job source API keys in Settings")
    } finally { setSearchLoading(false) }
  }

  const handleAutoApply = async () => {
    setSearchLoading(true)
    const role = filters.title || filters.keywords || "matching roles"

    // Stage: searching
    setPipeline({ stage: "searching", searchRole: String(role), currentJob: "", entries: [], message: `Searching for ${role}...` })

    try {
      const searchFilters: Record<string, unknown> = {}
      if (filters.title) searchFilters.title = filters.title
      if (filters.location) searchFilters.location = filters.location
      if (filters.remote) searchFilters.remote = true
      if (filters.keywords) searchFilters.keywords = filters.keywords.split(",").map((k) => k.trim())

      // Stage: matching
      setPipeline((prev) => ({ ...prev, stage: "matching", message: "Matching knowledge bank against job descriptions..." }))

      const r = await fetch("/api/apply/auto", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filters: searchFilters, max_jobs: 5 }),
      })
      const data = await r.json()

      const q = (data.queue || []) as PipelineEntry[]
      setPipeline({
        stage: q.some((e) => e.status === "ready") ? "ready" : "idle",
        searchRole: "",
        currentJob: "",
        entries: q,
        message: data.message || `Found ${data.jobs_found} jobs`,
      })
      loadJobs()
    } catch {
      setPipeline({ stage: "idle", searchRole: "", currentJob: "", entries: [], message: "Auto apply failed — check job source API keys in Settings" })
    } finally { setSearchLoading(false) }
  }

  const handlePaste = async () => {
    if (!pasteInput.trim()) return
    setSearchLoading(true)
    setPasteMsg("")
    try {
      const lines = pasteInput.split("\n").map((l) => l.trim()).filter(Boolean)
      const result = await api.parseJobs(lines)
      setPasteMsg(`Parsed ${result.jobs.length} job(s)`)
      setPasteInput("")
      loadJobs()
    } catch (err) {
      setPasteMsg(`Error: ${err instanceof Error ? err.message : "Parse failed"}`)
    } finally { setSearchLoading(false) }
  }

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else if (next.size < 5) next.add(id)
      return next
    })
  }

  const handleStartPipeline = async () => {
    const ids = Array.from(selected)
    if (ids.length === 0) return

    // Stage 1: Queue
    setPipeline({ stage: "matching", searchRole: filters.title || "selected roles", currentJob: "", entries: [], message: "Matching knowledge bank against job descriptions..." })

    try {
      const r = await fetch("/api/apply/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_ids: ids }),
      })
      const data = await r.json()
      const entries = data.queue as PipelineEntry[]

      // Stage 2: Generate docs for each
      setPipeline((prev) => ({ ...prev, stage: "generating", entries, message: "" }))

      for (const entry of entries) {
        const now = new Date()
        const mmyy = `${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getFullYear()).slice(2)}`
        setPipeline((prev) => ({
          ...prev,
          currentJob: `Generating Resume_${(entry.job_title || "role").replace(/\s+/g, "_")}_${mmyy}.pdf`,
          message: `for ${entry.job_company}`,
        }))

        try {
          await fetch(`/api/apply/generate/${entry.id}`, { method: "POST" })
        } catch { /* continue to next */ }
      }

      // Refresh queue
      const q = await fetch("/api/apply/queue").then((r) => r.json()) as PipelineEntry[]
      setPipeline((prev) => ({ ...prev, stage: "ready", entries: q, currentJob: "", message: "Documents ready for review" }))
      setSelected(new Set())
      loadJobs()
    } catch {
      setPipeline((prev) => ({ ...prev, stage: "idle", message: "Pipeline failed" }))
    }
  }

  const handleOpenApplication = async (entryId: number) => {
    // Step 1: Open the application page in browser
    setPipeline((prev) => ({ ...prev, stage: "applying" }))
    await fetch(`/api/apply/confirm/${entryId}`, { method: "POST" })
    await fetch(`/api/apply/execute/${entryId}`, { method: "POST" })

    // Don't mark as "applied" yet — user needs to confirm they actually submitted
    const q = await fetch("/api/apply/queue").then((r) => r.json()) as PipelineEntry[]
    setPipeline((prev) => ({
      ...prev,
      stage: q.some((e) => e.status === "ready") ? "ready" : "idle",
      entries: q,
      message: "",
    }))
  }

  const handleMarkApplied = async (_entryId: number) => {
    // User confirms they actually submitted on the company site
    // The application was already tracked when execute was called,
    // but this confirms it was truly submitted by the user
    const q = await fetch("/api/apply/queue").then((r) => r.json()) as PipelineEntry[]
    setPipeline((prev) => ({
      ...prev,
      entries: q,
      stage: q.some((e) => e.status === "ready") ? "ready" : "idle",
    }))
    onApplied()
  }

  const handleSkip = async (entryId: number) => {
    await fetch(`/api/apply/skip/${entryId}`, { method: "POST" })
    const q = await fetch("/api/apply/queue").then((r) => r.json()) as PipelineEntry[]
    setPipeline((prev) => ({
      ...prev,
      entries: q,
      stage: q.some((e) => e.status === "ready") ? "ready" : "idle",
    }))
  }

  const handleMatchAll = async () => {
    const ids = jobs.map((j) => j.id)
    if (ids.length > 0) { await api.matchBatch(ids); loadJobs() }
  }

  const handleRate = async (rating: string) => {
    if (!detailJob) return
    await fetch("/api/calibration/judge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: detailJob.id, rating }),
    })
  }

  const formatDate = () => {
    const now = new Date()
    return `${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getFullYear()).slice(2)}`
  }

  return (
    <div className="space-y-6">
      {/* Search Filters */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Search Jobs</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            <Input placeholder="Job Title" value={filters.title}
              onChange={(e) => setFilters({ ...filters, title: e.target.value })} />
            <Input placeholder="Location" value={filters.location}
              onChange={(e) => setFilters({ ...filters, location: e.target.value })} />
            <Input placeholder="Keywords (comma separated)" value={filters.keywords}
              onChange={(e) => setFilters({ ...filters, keywords: e.target.value })} />
            <div className="flex items-center gap-2">
              <input type="checkbox" id="remote" checked={filters.remote}
                onChange={(e) => setFilters({ ...filters, remote: e.target.checked })} />
              <label htmlFor="remote" className="text-sm">Remote Only</label>
            </div>
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button variant="outline" onClick={handleSearch} disabled={searchLoading || pipeline.stage !== "idle"}>
              {searchLoading ? "Searching..." : "Search Only"}
            </Button>
            <span className="text-sm text-muted-foreground self-center">
              Or use "Do the Magic" below to auto-search, match, and generate
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Paste Links */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Paste Links or Job Description</CardTitle></CardHeader>
        <CardContent>
          <Textarea placeholder="Paste job URLs (one per line) or a job description..."
            value={pasteInput} onChange={(e) => setPasteInput(e.target.value)} rows={3} className="mb-3 font-mono text-sm" />
          <div className="flex items-center gap-3">
            <Button onClick={handlePaste} disabled={searchLoading || !pasteInput.trim()}>Parse</Button>
            {pasteMsg && <span className={`text-sm ${pasteMsg.startsWith("Error") ? "text-destructive" : "text-muted-foreground"}`}>{pasteMsg}</span>}
          </div>
        </CardContent>
      </Card>

      <Separator />

      {/* Job Results */}
      {jobs.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">{jobs.length} Jobs</h2>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={handleMatchAll}>Match All</Button>
              {selected.size > 0 && (
                <Button size="sm" onClick={handleStartPipeline}>
                  Start Pipeline ({selected.size})
                </Button>
              )}
            </div>
          </div>

          <div className="space-y-2">
            {jobs.map((job) => (
              <Card key={job.id} className="hover:shadow-sm transition-shadow">
                <CardContent className="flex items-center gap-3 py-3">
                  <input type="checkbox" checked={selected.has(job.id)}
                    onChange={() => toggleSelect(job.id)} className="w-4 h-4 accent-primary" />
                  <div className="flex-1 cursor-pointer" onClick={() => setDetailJob(job)}>
                    <div className="font-medium text-sm">{job.title || "(untitled)"}</div>
                    <div className="text-xs text-muted-foreground">{job.company || "Unknown"}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    {job.match_score !== null && (
                      <span className="text-sm text-muted-foreground">{Math.round(job.match_score * 100)}% match</span>
                    )}
                    <Button variant="ghost" size="sm"
                      onClick={() => setPreview({ jobId: job.id, title: job.title, company: job.company })}>
                      Generate
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Apply Superpowers */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg">Apply Superpowers</CardTitle>
          {pipeline.stage === "idle" && (
            <Button onClick={handleAutoApply} disabled={searchLoading}>
              Do the Magic
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {/* Idle — no activity */}
          {pipeline.stage === "idle" && pipeline.entries.length === 0 && (
            <div className="text-center py-6">
              <p className="text-sm text-muted-foreground">
                Set your search filters above and click <strong>Do the Magic</strong>.
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                The agent will search, match your superpowers, generate tailored resumes, and queue applications for your review.
              </p>
            </div>
          )}

          {/* Active stages */}
          {pipeline.stage !== "idle" && pipeline.stage !== "ready" && (
            <div className="mb-4 space-y-2">
              {/* Stage indicators */}
              <div className={`flex items-center gap-3 p-2 rounded ${pipeline.stage === "searching" ? "" : "opacity-40"}`}>
                <div className={`w-2 h-2 rounded-full ${pipeline.stage === "searching" ? "bg-primary animate-pulse" : "bg-muted-foreground"}`} />
                <span className="text-sm">Searching for {pipeline.searchRole || "jobs"}...</span>
              </div>
              <div className={`flex items-center gap-3 p-2 rounded ${pipeline.stage === "matching" ? "" : "opacity-40"}`}>
                <div className={`w-2 h-2 rounded-full ${pipeline.stage === "matching" ? "bg-primary animate-pulse" : "bg-muted-foreground"}`} />
                <span className="text-sm">Matching knowledge bank against descriptions...</span>
              </div>
              <div className={`flex items-center gap-3 p-2 rounded ${pipeline.stage === "generating" ? "" : "opacity-40"}`}>
                <div className={`w-2 h-2 rounded-full ${pipeline.stage === "generating" ? "bg-primary animate-pulse" : "bg-muted-foreground"}`} />
                <span className="text-sm">
                  {pipeline.stage === "generating" && pipeline.currentJob
                    ? pipeline.currentJob
                    : "Generating tailored resumes..."}
                </span>
                {pipeline.message && pipeline.stage === "generating" && (
                  <span className="text-xs text-muted-foreground">{pipeline.message}</span>
                )}
              </div>
              <div className={`flex items-center gap-3 p-2 rounded ${pipeline.stage === "applying" ? "" : "opacity-40"}`}>
                <div className={`w-2 h-2 rounded-full ${pipeline.stage === "applying" ? "bg-primary animate-pulse" : "bg-muted-foreground"}`} />
                <span className="text-sm">Opening application page...</span>
              </div>
            </div>
          )}

          {/* Pipeline message */}
          {pipeline.message && pipeline.stage === "ready" && (
            <p className="text-sm text-muted-foreground mb-3">{pipeline.message}</p>
          )}
          {pipeline.message && pipeline.stage === "idle" && pipeline.entries.length > 0 && (
            <p className="text-sm text-muted-foreground mb-3">{pipeline.message}</p>
          )}

          {/* Queue entries */}
          {pipeline.entries.length > 0 && (
            <div className="space-y-2">
              {pipeline.entries.map((entry) => (
                <div key={entry.id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex-1">
                    <div className="text-sm font-medium">{entry.job_title}</div>
                    <div className="text-xs text-muted-foreground">
                      {entry.job_company}
                      {entry.match_score != null && ` · ${Math.round(entry.match_score * 100)}% match`}
                    </div>
                    {entry.status === "ready" && (
                      <div className="text-xs text-muted-foreground mt-1">
                        Resume_{(entry.job_title || "role").replace(/\s+/g, "_")}_{formatDate()}.pdf ready
                      </div>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    {entry.status === "pending" && (
                      <span className="text-xs text-muted-foreground">queued</span>
                    )}

                    {(entry.status === "ready" || entry.status === "reviewing") && (
                      <>
                        <Button variant="outline" size="sm" onClick={() => handleOpenApplication(entry.id)}>
                          Open Application
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleSkip(entry.id)}>
                          Skip
                        </Button>
                      </>
                    )}

                    {entry.status === "confirmed" && (
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-muted-foreground">Application page opened.</span>
                        <Button variant="outline" size="sm" onClick={() => handleMarkApplied(entry.id)}>
                          I've Applied
                        </Button>
                      </div>
                    )}

                    {entry.status === "applied" && (
                      <span className="text-xs text-muted-foreground">tracked</span>
                    )}

                    {entry.status === "skipped" && (
                      <span className="text-xs text-muted-foreground">skipped</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {detailJob && (
        <JobDetail job={detailJob as unknown as Record<string, unknown>} onClose={() => setDetailJob(null)}
          onGenerate={() => { setDetailJob(null); setPreview({ jobId: detailJob.id, title: detailJob.title, company: detailJob.company }) }}
          onRate={handleRate} />
      )}
      {preview && (
        <PreviewModal jobId={preview.jobId} jobTitle={preview.title} company={preview.company}
          onClose={() => { setPreview(null); loadJobs(); onApplied() }} />
      )}
    </div>
  )
}
