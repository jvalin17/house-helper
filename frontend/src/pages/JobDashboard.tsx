import { useState } from "react"
import { Tabs, TabsContent } from "@/components/ui/tabs"
import JobSearchTab from "@/components/tabs/JobSearchTab"
import ResumeBuilderTab from "@/components/tabs/ResumeBuilderTab"
import DashboardTab from "@/components/tabs/DashboardTab"
import SettingsTab from "@/components/tabs/SettingsTab"

const TABS = [
  { id: "search", label: "Job Search", description: "Find & apply" },
  { id: "lab", label: "Superpower Lab", description: "Resume & skills" },
  { id: "dashboard", label: "Dashboard", description: "Track progress" },
  { id: "settings", label: "Settings", description: "Configure" },
]

export default function JobDashboard() {
  const [activeTab, setActiveTab] = useState("search")
  const [refreshKey, setRefreshKey] = useState(0)

  const refresh = () => setRefreshKey((k) => k + 1)

  return (
    <div className="min-h-screen">
      {/* Header */}
      <div className="border-b bg-white">
        <div className="max-w-7xl mx-auto px-6 pt-5 pb-0">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h1 className="text-xl font-semibold tracking-tight">Job Agent</h1>
              <p className="text-xs text-muted-foreground/60">One step at a time</p>
            </div>
            <a href="/" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
              {"\u2190"} All Agents
            </a>
          </div>

          {/* Tab bar — full width, centered, clear active state */}
          <div className="flex gap-1">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 flex flex-col items-center justify-center px-4 py-2.5 rounded-t-lg transition-all ${
                  activeTab === tab.id
                    ? "bg-blue-50/60 text-blue-800 border-b-2 border-blue-500"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/30"
                }`}
              >
                <span className="text-sm font-medium">{tab.label}</span>
                <span className={`text-[11px] ${
                  activeTab === tab.id ? "text-blue-600/60" : "text-muted-foreground/50"
                }`}>
                  {tab.description}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto p-6">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsContent value="search" className="mt-0">
            <JobSearchTab onApplied={refresh} onGoToDashboard={() => { refresh(); setActiveTab("dashboard") }} />
          </TabsContent>

          <TabsContent value="lab" className="mt-0">
            <ResumeBuilderTab />
          </TabsContent>

          <TabsContent value="dashboard" className="mt-0">
            <DashboardTab key={refreshKey} />
          </TabsContent>

          <TabsContent value="settings" className="mt-0">
            <SettingsTab />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}
