import { useNavigate } from "react-router-dom"
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"

const agents = [
  {
    id: "job",
    title: "Job Agent",
    description: "Find jobs, generate tailored resumes & cover letters, track applications",
    icon: "briefcase",
    ready: true,
  },
  {
    id: "apartments",
    title: "Apartment Agent",
    description: "Search and compare apartments, track applications",
    icon: "home",
    ready: false,
  },
  {
    id: "recipes",
    title: "Recipe Agent",
    description: "Find recipes based on ingredients you have",
    icon: "utensils",
    ready: false,
  },
]

const icons: Record<string, string> = {
  briefcase: "\uD83D\uDCBC",
  home: "\uD83C\uDFE0",
  utensils: "\uD83C\uDF73",
}

export default function Home() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8">
      <h1 className="text-4xl font-bold mb-2">House Helper</h1>
      <p className="text-muted-foreground mb-10">Pick an agent to get started</p>

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
              <div className="text-4xl mb-3">{icons[agent.icon]}</div>
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
