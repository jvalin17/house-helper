import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { api } from "@/api/client"
import ApplicationTracker from "@/components/ApplicationTracker"
import SavedResumes from "@/components/SavedResumes"
import type { AppStats } from "@/types"

export default function DashboardTab() {
  const [stats, setStats] = useState<AppStats>({ jobs: 0, applications: 0, skills: 0 })
  const [budgetRemaining, setBudgetRemaining] = useState("N/A")

  useEffect(() => {
    api.getStats().then(setStats).catch(() => {})
    api.getBudget().then((budgetData) => {
      const remainingCost = (budgetData as Record<string, unknown>)?.remaining_cost as number | null
      setBudgetRemaining(remainingCost != null ? `$${remainingCost.toFixed(2)}` : "No limit")
    }).catch(() => {})
  }, [])

  return (
    <div className="space-y-6">
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
            <div className="text-3xl font-bold text-blue-600">{budgetRemaining}</div>
            <div className="text-sm text-muted-foreground">Budget Left Today</div>
          </CardContent>
        </Card>
      </div>

      <SavedResumes />

      <Card>
        <CardHeader><CardTitle>Application Tracker</CardTitle></CardHeader>
        <CardContent>
          <ApplicationTracker />
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button variant="outline" size="sm" className="text-destructive"
          onClick={async () => {
            if (!confirm(`Reset dashboard? This will clear ${stats.jobs} jobs and ${stats.applications} applications.\n\nKnowledge bank, settings, templates, and saved resumes are preserved.`)) return
            try {
              const result = await api.resetDashboard()
              toast.success(`Cleared ${result.jobs_deleted} jobs, ${result.applications_deleted} applications`)
              api.getStats().then(setStats).catch(() => {})
            } catch (e) {
              toast.error(e instanceof Error ? e.message : "Reset failed")
            }
          }}>
          Reset Dashboard
        </Button>
      </div>
    </div>
  )
}
