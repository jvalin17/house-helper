import { useState } from "react"

const TABS = [
  { id: "search", label: "Nest Search", subtitle: "Find apartments" },
  { id: "lab", label: "Nest Lab", subtitle: "Deep analysis" },
  { id: "dashboard", label: "Dashboard", subtitle: "Shortlisted" },
  { id: "settings", label: "Settings", subtitle: "Configure" },
]

export default function ApartmentDashboard() {
  const [activeTab, setActiveTab] = useState("search")

  return (
    <div className="min-h-screen">
      <div className="border-b bg-white">
        <div className="max-w-7xl mx-auto px-6 pt-5 pb-0">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h1 className="text-xl font-semibold tracking-tight">NestScout</h1>
              <p className="text-xs text-muted-foreground/60">Find your perfect home</p>
            </div>
          </div>

          <div className="flex gap-1">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 flex flex-col items-center justify-center px-4 py-2.5 rounded-t-lg transition-all ${
                  activeTab === tab.id
                    ? "bg-purple-50/60 text-purple-800 border-b-2 border-purple-500"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/30"
                }`}
              >
                <span className="text-sm font-medium">{tab.label}</span>
                <span className={`text-[11px] ${
                  activeTab === tab.id ? "text-purple-600/70" : "text-muted-foreground/50"
                }`}>
                  {tab.subtitle}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6">
        <div className={activeTab === "search" ? "" : "hidden"}>
          <div className="text-center py-20 text-muted-foreground">
            <h2 className="text-lg font-medium mb-2">Nest Search</h2>
            <p className="text-sm">Search for apartments across multiple sources. Coming in Phase 2.</p>
          </div>
        </div>
        <div className={activeTab === "lab" ? "" : "hidden"}>
          <div className="text-center py-20 text-muted-foreground">
            <h2 className="text-lg font-medium mb-2">Nest Lab</h2>
            <p className="text-sm">Deep analysis: reviews, floor plans, neighborhood intelligence. Coming in Phase 5.</p>
          </div>
        </div>
        <div className={activeTab === "dashboard" ? "" : "hidden"}>
          <div className="text-center py-20 text-muted-foreground">
            <h2 className="text-lg font-medium mb-2">Dashboard</h2>
            <p className="text-sm">Your shortlisted apartments with visual cards. Coming in Phase 3.</p>
          </div>
        </div>
        <div className={activeTab === "settings" ? "" : "hidden"}>
          <div className="text-center py-20 text-muted-foreground">
            <h2 className="text-lg font-medium mb-2">Settings</h2>
            <p className="text-sm">API keys, preferences, layout requirements. Coming in Phase 3.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
