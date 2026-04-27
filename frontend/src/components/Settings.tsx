import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"

interface JobSource {
  id: string; name: string; signup: string | null
  free_tier: string; is_available: boolean; requires_api_key: boolean
}

interface ModelInfo {
  id: string; name: string; speed: string; quality: string
  input_per_1m: number; output_per_1m: number; est_per_resume: string; default?: boolean
}

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
  const [budgetLimit, setBudgetLimit] = useState("")
  const [currentUsage, setCurrentUsage] = useState<Record<string, unknown>>({})

  useEffect(() => { loadSettings() }, [])

  const loadSettings = async () => {
    try {
      const [config, providerList, modelData, calWeights, sources, budget] = await Promise.all([
        fetch("/api/settings/llm").then((r) => r.json()),
        fetch("/api/settings/llm/providers").then((r) => r.json()),
        fetch("/api/settings/llm/models").then((r) => r.ok ? r.json() : {}),
        fetch("/api/calibration/weights").then((r) => r.json()),
        fetch("/api/search/sources").then((r) => r.ok ? r.json() : []),
        fetch("/api/budget").then((r) => r.ok ? r.json() : {}),
      ])
      setProviders(providerList.providers || [])
      setModels(modelData)
      setProvider(config.provider || "")
      setModel(config.model || "")
      setBaseUrl(config.base_url || "")
      setWeights(calWeights)
      setJobSources(sources)
      const budgetData = budget as Record<string, unknown>
      const budgetConfig = budgetData?.budget as Record<string, unknown>
      if (budgetConfig?.daily_limit_cost) {
        setBudgetLimit(String(budgetConfig.daily_limit_cost))
      }
      setCurrentUsage(budget)
    } catch { /* silent */ }
    finally { setLoading(false) }
  }

  const handleSaveLLM = async () => {
    setMessage("")
    try {
      const config: Record<string, string> = { provider }
      if (model) config.model = model
      if (baseUrl) config.base_url = baseUrl
      if (apiKey) config.api_key = apiKey

      await fetch("/api/settings/llm", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      })
      setMessage("Saved. Run ./restart.sh to apply the new provider.")
      setApiKey("")
    } catch { setMessage("Failed to save") }
  }

  const handleSaveBudget = async () => {
    const limit = parseFloat(budgetLimit)
    if (isNaN(limit) && budgetLimit !== "") return
    await fetch("/api/budget", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ daily_limit_cost: budgetLimit ? limit : null }),
    })
    setMessage("Budget limit saved")
    loadSettings()
  }

  const handleRecalibrate = async () => {
    try {
      const result = await fetch("/api/calibration/recalculate", { method: "POST" }).then((r) => r.json())
      setWeights(result)
      setMessage("Weights recalculated")
    } catch { setMessage("No judgements yet") }
  }

  if (loading) return <p className="text-muted-foreground">Loading...</p>

  const providerModels = models[provider] || []
  const usageCost = (currentUsage as Record<string, unknown>)?.usage as Record<string, unknown>
  const totalCost = (usageCost?.total_cost as number) || 0

  return (
    <div className="space-y-6">
      {/* LLM Provider + Model */}
      <Card>
        <CardHeader><CardTitle className="text-lg">AI Provider</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          {/* Provider selection */}
          <div>
            <p className="text-sm font-medium mb-2">Provider</p>
            <div className="flex flex-wrap gap-2">
              {providers.map((p) => (
                <Badge key={p} variant={provider === p ? "default" : "outline"} className="cursor-pointer"
                  onClick={() => { setProvider(p); setModel(""); if (p === "ollama") setBaseUrl("http://localhost:11434") }}>
                  {p}
                </Badge>
              ))}
              <Badge variant={provider === "" ? "default" : "outline"} className="cursor-pointer"
                onClick={() => { setProvider(""); setModel("") }}>
                None (free)
              </Badge>
            </div>
          </div>

          {/* Model selection with pricing */}
          {provider && providerModels.length > 0 && (
            <div>
              <p className="text-sm font-medium mb-2">Model</p>
              <div className="space-y-2">
                {providerModels.map((m) => (
                  <div key={m.id}
                    className={`flex items-center justify-between p-2.5 rounded-lg border cursor-pointer transition-colors ${
                      model === m.id ? "border-blue-400 bg-blue-50/50" : "border-border/50 hover:border-border"
                    }`}
                    onClick={() => setModel(m.id)}>
                    <div>
                      <span className="text-sm font-medium">{m.name}</span>
                      <span className="text-xs text-muted-foreground ml-2">{m.speed} · {m.quality}</span>
                    </div>
                    <div className="text-right">
                      <div className="text-xs text-muted-foreground">
                        ${m.input_per_1m} per 1M input tokens · ${m.output_per_1m} per 1M output
                      </div>
                      <div className="text-xs font-medium">
                        Estimated ~{m.est_per_resume} per resume
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* API Key */}
          {provider && provider !== "ollama" && (
            <div>
              <p className="text-sm font-medium mb-2">API Key</p>
              <Input placeholder="Paste API key (stored locally, never shared)"
                type="password" value={apiKey} onChange={(e) => setApiKey(e.target.value)} />
              <p className="text-xs text-muted-foreground mt-1">
                {provider === "claude" ? "Get key: console.anthropic.com" : "Get key: platform.openai.com"}
              </p>
            </div>
          )}

          {(provider === "ollama" || provider === "huggingface") && (
            <Input placeholder="Base URL" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
          )}

          <Button onClick={handleSaveLLM} disabled={!provider && !model}>
            {provider ? "Save Provider" : "Clear Provider"}
          </Button>

          {message && <p className="text-sm text-muted-foreground">{message}</p>}
        </CardContent>
      </Card>

      {/* Budget Limit */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Usage Limit</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-3">
            Set a daily spending limit. The app will pause AI features when the limit is reached.
          </p>

          {/* Current usage */}
          <div className="flex items-center gap-4 mb-4 p-3 rounded-lg bg-muted/50">
            <div>
              <span className="text-sm font-medium">Today</span>
              <div className="text-2xl font-bold">${totalCost.toFixed(4)}</div>
            </div>
            {budgetLimit && (
              <>
                <div className="text-muted-foreground">/</div>
                <div>
                  <span className="text-sm font-medium">Limit</span>
                  <div className="text-2xl font-bold">${parseFloat(budgetLimit).toFixed(2)}</div>
                </div>
              </>
            )}
          </div>

          <div className="flex gap-2 items-end">
            <div className="flex-1">
              <p className="text-sm font-medium mb-1">Daily limit ($)</p>
              <Input placeholder="e.g., 1.00 (leave empty for no limit)"
                value={budgetLimit} onChange={(e) => setBudgetLimit(e.target.value)} />
            </div>
            <Button onClick={handleSaveBudget}>Set Limit</Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            {budgetLimit ? `At ~$0.006/resume, that's ~${Math.floor(parseFloat(budgetLimit) / 0.006)} resumes per day` : "No limit set — you control when to use AI features"}
          </p>
        </CardContent>
      </Card>

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

      {/* Offline + Export */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Offline Mode</CardTitle></CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">Download AI models to run locally without API keys. Requires ~500MB disk, ~2GB RAM.</p>
          <Button variant="outline" disabled>Download Models (coming soon)</Button>
        </CardContent>
      </Card>
    </div>
  )
}
