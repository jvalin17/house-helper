import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
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

interface Props {
  onApplied: () => void
}

export default function JobSearchTab({ onApplied }: Props) {
  const [jobs, setJobs] = useState<Job[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [pasteInput, setPasteInput] = useState("")
  const [pasteMsg, setPasteMsg] = useState("")
  const [filters, setFilters] = useState({ title: "", location: "", remote: false, keywords: "" })
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [preview, setPreview] = useState<{ jobId: number; title: string; company: string } | null>(null)
  const [detailJob, setDetailJob] = useState<Job | null>(null)
  const [applyQueue, setApplyQueue] = useState<Array<Record<string, unknown>>>([])

  useEffect(() => { loadJobs() }, [])

  const loadJobs = async () => {
    try {
      const data = await api.listJobs() as unknown as Job[]
      setJobs(data)
    } catch { /* silent */ }
  }

  const handleAutoSearch = async () => {
    setSearchLoading(true)
    try {
      const searchFilters: Record<string, unknown> = {}
      if (filters.title) searchFilters.title = filters.title
      if (filters.location) searchFilters.location = filters.location
      if (filters.remote) searchFilters.remote = true
      if (filters.keywords) searchFilters.keywords = filters.keywords.split(",").map((k: string) => k.trim())

      const r = await fetch("/api/search/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(searchFilters),
      })
      const data = await r.json()
      setPasteMsg(`Found ${data.count || 0} new jobs`)
      loadJobs()
    } catch (err) {
      setPasteMsg("Search failed — check settings for API keys")
    } finally { setSearchLoading(false) }
  }

  const handlePaste = async () => {
    if (!pasteInput.trim()) return
    setSearchLoading(true)
    setPasteMsg("")
    try {
      const lines = pasteInput.split("\n").map((l: string) => l.trim()).filter(Boolean)
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

  const handleApplySelected = async () => {
    const ids = Array.from(selected)
    const r = await fetch("/api/apply/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_ids: ids }),
    })
    const data = await r.json()
    setApplyQueue(data.queue || [])
    setSelected(new Set())
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
          <div className="flex gap-2">
            <Button onClick={handleAutoSearch} disabled={searchLoading}>
              {searchLoading ? "Searching..." : "Auto Search"}
            </Button>
            <span className="text-sm text-muted-foreground self-center">
              Searches LinkedIn, Indeed, and more
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
            {pasteMsg && <span className={`text-sm ${pasteMsg.startsWith("Error") ? "text-destructive" : "text-green-600"}`}>{pasteMsg}</span>}
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
                <Button size="sm" onClick={handleApplySelected}>
                  Apply Selected ({selected.size})
                </Button>
              )}
            </div>
          </div>

          <div className="space-y-2">
            {jobs.map((job) => (
              <Card key={job.id} className="hover:shadow-md transition-shadow">
                <CardContent className="flex items-center gap-3 py-3">
                  <input type="checkbox" checked={selected.has(job.id)}
                    onChange={() => toggleSelect(job.id)} className="w-4 h-4" />
                  <div className="flex-1 cursor-pointer" onClick={() => setDetailJob(job)}>
                    <div className="font-medium">{job.title || "(untitled)"}</div>
                    <div className="text-sm text-muted-foreground">{job.company || "Unknown"}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    {job.match_score !== null && (
                      <Badge variant={job.match_score > 0.5 ? "default" : job.match_score > 0.2 ? "secondary" : "outline"}>
                        {Math.round(job.match_score * 100)}%
                      </Badge>
                    )}
                    <Button variant="outline" size="sm"
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

      {/* Apply Queue */}
      {applyQueue.length > 0 && (
        <Card className="border-green-200">
          <CardHeader><CardTitle className="text-lg">Apply Queue</CardTitle></CardHeader>
          <CardContent>
            {applyQueue.map((entry) => (
              <div key={String(entry.id)} className="flex items-center justify-between p-2 border-b">
                <span>{String(entry.job_title)} at {String(entry.job_company)}</span>
                <div className="flex gap-2">
                  <Badge>{String(entry.status)}</Badge>
                  {entry.status === "pending" && (
                    <Button size="sm" onClick={async () => {
                      await fetch(`/api/apply/generate/${entry.id}`, { method: "POST" })
                      const q = await fetch("/api/apply/queue").then((r) => r.json())
                      setApplyQueue(q)
                    }}>Generate</Button>
                  )}
                  {entry.status === "ready" && (
                    <>
                      <Button size="sm" variant="outline" onClick={async () => {
                        await fetch(`/api/apply/confirm/${entry.id}`, { method: "POST" })
                        const q = await fetch("/api/apply/queue").then((r) => r.json())
                        setApplyQueue(q)
                      }}>Confirm</Button>
                      <Button size="sm" variant="ghost" onClick={async () => {
                        await fetch(`/api/apply/skip/${entry.id}`, { method: "POST" })
                        const q = await fetch("/api/apply/queue").then((r) => r.json())
                        setApplyQueue(q)
                      }}>Skip</Button>
                    </>
                  )}
                  {entry.status === "confirmed" && (
                    <Button size="sm" className="bg-green-600 hover:bg-green-700" onClick={async () => {
                      await fetch(`/api/apply/execute/${entry.id}`, { method: "POST" })
                      const q = await fetch("/api/apply/queue").then((r) => r.json())
                      setApplyQueue(q)
                      onApplied()
                    }}>Apply Now</Button>
                  )}
                  {entry.status === "applied" && <span className="text-green-600 text-sm">Applied!</span>}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

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
