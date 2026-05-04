import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { api } from "@/api/client"
import BudgetCard from "@/components/settings/BudgetCard"

interface ServiceCredential {
  service_name: string
  category: string
  display_name: string
  signup_url: string | null
  description: string | null
  is_configured: number
  is_enabled: number
}

export default function GlobalSettings() {
  const navigate = useNavigate()
  const [services, setServices] = useState<ServiceCredential[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedService, setExpandedService] = useState<string | null>(null)
  const [keyInput, setKeyInput] = useState("")
  const [currentUsage, setCurrentUsage] = useState<Record<string, unknown>>({})

  useEffect(() => { loadAll() }, [])

  const loadAll = async () => {
    try {
      const [credentialsData, budgetData] = await Promise.all([
        api.getAllCredentials(),
        api.getBudget(),
      ])
      setServices(Array.isArray(credentialsData) ? credentialsData : [])
      setCurrentUsage(budgetData)
    } catch { /* partial load ok */ }
    finally { setLoading(false) }
  }

  const handleSaveKey = async (serviceName: string) => {
    try {
      await api.saveCredential(serviceName, keyInput.trim())
      toast.success(`${serviceName} connected`)
      setExpandedService(null)
      setKeyInput("")
      loadAll()
    } catch { toast.error("Failed to save API key") }
  }

  const handleDeleteKey = async (serviceName: string) => {
    try {
      await api.deleteCredential(serviceName)
      toast.success("API key removed")
      loadAll()
    } catch { toast.error("Failed to remove key") }
  }

  const aiProviders = services.filter(service => service.category === "ai_provider")
  const dataSources = services.filter(service => service.category === "data_source")
  const customSources = services.filter(service => service.category === "custom")

  if (loading) return <div className="min-h-screen flex items-center justify-center"><p className="text-gray-400">Loading settings...</p></div>

  const usageCost = (currentUsage as Record<string, unknown>)?.usage as Record<string, unknown> | undefined
  const totalCost = (usageCost?.total_cost as number) || 0

  return (
    <div className="min-h-screen bg-gray-50/50">
      {/* Header */}
      <div className="border-b bg-white shadow-sm">
        <div className="max-w-4xl mx-auto px-6 py-5">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate("/")} className="text-gray-400 hover:text-gray-600">
              ← Home
            </Button>
            <div>
              <h1 className="text-xl font-semibold tracking-tight text-gray-800">Panini Settings</h1>
              <p className="text-xs text-gray-400">API keys and budget — shared across all agents</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto p-6 space-y-6">
        {/* AI Providers */}
        <div className="rounded-2xl bg-white border shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-1">AI Providers</h2>
          <p className="text-xs text-gray-400 mb-4">Connect an AI provider for resume generation, property analysis, and Q&A</p>
          <div className="space-y-2">
            {aiProviders.map(service => (
              <ServiceRow
                key={service.service_name}
                service={service}
                isExpanded={expandedService === service.service_name}
                keyInput={keyInput}
                onToggleExpand={() => {
                  setExpandedService(expandedService === service.service_name ? null : service.service_name)
                  setKeyInput("")
                }}
                onKeyInputChange={setKeyInput}
                onSave={() => handleSaveKey(service.service_name)}
                onDelete={() => handleDeleteKey(service.service_name)}
              />
            ))}
          </div>
        </div>

        {/* Data Sources */}
        <div className="rounded-2xl bg-white border shadow-sm p-6">
          <h2 className="text-lg font-semibold text-gray-800 mb-1">Data Sources</h2>
          <p className="text-xs text-gray-400 mb-4">Connect data APIs — used automatically by any agent that needs them</p>
          <div className="space-y-2">
            {dataSources.map(service => (
              <ServiceRow
                key={service.service_name}
                service={service}
                isExpanded={expandedService === service.service_name}
                keyInput={keyInput}
                onToggleExpand={() => {
                  setExpandedService(expandedService === service.service_name ? null : service.service_name)
                  setKeyInput("")
                }}
                onKeyInputChange={setKeyInput}
                onSave={() => handleSaveKey(service.service_name)}
                onDelete={() => handleDeleteKey(service.service_name)}
              />
            ))}
          </div>
        </div>

        {/* Custom Sources */}
        {customSources.length > 0 && (
          <div className="rounded-2xl bg-white border shadow-sm p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-1">Custom Sources</h2>
            <div className="space-y-2">
              {customSources.map(service => (
                <ServiceRow
                  key={service.service_name}
                  service={service}
                  isExpanded={expandedService === service.service_name}
                  keyInput={keyInput}
                  onToggleExpand={() => {
                    setExpandedService(expandedService === service.service_name ? null : service.service_name)
                    setKeyInput("")
                  }}
                  onKeyInputChange={setKeyInput}
                  onSave={() => handleSaveKey(service.service_name)}
                  onDelete={() => handleDeleteKey(service.service_name)}
                />
              ))}
            </div>
          </div>
        )}

        {/* Budget */}
        <BudgetCard
          todayCost={totalCost}
          alltimeCost={((currentUsage as Record<string, unknown>)?.alltime as Record<string, number>)?.total_cost || 0}
          breakdown={(usageCost?.breakdown || {}) as Record<string, { tokens: number; cost: number }>}
          dailyLimit={(((currentUsage as Record<string, unknown>)?.budget as Record<string, unknown>)?.daily_limit_cost as number) || null}
          onLimitSaved={loadAll}
        />
      </div>
    </div>
  )
}

function ServiceRow({ service, isExpanded, keyInput, onToggleExpand, onKeyInputChange, onSave, onDelete }: {
  service: ServiceCredential
  isExpanded: boolean
  keyInput: string
  onToggleExpand: () => void
  onKeyInputChange: (value: string) => void
  onSave: () => void
  onDelete: () => void
}) {
  const isConfigured = service.is_configured === 1

  return (
    <div className="border rounded-lg overflow-hidden">
      <div className="flex items-center justify-between p-3">
        <div className="flex items-center gap-3">
          <div className={`w-2 h-2 rounded-full ${isConfigured ? "bg-green-500" : "bg-gray-300"}`} />
          <div>
            <span className="text-sm font-medium text-gray-800">{service.display_name}</span>
            {isConfigured && <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-green-50 text-green-700">Connected</span>}
            {service.description && (
              <p className="text-xs text-gray-400">{service.description}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isConfigured && (
            <button onClick={onDelete} className="text-xs text-gray-400 hover:text-red-500 transition-colors">Remove</button>
          )}
          <Button variant="outline" size="sm" onClick={onToggleExpand}>
            {isExpanded ? "Cancel" : isConfigured ? "Update" : "Connect"}
          </Button>
        </div>
      </div>

      {isExpanded && (
        <div className="px-3 pb-3 border-t bg-gray-50/50 space-y-2">
          {service.signup_url && (
            <p className="text-xs text-gray-400 pt-2">
              Get your key from <a href={service.signup_url} target="_blank" rel="noreferrer" className="text-purple-600 hover:underline">{service.display_name}</a>
            </p>
          )}
          <Input type="password" placeholder="Paste your API key"
            value={keyInput} onChange={(event) => onKeyInputChange(event.target.value)} />
          <Button size="sm" className="bg-purple-600 hover:bg-purple-700 text-white"
            onClick={onSave} disabled={!keyInput.trim()}>
            Save Key
          </Button>
        </div>
      )}
    </div>
  )
}
