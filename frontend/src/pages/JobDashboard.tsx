import { useState } from "react"
import { Tabs, TabsContent } from "@/components/ui/tabs"
import JobSearchTab from "@/components/tabs/JobSearchTab"
import ResumeBuilderTab from "@/components/tabs/ResumeBuilderTab"
import DashboardTab from "@/components/tabs/DashboardTab"
import SettingsTab from "@/components/tabs/SettingsTab"

const TABS = [
  { id: "search", label: "Job Search", icon: "\uD83D\uDD0D", description: "Find & apply" },
  { id: "lab", label: "Superpower Lab", icon: "\u26A1", description: "Resume & skills" },
  { id: "dashboard", label: "Dashboard", icon: "\uD83D\uDCCA", description: "Track progress" },
  { id: "settings", label: "Settings", icon: "\u2699\uFE0F", description: "Configure" },
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
              <h1 className="text-2xl font-bold tracking-tight">House Helper</h1>
              <p className="text-sm text-muted-foreground">Your career copilot</p>
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
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 text-sm font-medium rounded-t-lg transition-all ${
                  activeTab === tab.id
                    ? "bg-blue-50 text-blue-800 border-b-2 border-blue-600"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                }`}
              >
                <span className="text-base">{tab.icon}</span>
                <span className="hidden sm:inline">{tab.label}</span>
                <span className="hidden lg:inline text-xs font-normal text-muted-foreground">
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
            <JobSearchTab key={refreshKey} onApplied={refresh} onGoToDashboard={() => { refresh(); setActiveTab("dashboard") }} />
          </TabsContent>

          <TabsContent value="lab" className="mt-0">
            <ResumeBuilderTab key={refreshKey} />
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
