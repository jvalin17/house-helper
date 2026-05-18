import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { api } from "@/api/client"
import type { HomeStats, CredentialReadiness } from "@/types"

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
    title: "NestScout",
    description: "Find apartments, compare neighborhoods, calculate real costs",
    icon: "\uD83C\uDFE0",
    ready: true,
    status: "Active",
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
  const [stats, setStats] = useState<HomeStats>({ applications: 0, homes_explored: 0, hours_saved: 0 })
  const [readiness, setReadiness] = useState<CredentialReadiness | null>(null)

  useEffect(() => {
    api.getHomeStats().then(setStats).catch(() => {})
    api.getCredentialsReadiness().then(setReadiness)
  }, [])

  const hasActivity = stats.applications > 0 || stats.homes_explored > 0
  const needsAnySetup = readiness && readiness.configured_count === 0

  const agentNeedsSetup = (agentId: string): boolean => {
    if (!readiness) return false
    if (agentId === "apartments") return !readiness.nestscout_ready
    if (agentId === "job") return !readiness.jobsmith_ready
    return false
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold mb-2">Panini</h1>
      <p className="text-muted-foreground mb-8">Your personal AI assistant</p>

      {/* Stats strip */}
      <div className="flex gap-4 mb-8">
        {needsAnySetup ? (
          <button onClick={() => navigate("/settings")}
            className="text-center px-6 py-4 bg-indigo-50 rounded-xl border border-indigo-100 hover:bg-indigo-100 transition-colors cursor-pointer">
            <div className="text-2xl font-bold text-indigo-600">Get started</div>
            <div className="text-xs text-indigo-500">Connect an API source</div>
          </button>
        ) : null}
        <div className={`text-center px-6 py-4 bg-blue-50 rounded-xl border border-blue-100 ${!hasActivity && !needsAnySetup ? "opacity-50" : ""}`}>
          <div className="text-2xl font-bold text-blue-700">{stats.applications}</div>
          <div className="text-xs text-blue-500">Applications</div>
        </div>
        <div className={`text-center px-6 py-4 bg-purple-50 rounded-xl border border-purple-100 ${!hasActivity && !needsAnySetup ? "opacity-50" : ""}`}>
          <div className="text-2xl font-bold text-purple-700">{stats.homes_explored}</div>
          <div className="text-xs text-purple-500">Homes Explored</div>
        </div>
        {!needsAnySetup && (
          <div className={`text-center px-6 py-4 bg-emerald-50 rounded-xl border border-emerald-100 ${!hasActivity ? "opacity-50" : ""}`}>
            <div className="text-2xl font-bold text-emerald-700">{stats.hours_saved}h</div>
            <div className="text-xs text-emerald-500">Time Saved</div>
          </div>
        )}
      </div>

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
              {agent.ready && agentNeedsSetup(agent.id) ? (
                <span className="inline-block mt-2 text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-700">
                  Needs setup
                </span>
              ) : !agent.ready ? (
                <span className="inline-block mt-2 text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
                  {agent.status}
                </span>
              ) : null}
            </CardHeader>
          </Card>
        ))}

        {/* Add Agent card */}
        <Card className="cursor-pointer transition-all hover:shadow-lg hover:-translate-y-1 border-dashed"
          onClick={() => window.open("https://github.com/jvalin17/panini/issues/new?title=Agent+Request:+&labels=agent-request", "_blank")}>
          <CardHeader className="text-center">
            <div className="text-4xl mb-3 text-muted-foreground">+</div>
            <CardTitle className="text-muted-foreground">Request Agent</CardTitle>
            <CardDescription>
              Suggest a new AI agent you'd like to see
            </CardDescription>
          </CardHeader>
        </Card>
      </div>

      {/* Global Settings */}
      <button onClick={() => navigate("/settings")}
        className="mt-8 text-sm text-gray-400 hover:text-gray-600 transition-colors flex items-center gap-2">
        <span>Settings</span> — API keys, budget, data sources
      </button>
    </div>
  )
}
