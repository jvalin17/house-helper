import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { api } from "@/api/client"
import type { AppStats } from "@/types"

const agents = [
  {
    id: "job",
    title: "Job Agent",
    description: "Find jobs, generate tailored resumes & cover letters, track applications",
    icon: "\uD83D\uDCBC",
    ready: true,
  },
  {
    id: "apartments",
    title: "Apartment Agent",
    description: "Search and compare apartments, track applications",
    icon: "\uD83C\uDFE0",
    ready: false,
  },
  {
    id: "recipes",
    title: "Recipe Agent",
    description: "Find recipes based on ingredients you have",
    icon: "\uD83C\uDF73",
    ready: false,
  },
]

export default function Home() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<AppStats>({ jobs: 0, applications: 0, skills: 0 })

  useEffect(() => {
    api.getStats().then(setStats).catch(() => {})
  }, [])

  const hasActivity = stats.jobs > 0 || stats.applications > 0 || stats.skills > 0

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold mb-2">House Helper</h1>
      <p className="text-muted-foreground mb-8">Your personal AI assistant</p>

      {/* Quick Stats */}
      {hasActivity && (
        <div className="flex gap-4 mb-8">
          <div className="text-center px-6 py-3 bg-muted rounded-lg">
            <div className="text-xl font-bold">{stats.jobs}</div>
            <div className="text-xs text-muted-foreground">Jobs Tracked</div>
          </div>
          <div className="text-center px-6 py-3 bg-muted rounded-lg">
            <div className="text-xl font-bold">{stats.applications}</div>
            <div className="text-xs text-muted-foreground">Applications</div>
          </div>
          <div className="text-center px-6 py-3 bg-muted rounded-lg">
            <div className="text-xl font-bold">{stats.skills}</div>
            <div className="text-xs text-muted-foreground">Skills</div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl w-full">
        {agents.map((agent) => (
          <Card
            key={agent.id}
            className={`cursor-pointer transition-all hover:shadow-lg hover:-translate-y-1 ${
              agent.ready ? "" : "opacity-50 pointer-events-none"
            }`}
            onClick={() => agent.ready && navigate(`/${agent.id}`)}
          >
            <CardHeader className="text-center">
              <div className="text-4xl mb-3">{agent.icon}</div>
              <CardTitle>{agent.title}</CardTitle>
              <CardDescription>
                {agent.ready ? agent.description : "Coming soon"}
              </CardDescription>
            </CardHeader>
          </Card>
        ))}
      </div>
    </div>
  )
}
