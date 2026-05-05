/**
 * Agent-level AI provider + model picker.
 *
 * Shows configured providers from global settings.
 * No API key input — keys are managed in Global Settings only.
 * Each agent picks which provider + model to use.
 */

import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { ModelInfo } from "@/types"

interface Props {
  providers: string[]
  models: Record<string, ModelInfo[]>
  llmStatus: { active: boolean; provider: string | null; model: string | null }
  selectedProvider: string
  selectedModel: string
  onProviderChange: (providerName: string) => void
  onModelChange: (modelId: string) => void
  onSave: () => void
  message: string
  themeColor?: "blue" | "purple"
}

export default function AgentProviderPicker({
  providers, models, llmStatus, selectedProvider, selectedModel,
  onProviderChange, onModelChange, onSave, message,
  themeColor = "blue",
}: Props) {
  const navigate = useNavigate()
  const providerModels = models[selectedProvider] || []
  const themeClasses = themeColor === "purple"
    ? { activeBg: "bg-purple-50", activeDot: "bg-purple-500", badge: "bg-purple-600 hover:bg-purple-700 border-purple-600", modelBorder: "border-purple-400 bg-purple-50/50", button: "bg-purple-600 hover:bg-purple-700 text-white" }
    : { activeBg: "bg-blue-50", activeDot: "bg-blue-500", badge: "bg-blue-600 hover:bg-blue-700 border-blue-600", modelBorder: "border-blue-400 bg-blue-50/50", button: "" }

  return (
    <Card>
      <CardHeader><CardTitle className="text-lg">AI Provider</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        {/* Status */}
        <div className={`flex items-center gap-3 p-3 rounded-lg ${llmStatus.active ? themeClasses.activeBg : "bg-muted/50"}`}>
          <div className={`w-2 h-2 rounded-full ${llmStatus.active ? themeClasses.activeDot : "bg-muted-foreground/30"}`} />
          <div>
            <span className="text-sm font-medium">
              {llmStatus.active ? `${llmStatus.provider} — ${llmStatus.model}` : "No AI provider active"}
            </span>
            <p className="text-xs text-muted-foreground">
              {llmStatus.active ? "AI features enabled." : "Select a provider below or configure API keys in Settings."}
            </p>
          </div>
        </div>

        {/* Provider selection */}
        {providers.length > 0 ? (
          <div>
            <p className="text-sm font-medium mb-2">Provider</p>
            <div className="flex flex-wrap gap-2">
              {providers.map((providerName) => (
                <Badge key={providerName}
                  variant={selectedProvider === providerName ? "default" : "outline"}
                  className={`cursor-pointer ${selectedProvider === providerName ? themeClasses.badge : ""}`}
                  onClick={() => { onProviderChange(providerName); onModelChange("") }}>
                  {providerName}
                </Badge>
              ))}
              <Badge
                variant={selectedProvider === "" ? "default" : "outline"}
                className={`cursor-pointer ${selectedProvider === "" ? themeClasses.badge : ""}`}
                onClick={() => { onProviderChange(""); onModelChange("") }}>
                None (free)
              </Badge>
            </div>
          </div>
        ) : (
          <div className="text-center py-4">
            <p className="text-sm text-gray-400 mb-2">No AI providers configured yet</p>
            <Button variant="outline" size="sm" onClick={() => navigate("/settings")}>
              ⚙️ Add AI Provider in Settings
            </Button>
          </div>
        )}

        {/* Model selection */}
        {selectedProvider && providerModels.length > 0 && (
          <div>
            <p className="text-sm font-medium mb-2">Model</p>
            <div className="space-y-2">
              {providerModels.map((modelOption) => (
                <div key={modelOption.id}
                  className={`flex items-center justify-between p-2.5 rounded-lg border cursor-pointer transition-colors ${
                    selectedModel === modelOption.id ? themeClasses.modelBorder : "border-border/50 hover:border-border"
                  }`}
                  onClick={() => onModelChange(modelOption.id)}>
                  <div>
                    <span className="text-sm font-medium">{modelOption.name}</span>
                    <span className="text-xs text-muted-foreground ml-2">{modelOption.speed} · {modelOption.quality}</span>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-muted-foreground">
                      ${modelOption.input_per_1m} in · ${modelOption.output_per_1m} out per 1M tokens
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Save */}
        <Button onClick={onSave} disabled={!selectedProvider && !selectedModel}
          className={themeClasses.button}>
          {selectedProvider ? "Save Provider" : "Clear Provider"}
        </Button>

        {message && <p className="text-sm text-muted-foreground">{message}</p>}
      </CardContent>
    </Card>
  )
}
