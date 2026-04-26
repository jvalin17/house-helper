import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Separator } from "@/components/ui/separator"
import { api } from "@/api/client"
import PreviewModal from "@/components/PreviewModal"
import ApplyPipeline from "@/components/ApplyPipeline"
import JobDetail from "@/components/JobDetail"

interface Job {
  id: number; title: string; company: string
  match_score: number | null; source_url: string | null
  parsed_data: string; match_breakdown: string | null
}

interface Props {
  onApplied: () => void
  onSwitchToDashboard: () => void
}

export default function JobSearchTab({ onApplied, onSwitchToDashboard }: Props) {
  const [searchResults, setSearchResults] = useState<Job[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [pasteInput, setPasteInput] = useState("")
  const [pasteMsg, setPasteMsg] = useState("")
  const [filters, setFilters] = useState({ title: "", location: "", remote: false, keywords: "" })
  const [preview, setPreview] = useState<{ jobId: number; title: string; company: string } | null>(null)
  const [detailJob, setDetailJob] = useState<Job | null>(null)

  // "Search Only" — results appear HERE on this page
  const handleSearchOnly = async () => {
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
      const jobs = (data.jobs || []) as Job[]
      setSearchResults(jobs)
      setPasteMsg(`Found ${jobs.length} jobs`)
    } catch {
      setPasteMsg("Search failed — check job source API keys in Settings")
    } finally { setSearchLoading(false) }
  }

  const handlePaste = async () => {
    if (!pasteInput.trim()) return
    setSearchLoading(true)
    setPasteMsg("")
    try {
      const lines = pasteInput.split("\n").map((l) => l.trim()).filter(Boolean)
      const result = await api.parseJobs(lines)
      // Add parsed jobs to search results
      const newJobs = result.jobs as unknown as Job[]
      setSearchResults((prev) => [...newJobs, ...prev])
      setPasteMsg(`Parsed ${result.jobs.length} job(s)`)
      setPasteInput("")
    } catch (err) {
      setPasteMsg(`Error: ${err instanceof Error ? err.message : "Parse failed"}`)
    } finally { setSearchLoading(false) }
  }

  const handleMatchAll = async () => {
    const ids = searchResults.map((j) => j.id)
    if (ids.length > 0) {
      await api.matchBatch(ids)
      // Reload matched jobs
      const updated = await api.listJobs() as unknown as Job[]
      const resultIds = new Set(ids)
      setSearchResults(updated.filter((j) => resultIds.has(j.id)))
    }
  }

  const handleRate = async (rating: string) => {
    if (!detailJob) return
    await fetch("/api/calibration/judge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ job_id: detailJob.id, rating }),
    })
  }

  // "Do the Magic" completes → switch to Dashboard to see results
  const handlePipelineComplete = () => {
    onApplied()
    onSwitchToDashboard()
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
            <Button variant="outline" onClick={handleSearchOnly} disabled={searchLoading}>
              {searchLoading ? "Searching..." : "Search Only"}
            </Button>
            <span className="text-xs text-muted-foreground self-center">
              Browse results here · or use The Launchpad below for the full pipeline
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
            {pasteMsg && <span className={`text-xs ${pasteMsg.startsWith("Error") ? "text-destructive" : "text-muted-foreground"}`}>{pasteMsg}</span>}
          </div>
        </CardContent>
      </Card>

      {/* Search Only Results — only shows when user explicitly searched */}
      {searchResults.length > 0 && (
        <>
          <Separator />
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-muted-foreground">{searchResults.length} Results</h2>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={handleMatchAll}>Match All</Button>
                <Button variant="ghost" size="sm" onClick={() => setSearchResults([])}>Clear</Button>
              </div>
            </div>
            <div className="space-y-1.5">
              {searchResults.map((job) => (
                <Card key={job.id} className="hover:shadow-sm transition-shadow">
                  <CardContent className="flex items-center gap-3 py-2.5 px-3">
                    <div className="flex-1 cursor-pointer" onClick={() => setDetailJob(job)}>
                      <div className="text-sm font-medium">{job.title || "(untitled)"}</div>
                      <div className="text-xs text-muted-foreground">{job.company || "Unknown"}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      {job.match_score !== null && (
                        <span className="text-xs text-muted-foreground">{Math.round(job.match_score * 100)}%</span>
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
        </>
      )}

      <Separator />

      {/* The Launchpad */}
      <ApplyPipeline filters={filters} onComplete={handlePipelineComplete} />

      {detailJob && (
        <JobDetail job={detailJob as unknown as Record<string, unknown>} onClose={() => setDetailJob(null)}
          onGenerate={() => { setDetailJob(null); setPreview({ jobId: detailJob.id, title: detailJob.title, company: detailJob.company }) }}
          onRate={handleRate} />
      )}
      {preview && (
        <PreviewModal jobId={preview.jobId} jobTitle={preview.title} company={preview.company}
          onClose={() => { setPreview(null); onApplied() }} />
      )}
    </div>
  )
}
