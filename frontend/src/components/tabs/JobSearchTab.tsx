import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
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
  onGoToDashboard?: () => void
}

export default function JobSearchTab({ onApplied, onGoToDashboard }: Props) {
  const [searchResults, setSearchResults] = useState<Job[]>([])
  const [searchLoading, setSearchLoading] = useState(false)
  const [statusMsg, setStatusMsg] = useState("")
  const [evaluating, setEvaluating] = useState(false)
  const [filters, setFilters] = useState({ title: "", location: "", remote: false, keywords: "" })
  const [preview, setPreview] = useState<{ jobId: number; title: string; company: string } | null>(null)
  const [detailJob, setDetailJob] = useState<Job | null>(null)

  // #region agent log
  ;(window as unknown as { __dbgLog?: (l: string, m: string, d?: Record<string, unknown>) => void }).__dbgLog?.(
    "JobSearchTab.tsx:render",
    "JobSearchTab render",
    {
      hypothesisId: "G",
      searchResults_len: searchResults.length,
      first_result_keys: searchResults[0] ? Object.keys(searchResults[0] as object) : null,
      first_match_score: searchResults[0]?.match_score ?? null,
      first_parsed_data_type: typeof searchResults[0]?.parsed_data,
      hasPreview: !!preview,
      hasDetail: !!detailJob,
    }
  )
  // #endregion

  // "Search Only" — results appear HERE on this page
  // Search always works — empty filters default to knowledge bank skills + US
  const hasSearchInput = true

  const handleSearchOnly = async () => {
    if (!hasSearchInput) {
      setStatusMsg("Enter a job title or keywords to search")
      return
    }
    setSearchLoading(true)
    setStatusMsg("")
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
      setStatusMsg(`Found ${jobs.length} jobs`)
    } catch {
      setStatusMsg("Search failed — check job source API keys in Settings")
    } finally { setSearchLoading(false) }
  }

  const handleEvaluateMatch = async () => {
    if (searchResults.length === 0) return
    setEvaluating(true)
    setStatusMsg("Evaluating top 5 with AI...")
    try {
      const top5 = searchResults.slice(0, 5)
      const updated = [...searchResults]
      for (const job of top5) {
        const r = await fetch(`/api/jobs/${job.id}/match`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ use_llm: true }),
        })
        if (r.ok) {
          const data = await r.json()
          const idx = updated.findIndex((j) => j.id === job.id)
          if (idx >= 0) updated[idx] = { ...updated[idx], match_score: data.score }
        }
      }
      updated.sort((a, b) => (b.match_score || 0) - (a.match_score || 0))
      setSearchResults(updated)
      setStatusMsg("Top 5 evaluated with AI")
    } catch {
      setStatusMsg("Evaluation failed")
    } finally { setEvaluating(false) }
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

  const handleMatchAllWithAI = async () => {
    if (searchResults.length === 0) return
    setEvaluating(true)
    setStatusMsg(`Matching all ${searchResults.length} jobs with AI... this may take a minute`)
    try {
      const updated = [...searchResults]
      for (let i = 0; i < updated.length; i++) {
        setStatusMsg(`AI matching ${i + 1}/${updated.length}: ${updated[i].title}`)
        const r = await fetch(`/api/jobs/${updated[i].id}/match`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ use_llm: true }),
        })
        if (r.ok) {
          const data = await r.json()
          updated[i] = { ...updated[i], match_score: data.score }
        }
      }
      updated.sort((a, b) => (b.match_score || 0) - (a.match_score || 0))
      setSearchResults(updated)
      setStatusMsg(`All ${updated.length} jobs matched with AI`)
    } catch {
      setStatusMsg("AI matching failed")
    } finally { setEvaluating(false) }
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
  }

  return (
    <div className="space-y-6">
      {/* Search Filters */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Search Jobs</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
            <Input placeholder="Job Title (or leave empty — uses your skills)" value={filters.title}
              onChange={(e) => setFilters({ ...filters, title: e.target.value })} />
            <Input placeholder="Location (default: United States)" value={filters.location}
              onChange={(e) => setFilters({ ...filters, location: e.target.value })} />
            <Input placeholder="Skills (default: from your knowledge bank)" value={filters.keywords}
              onChange={(e) => setFilters({ ...filters, keywords: e.target.value })} />
            <div className="flex items-center gap-2">
              <input type="checkbox" id="remote" checked={filters.remote}
                onChange={(e) => setFilters({ ...filters, remote: e.target.checked })} />
              <label htmlFor="remote" className="text-sm">Remote Only</label>
            </div>
          </div>
          <div className="flex gap-2 flex-wrap items-center">
            <Button className="bg-blue-600 hover:bg-blue-700 text-white" onClick={handleSearchOnly} disabled={searchLoading || !hasSearchInput}>
              {searchLoading ? "Scanning..." : "Scout Jobs \uD83D\uDD0D"}
            </Button>
            <a href="#" onClick={(e) => { e.preventDefault(); window.open("/api/search/sources", "_blank") }}
              className="text-xs text-muted-foreground hover:text-primary" title="Add more job sources">
              + Sources
            </a>
            {statusMsg && (
              <span className={`text-xs ${statusMsg.startsWith("Error") || statusMsg.includes("failed") ? "text-destructive" : "text-muted-foreground"}`}>
                {statusMsg}
              </span>
            )}
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
                <Button variant="outline" size="sm" onClick={handleMatchAll}>Match All (local)</Button>
                <Button variant="outline" size="sm" onClick={handleEvaluateMatch} disabled={evaluating}>
                  {evaluating ? "Evaluating..." : "Evaluate Top 5 (AI)"}
                </Button>
                <Button variant="outline" size="sm" onClick={handleMatchAllWithAI} disabled={evaluating}>
                  {evaluating ? "Matching..." : "Match All (AI)"}
                </Button>
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
      <ApplyPipeline filters={filters} onComplete={handlePipelineComplete} onGoToDashboard={onGoToDashboard} />

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
