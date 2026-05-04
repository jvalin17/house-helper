import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import NestSearchTab from "@/components/apartment/tabs/NestSearchTab"
import NestLabTab from "@/components/apartment/tabs/NestLabTab"
import ApartmentSettingsTab from "@/components/apartment/tabs/ApartmentSettingsTab"

const TABS = [
  { id: "search", label: "Nest Search", subtitle: "Find apartments", icon: "🔍" },
  { id: "lab", label: "Nest Lab", subtitle: "Deep analysis", icon: "🔬" },
  { id: "dashboard", label: "Dashboard", subtitle: "Shortlisted", icon: "📋" },
  { id: "settings", label: "Settings", subtitle: "Configure", icon: "⚙️" },
]

export default function ApartmentDashboard() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState("search")

  return (
    <div className="min-h-screen bg-gray-50/50">
      {/* Header */}
      <div className="border-b bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-6 pt-5 pb-0">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="sm" onClick={() => navigate("/")} className="text-gray-400 hover:text-gray-600">
                &larr; Home
              </Button>
              <div>
                <h1 className="text-xl font-semibold tracking-tight text-gray-800">NestScout</h1>
                <p className="text-xs text-gray-400">Find your perfect home</p>
              </div>
            </div>
          </div>

          <div className="flex gap-1">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex-1 flex flex-col items-center justify-center px-4 py-2.5 rounded-t-lg transition-all ${
                  activeTab === tab.id
                    ? "bg-white text-purple-700 border-b-2 border-orange-400"
                    : "text-gray-400 hover:text-gray-600 hover:bg-gray-50"
                }`}
              >
                <span className="text-sm font-medium">{tab.label}</span>
                <span className={`text-[11px] ${
                  activeTab === tab.id ? "text-purple-500/70" : "text-gray-300"
                }`}>
                  {tab.subtitle}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto p-6">
        <div className={activeTab === "search" ? "" : "hidden"}>
          <NestSearchTab />
        </div>
        <div className={activeTab === "lab" ? "" : "hidden"}>
          <NestLabTab />
        </div>
        <div className={activeTab === "dashboard" ? "" : "hidden"}>
          <div className="rounded-2xl bg-white border shadow-sm p-8">
            <div className="text-center py-12">
              <div className="w-16 h-16 rounded-2xl bg-purple-50 flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">📋</span>
              </div>
              <h2 className="text-lg font-semibold text-gray-800 mb-2">Dashboard</h2>
              <p className="text-sm text-gray-500 max-w-md mx-auto">
                Your shortlisted apartments with visual comparison cards, cost calculator,
                visit notes, and radar charts.
              </p>
              <p className="text-xs text-gray-300 mt-4">Coming in Phase 3</p>
            </div>
          </div>
        </div>
        <div className={activeTab === "settings" ? "" : "hidden"}>
          <ApartmentSettingsTab />
        </div>
      </div>
    </div>
  )
}
