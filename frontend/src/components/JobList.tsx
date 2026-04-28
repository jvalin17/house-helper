import { useEffect, useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { api } from "@/api/client"
import PreviewModal from "@/components/PreviewModal"
import JobDetail from "@/components/JobDetail"

interface Job {
  id: number; title: string; company: string
  match_score: number | null; status: string; created_at: string
  parsed_data: string; match_breakdown: string | null
}

export default function JobList() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [preview, setPreview] = useState<{ jobId: number; title: string; company: string } | null>(null)
  const [detailJob, setDetailJob] = useState<Job | null>(null)

  useEffect(() => { loadJobs() }, [])

  const loadJobs = async () => {
    try {
      const data = await api.listJobs()
      setJobs(Array.isArray(data) ? data as unknown as Job[] : [])
    } catch { /* silent */ } finally { setLoading(false) }
  }

  const handleMatch = async (jobId: number) => {
    try {
      await api.matchJob(jobId)
      loadJobs()
    } catch { /* silent */ }
  }

  const handleMatchAll = async () => {
    const ids = jobs.map((j) => j.id)
    if (ids.length === 0) return
    try {
      await api.matchBatch(ids)
      loadJobs()
    } catch { /* silent */ }
  }

  const handleDelete = async (jobId: number) => {
    try {
      await api.deleteJob(jobId)
      loadJobs()
    } catch { /* silent */ }
  }

  const handleRate = async (rating: string) => {
    if (!detailJob) return
    try {
      await fetch(`/api/calibration/judge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: detailJob.id, rating }),
      })
    } catch { /* silent */ }
  }

  if (loading) return <p className="text-muted-foreground">Loading jobs...</p>
  if (jobs.length === 0) return <p className="text-muted-foreground">No jobs yet. Paste some links above.</p>

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold">{jobs.length} Job{jobs.length !== 1 ? "s" : ""}</h2>
        <Button variant="outline" size="sm" onClick={handleMatchAll}>Match All</Button>
      </div>

      <div className="space-y-3">
        {jobs.map((job) => (
          <Card key={job.id} className="hover:shadow-md transition-shadow cursor-pointer"
            onClick={() => setDetailJob(job)}>
            <CardContent className="flex items-center justify-between py-4">
              <div className="flex-1">
                <div className="font-medium">{job.title || "(untitled)"}</div>
                <div className="text-sm text-muted-foreground">{job.company || "Unknown"}</div>
              </div>
              <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                {job.match_score !== null && (
                  <Badge variant={job.match_score > 0.5 ? "default" : job.match_score > 0.2 ? "secondary" : "outline"}>
                    {Math.round(job.match_score * 100)}%
                  </Badge>
                )}
                {job.match_score === null && (
                  <Button variant="ghost" size="sm" onClick={() => handleMatch(job.id)}>Score</Button>
                )}
                <Button variant="outline" size="sm"
                  onClick={() => setPreview({ jobId: job.id, title: job.title, company: job.company })}>
                  Tailor Resume
                </Button>
                <Button variant="ghost" size="sm" onClick={() => handleDelete(job.id)}>Delete</Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {detailJob && (
        <JobDetail
          job={detailJob as unknown as Record<string, unknown>}
          onClose={() => setDetailJob(null)}
          onGenerate={() => {
            setDetailJob(null)
            setPreview({ jobId: detailJob.id, title: detailJob.title, company: detailJob.company })
          }}
          onRate={handleRate}
        />
      )}

      {preview && (
        <PreviewModal
          jobId={preview.jobId} jobTitle={preview.title} company={preview.company}
          onClose={() => { setPreview(null); loadJobs() }}
        />
      )}
    </>
  )
}
