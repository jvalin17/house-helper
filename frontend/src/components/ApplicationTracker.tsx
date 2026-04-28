import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { api } from "@/api/client"
import type { Application, Job, StatusEntry } from "@/types"

const STATUS_COLORS: Record<string, string> = {
  applied: "bg-blue-100 text-blue-800",
  interview: "bg-yellow-100 text-yellow-800",
  offer: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
}
const STATUS_ORDER = ["applied", "interview", "offer", "rejected"]

export default function ApplicationTracker() {
  const [apps, setApps] = useState<Application[]>([])
  const [jobs, setJobs] = useState<Record<number, Job>>({})
  const [loading, setLoading] = useState(true)
  const [expandedApp, setExpandedApp] = useState<number | null>(null)
  const [historyMap, setHistoryMap] = useState<Record<number, StatusEntry[]>>({})

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    try {
      const appData = await api.listApplications()
      const appList = Array.isArray(appData) ? appData : []
      setApps(appList)
      const jobMap: Record<number, Job> = {}
      // Fetch all jobs in parallel instead of N+1
      const uniqueJobIds = [...new Set(appList.map((a) => a.job_id))]
      await Promise.all(
        uniqueJobIds.map(async (jobId) => {
          try { jobMap[jobId] = await api.getJob(jobId) }
          catch { jobMap[jobId] = { id: jobId, title: "Unknown", company: "Unknown", match_score: null, parsed_data: "{}", match_breakdown: null } }
        })
      )
      setJobs(jobMap)
    } catch { /* silent */ } finally { setLoading(false) }
  }

  const handleStatusChange = async (appId: number, newStatus: string) => {
    try {
      await api.updateApplicationStatus(appId, newStatus)
      loadData()
    } catch (e) { toast.error(e instanceof Error ? e.message : "Failed to update status") }
  }

  const toggleExpand = async (appId: number) => {
    if (expandedApp === appId) { setExpandedApp(null); return }
    setExpandedApp(appId)
    if (!historyMap[appId]) {
      try {
        const h = await api.getApplicationHistory(appId)
        setHistoryMap((prev) => ({ ...prev, [appId]: Array.isArray(h) ? h : [] }))
      } catch {
        setHistoryMap((prev) => ({ ...prev, [appId]: [] }))
      }
    }
  }

  if (loading) return <p className="text-muted-foreground">Loading...</p>
  if (apps.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl mb-3">&#128203;</div>
        <p className="text-muted-foreground">No applications yet. Generate a resume and click "Apply & Track".</p>
      </div>
    )
  }

  const grouped = STATUS_ORDER.reduce((acc, status) => {
    acc[status] = apps.filter((a) => a.status === status)
    return acc
  }, {} as Record<string, Application[]>)

  // Stats
  const total = apps.length
  const interviews = grouped.interview.length
  const offers = grouped.offer.length

  return (
    <div>
      {/* Stats bar */}
      <div className="flex gap-4 mb-6">
        <div className="p-3 bg-muted rounded-lg text-center flex-1">
          <div className="text-2xl font-bold">{total}</div>
          <div className="text-xs text-muted-foreground">Total</div>
        </div>
        <div className="p-3 bg-blue-50 rounded-lg text-center flex-1">
          <div className="text-2xl font-bold text-blue-700">{interviews}</div>
          <div className="text-xs text-muted-foreground">Interviews</div>
        </div>
        <div className="p-3 bg-blue-100/50 rounded-lg text-center flex-1">
          <div className="text-2xl font-bold text-blue-800">{offers}</div>
          <div className="text-xs text-muted-foreground">Offers</div>
        </div>
      </div>

      {/* Kanban */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {STATUS_ORDER.map((status) => (
          <div key={status}>
            <div className="flex items-center gap-2 mb-3">
              <Badge className={STATUS_COLORS[status]}>{status}</Badge>
              <span className="text-sm text-muted-foreground">{grouped[status].length}</span>
            </div>
            <div className="space-y-2">
              {grouped[status].map((app) => {
                const job = jobs[app.job_id] || {}
                const isExpanded = expandedApp === app.id
                return (
                  <Card key={app.id} className="hover:shadow-sm transition-shadow">
                    <CardContent className="py-3 px-4">
                      <div className="cursor-pointer" onClick={() => toggleExpand(app.id)}>
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium text-sm">{job.title || "Unknown"}</span>
                          {app.resume_id && app.cover_letter_id && (
                            <span className="text-xs" title="Auto-launched">{"\uD83D\uDE80"}</span>
                          )}
                        </div>
                        <div className="text-xs text-muted-foreground">{job.company || ""}</div>
                      </div>

                      {isExpanded && (
                        <div className="mt-3 pt-3 border-t space-y-2">
                          {/* Linked docs */}
                          <div className="flex gap-1 flex-wrap">
                            {app.resume_id && <Badge variant="outline" className="text-xs">Resume #{app.resume_id}</Badge>}
                            {app.cover_letter_id && <Badge variant="outline" className="text-xs">CL #{app.cover_letter_id}</Badge>}
                          </div>

                          {/* Timeline */}
                          {(historyMap[app.id] || []).length > 0 && (
                            <div className="text-xs space-y-1">
                              <p className="font-medium">Timeline:</p>
                              {(historyMap[app.id] || []).map((h, i) => (
                                <div key={i} className="flex items-center gap-2">
                                  <span className="w-2 h-2 rounded-full bg-primary" />
                                  <span>{h.status}</span>
                                  <span className="text-muted-foreground">{new Date(h.changed_at).toLocaleDateString()}</span>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Notes placeholder */}
                          <p className="text-xs text-muted-foreground italic">
                            {app.notes || "No notes (coming soon)"}
                          </p>

                          {/* Status change buttons */}
                          <div className="flex gap-1 flex-wrap">
                            {STATUS_ORDER.filter((s) => s !== status).map((s) => (
                              <Button key={s} variant="ghost" size="sm" className="text-xs h-6 px-2"
                                onClick={() => handleStatusChange(app.id, s)}>
                                → {s}
                              </Button>
                            ))}
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
