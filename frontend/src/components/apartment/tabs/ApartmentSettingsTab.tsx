import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { api } from "@/api/client"
import ProviderCard from "@/components/settings/ProviderCard"
import BudgetCard from "@/components/settings/BudgetCard"
import type { ModelInfo } from "@/types"

interface ApartmentSource {
  id: string
  name: string
  signup?: string
  free_tier?: string
  is_custom: boolean
  enabled: boolean
  requires_api_key?: boolean
  api_url?: string
  has_api_key?: boolean
  is_connected?: boolean
}

export default function ApartmentSettingsTab() {
  // LLM settings (shared with Jobsmith)
  const [providers, setProviders] = useState<string[]>([])
  const [models, setModels] = useState<Record<string, ModelInfo[]>>({})
  const [provider, setProvider] = useState("")
  const [model, setModel] = useState("")
  const [apiKey, setApiKey] = useState("")
  const [baseUrl, setBaseUrl] = useState("")
  const [llmMessage, setLlmMessage] = useState("")
  const [llmStatus, setLlmStatus] = useState<{ active: boolean; provider: string | null; model: string | null }>({
    active: false, provider: null, model: null,
  })

  // Budget (shared)
  const [currentUsage, setCurrentUsage] = useState<Record<string, unknown>>({})

  // Apartment sources
  const [apartmentSources, setApartmentSources] = useState<ApartmentSource[]>([])
  const [showAddSource, setShowAddSource] = useState(false)
  const [newSourceName, setNewSourceName] = useState("")
  const [newSourceUrl, setNewSourceUrl] = useState("")
  const [newSourceApiKey, setNewSourceApiKey] = useState("")
  const [expandedSourceId, setExpandedSourceId] = useState<string | null>(null)
  const [sourceApiKeyInput, setSourceApiKeyInput] = useState("")

  // Search preferences
  const [preferences, setPreferences] = useState({
    location: "", max_price: "", min_bedrooms: "",
    must_haves: "", layout_requirements: "",
  })

  const [loading, setLoading] = useState(true)

  useEffect(() => { loadAll() }, [])

  const loadAll = async () => {
    try {
      const [llmConfig, providerList, modelData, status, budget, sources, prefs] = await Promise.all([
        api.getLLMConfig(),
        api.getLLMProviders(),
        api.getLLMModels(),
        api.getLLMStatus(),
        api.getBudget(),
        api.listApartmentSources(),
        api.getApartmentPreferences(),
      ])
      setProviders((providerList as { providers: string[] }).providers || [])
      setModels(modelData as Record<string, ModelInfo[]>)
      setProvider((llmConfig as Record<string, string>).provider || "")
      setModel((llmConfig as Record<string, string>).model || "")
      setBaseUrl((llmConfig as Record<string, string>).base_url || "")
      setLlmStatus(status)
      setCurrentUsage(budget)
      setApartmentSources(Array.isArray(sources) ? sources : [])
      setPreferences({
        location: (prefs as Record<string, string>).location || "",
        max_price: String((prefs as Record<string, number>).max_price || ""),
        min_bedrooms: String((prefs as Record<string, number>).min_bedrooms || ""),
        must_haves: ((prefs as Record<string, string[]>).must_haves || []).join(", "),
        layout_requirements: ((prefs as Record<string, string[]>).layout_requirements || []).join(", "),
      })
    } catch {
      /* partial load is OK */
    } finally {
      setLoading(false)
    }
  }

  const handleSaveLLM = async () => {
    setLlmMessage("")
    try {
      const config: Record<string, string> = { provider }
      if (model) config.model = model
      if (baseUrl) config.base_url = baseUrl
      if (apiKey) config.api_key = apiKey
      await api.saveLLM(config)
      setLlmMessage("Saved and active.")
      setApiKey("")
      loadAll()
    } catch {
      setLlmMessage("Failed to save")
    }
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
    } catch {
      toast.error("Failed to save preferences")
    }
  }

  const handleAddSource = async () => {
    if (!newSourceName.trim() || !newSourceUrl.trim()) {
      toast.error("Name and URL required")
      return
    }
    try {
      await api.addApartmentSource({
        name: newSourceName.trim(),
        api_url: newSourceUrl.trim(),
        api_key: newSourceApiKey.trim() || undefined,
      })
      toast.success(`Added ${newSourceName}`)
      setNewSourceName("")
      setNewSourceUrl("")
      setNewSourceApiKey("")
      setShowAddSource(false)
      loadAll()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to add source")
    }
  }

  if (loading) return <p className="text-muted-foreground">Loading settings...</p>

  const usageCost = (currentUsage as Record<string, unknown>)?.usage as Record<string, unknown> | undefined
  const totalCost = (usageCost?.total_cost as number) || 0

  return (
    <div className="space-y-6">
      {/* LLM Provider (shared with Jobsmith) */}
      <ProviderCard
        providers={providers} models={models} llmStatus={llmStatus}
        provider={provider} model={model} apiKey={apiKey} baseUrl={baseUrl} message={llmMessage}
        themeColor="purple"
        onProviderChange={setProvider} onModelChange={setModel}
        onApiKeyChange={setApiKey} onBaseUrlChange={setBaseUrl} onSave={handleSaveLLM}
      />

      {/* AI Budget (shared) */}
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
          <Input placeholder="Layout requirements (comma-separated: kitchen not sharing wall with bathroom)"
            value={preferences.layout_requirements}
            onChange={(event) => setPreferences({ ...preferences, layout_requirements: event.target.value })} />
          <Button size="sm" className="bg-purple-600 hover:bg-purple-700 text-white" onClick={handleSavePreferences}>Save Preferences</Button>
        </CardContent>
      </Card>

      {/* Data Sources — managed in global settings */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg">Apartment Sources</CardTitle>
          <Badge className="bg-purple-50 text-purple-700 border-purple-200">
            {apartmentSources.filter(source => source.enabled).length}/{apartmentSources.length} active
          </Badge>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {apartmentSources.map((source) => (
              <div key={source.id} className="border rounded-lg overflow-hidden">
                <div className={`flex items-center justify-between p-3 ${!source.enabled ? "opacity-50" : ""}`}>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={async () => {
                        const newEnabled = !source.enabled
                        if (source.is_custom) {
                          await api.toggleApartmentSource(source.id, newEnabled)
                        }
                        setApartmentSources(previous =>
                          previous.map(prevSource => prevSource.id === source.id ? { ...prevSource, enabled: newEnabled } : prevSource)
                        )
                      }}
                      className={`w-10 h-5 rounded-full transition-colors relative ${source.enabled ? "bg-purple-500" : "bg-gray-300"}`}
                      aria-label={`Toggle ${source.name}`}
                    >
                      <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${source.enabled ? "left-5" : "left-0.5"}`} />
                    </button>
                    <div>
                      <div className="text-sm font-medium">
                        {source.name}
                        {source.is_custom && <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-amber-50 text-amber-700">Custom</span>}
                        {source.is_connected && <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-green-50 text-green-700">Connected</span>}
                      </div>
                      <div className="text-xs text-muted-foreground">
                        {source.is_custom ? source.api_url : source.free_tier}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {source.is_custom ? (
                      <Button variant="ghost" size="sm" className="text-destructive" aria-label={`Delete ${source.name}`}
                        onClick={async () => {
                          await api.deleteApartmentSource(source.id)
                          toast.success(`Removed ${source.name}`)
                          loadAll()
                        }}>Delete</Button>
                    ) : source.requires_api_key ? (
                      <Button variant="outline" size="sm"
                        onClick={() => {
                          setExpandedSourceId(expandedSourceId === source.id ? null : source.id)
                          setSourceApiKeyInput("")
                        }}>
                        {source.is_connected ? "Update Key" : "Connect"}
                      </Button>
                    ) : null}
                  </div>
                </div>
                {expandedSourceId === source.id && (
                  <div className="px-3 pb-3 border-t bg-muted/30 space-y-2">
                    <p className="text-xs text-muted-foreground pt-2">
                      Get your API key from <a href={source.signup || "#"} target="_blank" rel="noreferrer" className="text-purple-600 hover:underline">{source.name}</a>
                    </p>
                    <Input
                      type="password"
                      placeholder="Paste your API key"
                      value={sourceApiKeyInput}
                      onChange={(event) => setSourceApiKeyInput(event.target.value)}
                    />
                    <div className="flex gap-2">
                      <Button size="sm" className="bg-purple-600 hover:bg-purple-700 text-white" onClick={async () => {
                        try {
                          await api.saveApartmentSourceApiKey(source.id, sourceApiKeyInput)
                          toast.success(`${source.name} connected`)
                          setExpandedSourceId(null)
                          setSourceApiKeyInput("")
                          loadAll()
                        } catch {
                          toast.error("Failed to save API key")
                        }
                      }}>Save Key</Button>
                      <Button size="sm" variant="ghost" onClick={() => setExpandedSourceId(null)}>Cancel</Button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {showAddSource ? (
            <div className="mt-4 p-3 border border-dashed rounded-lg space-y-2">
              <Input placeholder="Source name (e.g., RentCast)" value={newSourceName}
                onChange={(event) => setNewSourceName(event.target.value)} />
              <Input placeholder="API URL" value={newSourceUrl}
                onChange={(event) => setNewSourceUrl(event.target.value)} />
              <Input type="password" placeholder="API key (optional)" value={newSourceApiKey}
                onChange={(event) => setNewSourceApiKey(event.target.value)} />
              <div className="flex gap-2">
                <Button size="sm" className="bg-purple-600 hover:bg-purple-700 text-white" onClick={handleAddSource}>Save Source</Button>
                <Button size="sm" variant="ghost" onClick={() => setShowAddSource(false)}>Cancel</Button>
              </div>
            </div>
          ) : (
            <div className="mt-4">
              <Button variant="outline" size="sm"
                className="border-purple-200 text-purple-600 hover:bg-purple-50"
                disabled={apartmentSources.filter(source => source.is_custom).length >= 5}
                onClick={() => setShowAddSource(true)}>
                + Add Source
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
