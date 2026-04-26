import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import ApplicationTracker from "@/components/ApplicationTracker"

interface Stats {
  jobs: number; applications: number; skills: number; budget_remaining: string
}

export default function DashboardTab() {
  const [stats, setStats] = useState<Stats>({ jobs: 0, applications: 0, skills: 0, budget_remaining: "N/A" })

  useEffect(() => { loadStats() }, [])

  const loadStats = async () => {
    try {
      const [jobs, apps, skills, budget] = await Promise.all([
        fetch("/api/jobs").then((r) => r.ok ? r.json() : []),
        fetch("/api/applications").then((r) => r.ok ? r.json() : []),
        fetch("/api/knowledge/skills").then((r) => r.ok ? r.json() : []),
        fetch("/api/budget").then((r) => r.ok ? r.json() : {}),
      ]) as [unknown[], unknown[], unknown[], Record<string, unknown>]
      const rc = (budget?.remaining_cost ?? null) as number | null
      const remaining = rc != null ? `$${rc.toFixed(2)}` : "No limit"
      setStats({
        jobs: Array.isArray(jobs) ? jobs.length : 0,
        applications: Array.isArray(apps) ? apps.length : 0,
        skills: Array.isArray(skills) ? skills.length : 0,
        budget_remaining: remaining,
      })
    } catch { /* silent */ }
  }

  return (
    <div className="space-y-6">
      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="py-4 text-center">
            <div className="text-3xl font-bold">{stats.jobs}</div>
            <div className="text-sm text-muted-foreground">Jobs Found</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4 text-center">
            <div className="text-3xl font-bold">{stats.applications}</div>
            <div className="text-sm text-muted-foreground">Applications</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4 text-center">
            <div className="text-3xl font-bold">{stats.skills}</div>
            <div className="text-sm text-muted-foreground">Skills</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="py-4 text-center">
            <div className="text-3xl font-bold text-green-600">{stats.budget_remaining}</div>
            <div className="text-sm text-muted-foreground">Budget Left Today</div>
          </CardContent>
        </Card>
      </div>

      {/* Tracker */}
      <Card>
        <CardHeader><CardTitle>Application Tracker</CardTitle></CardHeader>
        <CardContent>
          <ApplicationTracker />
        </CardContent>
      </Card>
    </div>
  )
}
