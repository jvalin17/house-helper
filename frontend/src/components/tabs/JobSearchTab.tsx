import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { api } from "@/api/client"
import PreviewModal from "@/components/PreviewModal"
import ApplyPipeline from "@/components/ApplyPipeline"
import JobDetail from "@/components/JobDetail"
import type { Job, SavedResume } from "@/types"

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
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [preview, setPreview] = useState<{ jobId: number; title: string; company: string } | null>(null)
  const [detailJob, setDetailJob] = useState<Job | null>(null)
  const [profileId, setProfileId] = useState<number | null>(null)
  const [excludeSponsorship, setExcludeSponsorship] = useState(false)
  const [excludeClearance, setExcludeClearance] = useState(false)
  const [excludeInternship, setExcludeInternship] = useState(false)
  const [savedResumes, setSavedResumes] = useState<SavedResume[]>([])
  const [selectedResumeId, setSelectedResumeId] = useState<number | null>(null)

  useEffect(() => {
    // Load saved resumes for matching dropdown
    api.listSavedResumes().then((r) => {
      setSavedResumes(Array.isArray(r) ? r : [])
      const defaultResume = r.find((s: SavedResume) => s.is_saved)
      if (defaultResume) setSelectedResumeId(defaultResume.id)
    }).catch(() => {})
    // Load search defaults from active profile
    api.getActiveProfile().then((profile) => {
      if (!profile) return
      setProfileId(profile.id as number)
      if (profile.search_title) setFilters((f) => ({ ...f, title: String(profile.search_title) }))
      if (profile.search_location) setFilters((f) => ({ ...f, location: String(profile.search_location) }))
      if (profile.search_keywords) setFilters((f) => ({ ...f, keywords: String(profile.search_keywords) }))
      if (profile.search_remote) setFilters((f) => ({ ...f, remote: true }))
      try {
        const prefs = typeof profile.resume_preferences === "string"
          ? JSON.parse(profile.resume_preferences) : profile.resume_preferences || {}
        if (prefs.exclude_sponsorship) setExcludeSponsorship(true)
        if (prefs.exclude_clearance) setExcludeClearance(true)
        if (prefs.exclude_internship) setExcludeInternship(true)
      } catch { /* ignore */ }
    }).catch(() => {})
  }, [])

  const handleSearchOnly = async () => {
    setSearchLoading(true)
    setStatusMsg("")
    try {
      const searchFilters: Record<string, unknown> = {}
      if (filters.title) searchFilters.title = filters.title
      if (filters.location) searchFilters.location = filters.location
      if (filters.remote) searchFilters.remote = true
      if (filters.keywords) searchFilters.keywords = filters.keywords.split(",").map((k) => k.trim())

      const data = await api.searchJobs(searchFilters)
      const jobs = Array.isArray(data.jobs) ? data.jobs : []
      jobs.sort((a, b) => (b.match_score || 0) - (a.match_score || 0))
      setSearchResults(jobs)
      setStatusMsg(`Found ${jobs.length} jobs — sorted by match %`)
    } catch {
      setStatusMsg("Search failed — check job source API keys in Settings")
    } finally { setSearchLoading(false) }
  }

  const toggleSelect = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  const handleEvaluateSelected = async () => {
    const ids = Array.from(selected)
    if (ids.length === 0) return
    // Snapshot current result IDs to detect stale writes
    const snapshotIds = new Set(searchResults.map((j) => j.id))
    setEvaluating(true)
    setStatusMsg(`Evaluating ${ids.length} selected with AI...`)
    try {
      const updated = [...searchResults]
      for (let i = 0; i < ids.length; i++) {
        const job = updated.find((j) => j.id === ids[i])
        if (!job) continue
        setStatusMsg(`AI matching ${i + 1}/${ids.length}: ${job.title}`)
        const r = await fetch(`/api/jobs/${ids[i]}/match`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ use_llm: true }),
        })
        if (r.ok) {
          const data = await r.json()
          const idx = updated.findIndex((j) => j.id === ids[i])
          if (idx >= 0) updated[idx] = { ...updated[idx], match_score: data.score }
        }
      }
      // Only apply if the result set hasn't changed (prevents stale overwrites)
      setSearchResults((current) => {
        const currentIds = new Set(current.map((j) => j.id))
        if (currentIds.size !== snapshotIds.size || [...currentIds].some((id) => !snapshotIds.has(id))) {
          return current
        }
        const sorted = [...updated].sort((a, b) => (b.match_score || 0) - (a.match_score || 0))
        return sorted
      })
      setSelected(new Set())
      setStatusMsg(`${ids.length} jobs evaluated with AI`)
    } catch {
      setStatusMsg("AI matching failed")
    } finally { setEvaluating(false) }
  }

  const handleMatchAll = async () => {
    const ids = searchResults.map((j) => j.id)
    if (ids.length === 0) return
    setEvaluating(true)
    setStatusMsg("Matching all locally...")
    try {
      await api.matchBatch(ids)
      const allJobs = await api.listJobs()
      const jobList = Array.isArray(allJobs) ? allJobs  : []
      const resultIds = new Set(ids)
      const filtered = jobList.filter((j) => resultIds.has(j.id))
      filtered.sort((a, b) => (b.match_score || 0) - (a.match_score || 0))
      setSearchResults(filtered)
      setStatusMsg("All matched (local) — sorted by match %")
    } catch {
      setStatusMsg("Local matching failed")
    } finally { setEvaluating(false) }
  }

  const handleRate = async (rating: string) => {
    if (!detailJob) return
    try {
      await api.submitRating(detailJob.id, rating)
    } catch { /* silent */ }
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
          <div className="flex items-center gap-4 mb-3 text-xs text-muted-foreground flex-wrap">
            <label className="flex items-center gap-1" title="I need visa sponsorship — hide jobs that won't sponsor">
              <input type="checkbox" checked={excludeSponsorship}
                onChange={(e) => setExcludeSponsorship(e.target.checked)} />
              Need sponsorship
            </label>
            <label className="flex items-center gap-1" title="I don't have security clearance — hide jobs that require it">
              <input type="checkbox" checked={excludeClearance}
                onChange={(e) => setExcludeClearance(e.target.checked)} />
              I lack clearance
            </label>
            <label className="flex items-center gap-1" title="Hide internship and co-op positions">
              <input type="checkbox" checked={excludeInternship}
                onChange={(e) => setExcludeInternship(e.target.checked)} />
              Skip internships
            </label>
            {savedResumes.length > 0 && (
              <select
                className="text-xs border rounded px-2 py-1 bg-background"
                value={selectedResumeId || ""}
                onChange={(e) => setSelectedResumeId(e.target.value ? Number(e.target.value) : null)}
                aria-label="Resume for matching"
              >
                <option value="">Match with full KB</option>
                {savedResumes.map((r) => (
                  <option key={r.id} value={r.id}>{r.save_name || `Resume #${r.id}`}</option>
                ))}
              </select>
            )}
          </div>
          <div className="flex gap-2 flex-wrap items-center">
            <Button className="bg-blue-600 hover:bg-blue-700 text-white" onClick={handleSearchOnly} disabled={searchLoading}>
              {searchLoading ? "Scanning..." : "Scout Jobs \uD83D\uDD0D"}
            </Button>
            <Button variant="outline" size="sm" onClick={async () => {
              if (!profileId) return
              try {
                await api.updateProfile(profileId, {
                  search_title: filters.title || null,
                  search_location: filters.location || null,
                  search_keywords: filters.keywords || null,
                  search_remote: filters.remote ? 1 : 0,
                  resume_preferences: JSON.stringify({
                    exclude_sponsorship: excludeSponsorship,
                    exclude_clearance: excludeClearance,
                    exclude_internship: excludeInternship,
                  }),
                })
                toast.success("Search defaults saved")
              } catch (e) { toast.error(e instanceof Error ? e.message : "Failed to save") }
            }}>
              Save as Defaults
            </Button>
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
                <Button variant="outline" size="sm" onClick={handleMatchAll} disabled={evaluating}>
                  Match All (local)
                </Button>
                {selected.size > 0 ? (
                  <Button variant="outline" size="sm" onClick={handleEvaluateSelected} disabled={evaluating}>
                    {evaluating ? `Evaluating ${selected.size}...` : `Evaluate ${selected.size} Selected (AI)`}
                  </Button>
                ) : (
                  <span className="text-xs text-muted-foreground self-center">Select jobs to evaluate with AI</span>
                )}
                <Button variant="ghost" size="sm" onClick={() => setSearchResults([])}>Clear</Button>
              </div>
            </div>
            <div className="space-y-1.5">
              {searchResults.map((job) => (
                <Card key={job.id} className={`transition-shadow ${selected.has(job.id) ? "border-blue-300" : "hover:shadow-sm"}`}>
                  <CardContent className="flex items-center gap-3 py-2.5 px-3">
                    <input type="checkbox" checked={selected.has(job.id)}
                      onChange={() => toggleSelect(job.id)} className="w-3.5 h-3.5 accent-primary"
                      aria-label={`Select ${job.title}`} />
                    <div className="flex-1 cursor-pointer" onClick={() => setDetailJob(job)}>
                      <div className="text-sm font-medium">{job.title || "(untitled)"}</div>
                      <div className="text-xs text-muted-foreground">{job.company || "Unknown"}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      {job.match_score !== null && (
                        <span className="text-xs text-muted-foreground">{Math.round(job.match_score * 100)}%</span>
                      )}
                      {(job.url || job.source_url) && (
                        <a href={job.url || job.source_url || "#"} target="_blank" rel="noreferrer"
                          className="text-xs text-blue-600 hover:underline" onClick={(e) => e.stopPropagation()}>
                          View
                        </a>
                      )}
                      <Button variant="ghost" size="sm"
                        onClick={() => setPreview({ jobId: job.id, title: job.title, company: job.company })}>
                        Tailor Resume
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
        <JobDetail job={detailJob} onClose={() => setDetailJob(null)}
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
