import { useState } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import JobInput from "@/components/JobInput"
import JobList from "@/components/JobList"
import ApplicationTracker from "@/components/ApplicationTracker"
import KnowledgeBank from "@/components/KnowledgeBank"

export default function JobDashboard() {
  const [activeTab, setActiveTab] = useState("jobs")
  const [refreshKey, setRefreshKey] = useState(0)

  const refresh = () => setRefreshKey((k) => k + 1)

  return (
    <div className="min-h-screen p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Job Agent</h1>
          <p className="text-muted-foreground text-sm">Find, match, apply</p>
        </div>
        <a href="/" className="text-sm text-muted-foreground hover:text-foreground">
          ← All Agents
        </a>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-6">
          <TabsTrigger value="jobs">Jobs</TabsTrigger>
          <TabsTrigger value="tracker">Tracker</TabsTrigger>
          <TabsTrigger value="knowledge">Knowledge Bank</TabsTrigger>
        </TabsList>

        <TabsContent value="jobs">
          <JobInput onJobsParsed={refresh} />
          <JobList key={refreshKey} />
        </TabsContent>

        <TabsContent value="tracker">
          <ApplicationTracker key={refreshKey} />
        </TabsContent>

        <TabsContent value="knowledge">
          <KnowledgeBank key={refreshKey} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
