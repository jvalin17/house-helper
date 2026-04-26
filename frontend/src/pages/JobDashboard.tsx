import { useState } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import JobSearchTab from "@/components/tabs/JobSearchTab"
import ResumeBuilderTab from "@/components/tabs/ResumeBuilderTab"
import DashboardTab from "@/components/tabs/DashboardTab"
import SettingsTab from "@/components/tabs/SettingsTab"

export default function JobDashboard() {
  const [activeTab, setActiveTab] = useState("search")
  const [refreshKey, setRefreshKey] = useState(0)

  const refresh = () => setRefreshKey((k) => k + 1)

  return (
    <div className="min-h-screen p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Job Agent</h1>
          <p className="text-muted-foreground text-sm">Auto search, build, apply, track</p>
        </div>
        <a href="/" className="text-sm text-muted-foreground hover:text-foreground">
          ← All Agents
        </a>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-6">
          <TabsTrigger value="search">Job Search</TabsTrigger>
          <TabsTrigger value="lab">Superpower Lab</TabsTrigger>
          <TabsTrigger value="dashboard">Dashboard</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="search">
          <JobSearchTab key={refreshKey} onApplied={refresh} />
        </TabsContent>

        <TabsContent value="lab">
          <ResumeBuilderTab key={refreshKey} />
        </TabsContent>

        <TabsContent value="dashboard">
          <DashboardTab key={refreshKey} />
        </TabsContent>

        <TabsContent value="settings">
          <SettingsTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
