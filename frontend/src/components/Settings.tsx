import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"

export default function Settings() {
  const [llmConfig, setLlmConfig] = useState<Record<string, string | null>>({})
  const [providers, setProviders] = useState<string[]>([])
  const [weights, setWeights] = useState<Record<string, number>>({})
  const [provider, setProvider] = useState("")
  const [model, setModel] = useState("")
  const [apiKey, setApiKey] = useState("")
  const [baseUrl, setBaseUrl] = useState("")
  const [message, setMessage] = useState("")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      const [config, providerList] = await Promise.all([
        fetch("/api/settings/llm").then((r) => r.json()),
        fetch("/api/settings/llm/providers").then((r) => r.json()),
      ])
      setLlmConfig(config)
      setProviders(providerList.providers || [])
      setProvider(config.provider || "")
      setModel(config.model || "")
      setBaseUrl(config.base_url || "")

      const calWeights = await fetch("/api/calibration/weights").then((r) => r.json())
      setWeights(calWeights)
    } catch {
      // handle silently
    } finally {
      setLoading(false)
    }
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
      setMessage("LLM settings saved. Restart the backend to apply.")
      setApiKey("")
    } catch {
      setMessage("Failed to save settings")
    }
  }

  const handleRecalibrate = async () => {
    try {
      const result = await fetch("/api/calibration/recalculate", { method: "POST" }).then((r) => r.json())
      setWeights(result)
      setMessage("Weights recalculated from your judgements")
    } catch {
      setMessage("No judgements to recalibrate from")
    }
  }

  if (loading) return <p className="text-muted-foreground">Loading settings...</p>

  return (
    <div className="space-y-6">
      {/* LLM Provider */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">LLM Provider</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            Configure an LLM for AI-powered resume and cover letter generation.
            Without one, the app uses template-based generation.
          </p>

          <div className="flex flex-wrap gap-2 mb-4">
            {providers.map((p) => (
              <Badge
                key={p}
                variant={provider === p ? "default" : "outline"}
                className="cursor-pointer"
                onClick={() => {
                  setProvider(p)
                  if (p === "ollama") setBaseUrl("http://localhost:11434")
                }}
              >
                {p}
              </Badge>
            ))}
            <Badge
              variant={provider === "" ? "default" : "outline"}
              className="cursor-pointer"
              onClick={() => setProvider("")}
            >
              None (offline)
            </Badge>
          </div>

          {provider && provider !== "ollama" && (
            <Input
              placeholder="API Key"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="mb-3"
            />
          )}

          {provider && (
            <div className="grid grid-cols-2 gap-3 mb-3">
              <Input
                placeholder="Model (e.g., claude-sonnet-4-20250514)"
                value={model}
                onChange={(e) => setModel(e.target.value)}
              />
              {(provider === "ollama" || provider === "huggingface") && (
                <Input
                  placeholder="Base URL"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                />
              )}
            </div>
          )}

          <Button onClick={handleSaveLLM} disabled={!provider && !llmConfig.provider}>
            {provider ? "Save LLM Settings" : "Clear LLM Settings"}
          </Button>

          {message && (
            <p className="text-sm mt-2 text-muted-foreground">{message}</p>
          )}
        </CardContent>
      </Card>

      {/* Calibration Weights */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg">Match Calibration</CardTitle>
          <Button variant="outline" size="sm" onClick={handleRecalibrate}>
            Recalculate
          </Button>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            These weights determine how job matches are scored. They adjust based on your ratings.
          </p>
          <div className="space-y-2">
            {Object.entries(weights).map(([feature, weight]) => (
              <div key={feature} className="flex items-center justify-between">
                <span className="text-sm">{feature.replace(/_/g, " ")}</span>
                <div className="flex items-center gap-2">
                  <div className="w-32 bg-muted rounded-full h-2">
                    <div
                      className="bg-primary rounded-full h-2"
                      style={{ width: `${(weight as number) * 100}%` }}
                    />
                  </div>
                  <span className="text-sm text-muted-foreground w-12 text-right">
                    {Math.round((weight as number) * 100)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Offline Mode */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Offline Mode</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            Download AI models to run matching and extraction locally without any API keys.
            Requires ~500MB disk and ~2GB RAM.
          </p>
          <div className="flex items-center gap-4">
            <Button variant="outline" disabled>
              Download Models (coming soon)
            </Button>
            <span className="text-xs text-muted-foreground">
              Sentence Transformers (~80MB) + spaCy (~50MB)
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Export Calibration */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Data Export</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground mb-4">
            Export your anonymized calibration data. No personal information is included —
            only match feature weights and ratings.
          </p>
          <Button variant="outline" disabled>
            Export Calibration Data (coming soon)
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
