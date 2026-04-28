import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import type { ModelInfo } from "@/types"

interface Props {
  providers: string[]
  models: Record<string, ModelInfo[]>
  llmStatus: { active: boolean; provider: string | null; model: string | null }
  provider: string
  model: string
  apiKey: string
  baseUrl: string
  message: string
  onProviderChange: (p: string) => void
  onModelChange: (m: string) => void
  onApiKeyChange: (k: string) => void
  onBaseUrlChange: (u: string) => void
  onSave: () => void
}

export default function ProviderCard({
  providers, models, llmStatus, provider, model, apiKey, baseUrl, message,
  onProviderChange, onModelChange, onApiKeyChange, onBaseUrlChange, onSave,
}: Props) {
  const providerModels = models[provider] || []

  return (
    <Card>
      <CardHeader><CardTitle className="text-lg">AI Provider</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        <div className={`flex items-center gap-3 p-3 rounded-lg ${llmStatus.active ? "bg-blue-50" : "bg-muted/50"}`}>
          <div className={`w-2 h-2 rounded-full ${llmStatus.active ? "bg-blue-500" : "bg-muted-foreground/30"}`} />
          <div>
            <span className="text-sm font-medium">
              {llmStatus.active ? `${llmStatus.provider} — ${llmStatus.model}` : "No AI provider active"}
            </span>
            <p className="text-xs text-muted-foreground">
              {llmStatus.active ? "AI features enabled." : "Using free template-based generation."}
            </p>
          </div>
        </div>

        <div>
          <p className="text-sm font-medium mb-2">Provider</p>
          <div className="flex flex-wrap gap-2">
            {providers.map((p) => (
              <Badge key={p} variant={provider === p ? "default" : "outline"} className="cursor-pointer"
                onClick={() => { onProviderChange(p); onModelChange(""); if (p === "ollama") onBaseUrlChange("http://localhost:11434") }}>
                {p}
              </Badge>
            ))}
            <Badge variant={provider === "" ? "default" : "outline"} className="cursor-pointer"
              onClick={() => { onProviderChange(""); onModelChange("") }}>
              None (free)
            </Badge>
          </div>
        </div>

        {provider && providerModels.length > 0 && (
          <div>
            <p className="text-sm font-medium mb-2">Model</p>
            <div className="space-y-2">
              {providerModels.map((m) => (
                <div key={m.id}
                  className={`flex items-center justify-between p-2.5 rounded-lg border cursor-pointer transition-colors ${
                    model === m.id ? "border-blue-400 bg-blue-50/50" : "border-border/50 hover:border-border"
                  }`}
                  onClick={() => onModelChange(m.id)}>
                  <div>
                    <span className="text-sm font-medium">{m.name}</span>
                    <span className="text-xs text-muted-foreground ml-2">{m.speed} · {m.quality}</span>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-muted-foreground">
                      ${m.input_per_1m} per 1M input · ${m.output_per_1m} per 1M output
                    </div>
                    <div className="text-xs font-medium">~{m.est_per_resume} per resume</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {provider && provider !== "ollama" && (
          <div>
            <p className="text-sm font-medium mb-2">API Key</p>
            <Input placeholder="Pre-loaded from .env — only enter to override"
              type="password" value={apiKey} onChange={(e) => onApiKeyChange(e.target.value)} />
          </div>
        )}

        {(provider === "ollama" || provider === "huggingface") && (
          <Input placeholder="Base URL" value={baseUrl} onChange={(e) => onBaseUrlChange(e.target.value)} />
        )}

        <Button onClick={onSave} disabled={!provider && !model}>
          {provider ? "Save Provider" : "Clear Provider"}
        </Button>

        {message && <p className="text-sm text-muted-foreground">{message}</p>}
      </CardContent>
    </Card>
  )
}
