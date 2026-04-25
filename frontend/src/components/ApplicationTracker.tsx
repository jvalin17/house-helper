import { useEffect, useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { api } from "@/api/client"

interface Application {
  id: number
  job_id: number
  status: string
  resume_id: number | null
  cover_letter_id: number | null
  created_at: string
}

const STATUS_COLORS: Record<string, string> = {
  applied: "bg-blue-100 text-blue-800",
  interview: "bg-yellow-100 text-yellow-800",
  offer: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
}

const STATUS_ORDER = ["applied", "interview", "offer", "rejected"]

export default function ApplicationTracker() {
  const [apps, setApps] = useState<Application[]>([])
  const [jobs, setJobs] = useState<Record<number, Record<string, unknown>>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const appData = await api.listApplications() as unknown as Application[]
      setApps(appData)

      const jobMap: Record<number, Record<string, unknown>> = {}
      for (const app of appData) {
        if (!jobMap[app.job_id]) {
          try {
            jobMap[app.job_id] = await api.getJob(app.job_id) as Record<string, unknown>
          } catch {
            jobMap[app.job_id] = { title: "Unknown", company: "Unknown" }
          }
        }
      }
      setJobs(jobMap)
    } catch {
      // handle silently
    } finally {
      setLoading(false)
    }
  }

  const handleStatusChange = async (appId: number, newStatus: string) => {
    await api.updateApplicationStatus(appId, newStatus)
    loadData()
  }

  if (loading) return <p className="text-muted-foreground">Loading applications...</p>
  if (apps.length === 0) {
    return (
      <div className="text-center py-12">
        <div className="text-4xl mb-3">&#128203;</div>
        <p className="text-muted-foreground">No applications yet. Generate a resume and click "Apply & Track".</p>
      </div>
    )
  }

  // Group by status
  const grouped = STATUS_ORDER.reduce((acc, status) => {
    acc[status] = apps.filter((a) => a.status === status)
    return acc
  }, {} as Record<string, Application[]>)

  return (
    <div>
      <h2 className="text-lg font-semibold mb-4">
        {apps.length} Application{apps.length !== 1 ? "s" : ""}
      </h2>

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
                return (
                  <Card key={app.id} className="hover:shadow-sm transition-shadow">
                    <CardContent className="py-3 px-4">
                      <div className="font-medium text-sm">{String(job.title || "Unknown")}</div>
                      <div className="text-xs text-muted-foreground mb-2">{String(job.company || "")}</div>
                      <div className="flex gap-1 flex-wrap">
                        {STATUS_ORDER.filter((s) => s !== status).map((s) => (
                          <Button
                            key={s}
                            variant="ghost"
                            size="sm"
                            className="text-xs h-6 px-2"
                            onClick={() => handleStatusChange(app.id, s)}
                          >
                            → {s}
                          </Button>
                        ))}
                      </div>
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
