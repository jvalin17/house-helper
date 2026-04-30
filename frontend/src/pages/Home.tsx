import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { api } from "@/api/client"
import type { AppStats } from "@/types"

const agents = [
  {
    id: "job",
    title: "Jobsmith",
    description: "Find jobs, generate tailored resumes & cover letters, track applications",
    icon: "\uD83D\uDCBC",
    ready: true,
    status: "Active",
  },
  {
    id: "apartments",
    title: "Apartment Agent",
    description: "Search and compare apartments, track applications",
    icon: "\uD83C\uDFE0",
    ready: false,
    status: "Coming soon",
  },
  {
    id: "recipes",
    title: "Recipe Agent",
    description: "Find recipes based on ingredients you have",
    icon: "\uD83C\uDF73",
    ready: false,
    status: "Coming soon",
  },
  {
    id: "travel",
    title: "Travel Agent",
    description: "Plan trips, find deals, manage itineraries",
    icon: "\u2708\uFE0F",
    ready: false,
    status: "Coming soon",
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
      <h1 className="text-4xl font-bold mb-2">Panini</h1>
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

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl w-full">
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
                {agent.description}
              </CardDescription>
              <span className={`inline-block mt-2 text-xs px-2 py-0.5 rounded-full ${
                agent.ready
                  ? "bg-green-50 text-green-700"
                  : "bg-muted text-muted-foreground"
              }`}>
                {agent.status}
              </span>
            </CardHeader>
          </Card>
        ))}

        {/* Add Agent card */}
        <Card className="cursor-pointer transition-all hover:shadow-lg hover:-translate-y-1 border-dashed"
          onClick={() => window.open("https://github.com/jvalin17/house-helper/issues/new?title=Agent+Request:+&labels=agent-request", "_blank")}>
          <CardHeader className="text-center">
            <div className="text-4xl mb-3 text-muted-foreground">+</div>
            <CardTitle className="text-muted-foreground">Request Agent</CardTitle>
            <CardDescription>
              Suggest a new AI agent you'd like to see
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    </div>
  )
}
