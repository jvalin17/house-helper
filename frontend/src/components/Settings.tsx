import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { api } from "@/api/client"
import type { JobSource, ModelInfo } from "@/types"
import ProviderCard from "@/components/settings/ProviderCard"
import BudgetCard from "@/components/settings/BudgetCard"

export default function Settings() {
  const [providers, setProviders] = useState<string[]>([])
  const [models, setModels] = useState<Record<string, ModelInfo[]>>({})
  const [weights, setWeights] = useState<Record<string, number>>({})
  const [provider, setProvider] = useState("")
  const [model, setModel] = useState("")
  const [apiKey, setApiKey] = useState("")
  const [baseUrl, setBaseUrl] = useState("")
  const [message, setMessage] = useState("")
  const [jobSources, setJobSources] = useState<JobSource[]>([])
  const [loading, setLoading] = useState(true)
  const [currentUsage, setCurrentUsage] = useState<Record<string, unknown>>({})
  const [llmStatus, setLlmStatus] = useState<{ active: boolean; provider: string | null; model: string | null }>({ active: false, provider: null, model: null })

  useEffect(() => {
    loadSettings()
    const handleFocus = () => {
      api.getBudget().then((b) => setCurrentUsage(b))
    }
    window.addEventListener("focus", handleFocus)
    const interval = setInterval(handleFocus, 15000)
    return () => { window.removeEventListener("focus", handleFocus); clearInterval(interval) }
  }, [])

  const loadSettings = async () => {
    const config = await api.getLLMConfig()
    const providerList = await api.getLLMProviders()
    const modelData = await api.getLLMModels()
    const calWeights = await api.getCalibrationWeights()
    const sources = await api.getSearchSources()
    const budget = await api.getBudget()
    const status = await api.getLLMStatus()

    setLlmStatus(status)
    setProviders(providerList.providers || [])
    setModels(modelData as Record<string, ModelInfo[]>)
    setProvider(config.provider || "")
    setModel(config.model || "")
    setBaseUrl(config.base_url || "")
    setWeights(calWeights)
    setJobSources(Array.isArray(sources) ? sources : [])
    setCurrentUsage(budget)
    setLoading(false)
  }

  const handleSaveLLM = async () => {
    setMessage("")
    try {
      const config: Record<string, string> = { provider }
      if (model) config.model = model
      if (baseUrl) config.base_url = baseUrl
      if (apiKey) config.api_key = apiKey
      await api.saveLLM(config)
      setMessage("Saved and active.")
      setApiKey("")
      loadSettings()
    } catch { setMessage("Failed to save") }
  }

  const handleRecalibrate = async () => {
    try {
      const result = await api.recalibrate()
      setWeights(result)
      setMessage("Weights recalculated")
    } catch { setMessage("No judgements yet") }
  }

  if (loading) return <p className="text-muted-foreground">Loading...</p>

  const usageCost = (currentUsage as Record<string, unknown>)?.usage as Record<string, unknown>
  const totalCost = (usageCost?.total_cost as number) || 0

  return (
    <div className="space-y-6">
      <ProviderCard
        providers={providers} models={models} llmStatus={llmStatus}
        provider={provider} model={model} apiKey={apiKey} baseUrl={baseUrl} message={message}
        onProviderChange={setProvider} onModelChange={setModel}
        onApiKeyChange={setApiKey} onBaseUrlChange={setBaseUrl} onSave={handleSaveLLM}
      />

      <BudgetCard
        todayCost={totalCost}
        alltimeCost={((currentUsage as Record<string, unknown>)?.alltime as Record<string, number>)?.total_cost || 0}
        breakdown={(usageCost?.breakdown || {}) as Record<string, { tokens: number; cost: number }>}
      />

      {/* Job Sources */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Job Sources</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            Connect job board APIs for auto-search. All sources use official APIs.
          </p>
          <div className="space-y-2">
            {jobSources.map((source) => (
              <div key={source.id} className="flex items-center justify-between p-3 border rounded-lg">
                <div>
                  <div className="text-sm font-medium">{source.name}</div>
                  <div className="text-xs text-muted-foreground">Free tier: {source.free_tier}</div>
                </div>
                <div>
                  {source.is_available ? (
                    <Badge className="bg-blue-50 text-blue-700 border-blue-200">Connected</Badge>
                  ) : source.requires_api_key ? (
                    <a href={source.signup || "#"} target="_blank" rel="noreferrer">
                      <Button variant="outline" size="sm">Get API Key</Button>
                    </a>
                  ) : (
                    <Badge className="bg-blue-50 text-blue-700 border-blue-200">Free</Badge>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Calibration */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg">Match Calibration</CardTitle>
          <Button variant="outline" size="sm" onClick={handleRecalibrate}>Recalculate</Button>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            Weights adjust based on your match ratings. Rate jobs to improve accuracy.
          </p>
          <div className="space-y-2">
            {Object.entries(weights).map(([feature, weight]) => (
              <div key={feature} className="flex items-center justify-between">
                <span className="text-sm">{feature.replace(/_/g, " ")}</span>
                <div className="flex items-center gap-2">
                  <div className="w-32 bg-muted rounded-full h-2">
                    <div className="bg-blue-500 rounded-full h-2" style={{ width: `${(weight as number) * 100}%` }} />
                  </div>
                  <span className="text-sm text-muted-foreground w-12 text-right">{Math.round((weight as number) * 100)}%</span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Offline Mode */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Offline Mode</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">Install Ollama to run AI locally for PDF import extraction. Free, no data leaves your machine.</p>
          <code className="text-xs bg-muted p-2 rounded">brew install ollama && ollama serve && ollama pull mistral</code>
        </CardContent>
      </Card>
    </div>
  )
}
