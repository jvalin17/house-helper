import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { api } from "@/api/client"
import AgentProviderPicker from "@/components/settings/AgentProviderPicker"
import BudgetCard from "@/components/settings/BudgetCard"
import type { ModelInfo } from "@/types"

export default function ApartmentSettingsTab() {
  // LLM provider + model selection (no API key — managed in global settings)
  const [providers, setProviders] = useState<string[]>([])
  const [models, setModels] = useState<Record<string, ModelInfo[]>>({})
  const [provider, setProvider] = useState("")
  const [model, setModel] = useState("")
  const [llmMessage, setLlmMessage] = useState("")
  const [llmStatus, setLlmStatus] = useState<{ active: boolean; provider: string | null; model: string | null }>({
    active: false, provider: null, model: null,
  })

  // Budget
  const [currentUsage, setCurrentUsage] = useState<Record<string, unknown>>({})

  // Search preferences
  const [preferences, setPreferences] = useState({
    location: "", max_price: "", min_bedrooms: "",
    must_haves: "", layout_requirements: "",
  })

  const [loading, setLoading] = useState(true)

  useEffect(() => { loadAll() }, [])

  const loadAll = async () => {
    try {
      const [llmConfig, providerList, modelData, status, budget, prefs] = await Promise.all([
        api.getLLMConfig(),
        api.getLLMProviders(),
        api.getLLMModels(),
        api.getLLMStatus(),
        api.getBudget(),
        api.getApartmentPreferences(),
      ])
      setProviders((providerList as { providers: string[] }).providers || [])
      setModels(modelData as Record<string, ModelInfo[]>)
      setProvider((llmConfig as Record<string, string>).provider || "")
      setModel((llmConfig as Record<string, string>).model || "")
      setLlmStatus(status)
      setCurrentUsage(budget)
      setPreferences({
        location: (prefs as Record<string, string>).location || "",
        max_price: String((prefs as Record<string, number>).max_price || ""),
        min_bedrooms: String((prefs as Record<string, number>).min_bedrooms || ""),
        must_haves: ((prefs as Record<string, string[]>).must_haves || []).join(", "),
        layout_requirements: ((prefs as Record<string, string[]>).layout_requirements || []).join(", "),
      })
    } catch { /* partial load ok */ }
    finally { setLoading(false) }
  }

  const handleSaveLLM = async () => {
    setLlmMessage("")
    try {
      const config: Record<string, string> = { provider }
      if (model) config.model = model
      await api.saveLLM(config)
      setLlmMessage("Saved and active.")
      loadAll()
    } catch { setLlmMessage("Failed to save") }
  }

  const handleSavePreferences = async () => {
    try {
      await api.saveApartmentPreferences({
        location: preferences.location || null,
        max_price: preferences.max_price ? parseFloat(preferences.max_price) : null,
        min_bedrooms: preferences.min_bedrooms ? parseInt(preferences.min_bedrooms) : null,
        must_haves: preferences.must_haves ? preferences.must_haves.split(",").map(item => item.trim()).filter(Boolean) : [],
        layout_requirements: preferences.layout_requirements ? preferences.layout_requirements.split(",").map(item => item.trim()).filter(Boolean) : [],
      })
      toast.success("Preferences saved")
    } catch { toast.error("Failed to save preferences") }
  }

  if (loading) return <p className="text-muted-foreground">Loading settings...</p>

  const usageCost = (currentUsage as Record<string, unknown>)?.usage as Record<string, unknown> | undefined
  const totalCost = (usageCost?.total_cost as number) || 0

  return (
    <div className="space-y-6">
      {/* AI Provider + Model (no API key — managed in global Settings) */}
      <AgentProviderPicker
        providers={providers} models={models} llmStatus={llmStatus}
        selectedProvider={provider} selectedModel={model} message={llmMessage}
        themeColor="purple"
        onProviderChange={setProvider} onModelChange={setModel} onSave={handleSaveLLM}
      />

      {/* Budget */}
      <BudgetCard
        todayCost={totalCost}
        alltimeCost={((currentUsage as Record<string, unknown>)?.alltime as Record<string, number>)?.total_cost || 0}
        breakdown={(usageCost?.breakdown || {}) as Record<string, { tokens: number; cost: number }>}
        dailyLimit={(((currentUsage as Record<string, unknown>)?.budget as Record<string, unknown>)?.daily_limit_cost as number) || null}
        onLimitSaved={loadAll}
      />

      {/* Search Preferences */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Search Preferences</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-3 gap-3">
            <Input placeholder="Location (city, zip)" value={preferences.location}
              onChange={(event) => setPreferences({ ...preferences, location: event.target.value })} />
            <Input placeholder="Max price/mo" type="number" value={preferences.max_price}
              onChange={(event) => setPreferences({ ...preferences, max_price: event.target.value })} />
            <Input placeholder="Min bedrooms" type="number" value={preferences.min_bedrooms}
              onChange={(event) => setPreferences({ ...preferences, min_bedrooms: event.target.value })} />
          </div>
          <Input placeholder="Must-haves (comma-separated: elevator, parking, pool)"
            value={preferences.must_haves}
            onChange={(event) => setPreferences({ ...preferences, must_haves: event.target.value })} />
          <Input placeholder="Layout requirements (comma-separated)"
            value={preferences.layout_requirements}
            onChange={(event) => setPreferences({ ...preferences, layout_requirements: event.target.value })} />
          <Button size="sm" className="bg-purple-600 hover:bg-purple-700 text-white"
            onClick={handleSavePreferences}>
            Save Preferences
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
