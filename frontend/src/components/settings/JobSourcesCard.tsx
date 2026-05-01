import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { api } from "@/api/client"
import type { JobSource } from "@/types"

const MAX_CUSTOM_SOURCES = 5

interface Props {
  jobSources: JobSource[]
  onSourcesChanged: () => void
  onToggle: (sourceId: string, enabled: boolean) => void
}

export default function JobSourcesCard({ jobSources, onSourcesChanged, onToggle }: Props) {
  const [showAddForm, setShowAddForm] = useState(false)
  const [newSourceName, setNewSourceName] = useState("")
  const [newSourceUrl, setNewSourceUrl] = useState("")
  const [newSourceApiKey, setNewSourceApiKey] = useState("")
  const [isSaving, setIsSaving] = useState(false)

  const customSourceCount = jobSources.filter(source => source.is_custom).length
  const connectedCount = jobSources.filter(source => source.is_available || !source.requires_api_key).length

  const handleAddSource = async () => {
    if (!newSourceName.trim() || !newSourceUrl.trim()) {
      toast.error("Name and API URL are required")
      return
    }
    setIsSaving(true)
    try {
      await api.addCustomSource({
        name: newSourceName.trim(),
        api_url: newSourceUrl.trim(),
        api_key: newSourceApiKey.trim() || undefined,
      })
      toast.success(`Added ${newSourceName}`)
      setNewSourceName("")
      setNewSourceUrl("")
      setNewSourceApiKey("")
      setShowAddForm(false)
      onSourcesChanged()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to add source")
    } finally {
      setIsSaving(false)
    }
  }

  const handleDeleteSource = async (sourceId: string, sourceName: string) => {
    try {
      await api.deleteCustomSource(sourceId)
      toast.success(`Removed ${sourceName}`)
      onSourcesChanged()
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to remove source")
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">Job Sources</CardTitle>
        <Badge className="bg-purple-50 text-purple-700 border-purple-200">
          {connectedCount}/{jobSources.length} connected
        </Badge>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-4">
          Toggle sources on/off. Add your own job board API endpoints (max {MAX_CUSTOM_SOURCES} custom).
        </p>

        <div className="space-y-2">
          {jobSources.map((source) => (
            <div key={source.id} className={`flex items-center justify-between p-3 border rounded-lg transition-opacity ${!source.enabled ? "opacity-50" : ""}`}>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => onToggle(source.id, !source.enabled)}
                  className={`w-10 h-5 rounded-full transition-colors relative ${source.enabled ? "bg-purple-500" : "bg-gray-300"}`}
                  aria-label={`Toggle ${source.name}`}
                >
                  <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${source.enabled ? "left-5" : "left-0.5"}`} />
                </button>
                <div>
                  <div className="text-sm font-medium">
                    {source.name}
                    {source.is_custom && (
                      <span className="ml-2 text-[10px] px-1.5 py-0.5 rounded bg-purple-50 text-purple-600 font-normal">Custom</span>
                    )}
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {source.is_custom ? source.api_url : `Free tier: ${source.free_tier}`}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {source.is_custom ? (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-destructive"
                    aria-label={`Delete ${source.name}`}
                    onClick={() => handleDeleteSource(source.id, source.name)}
                  >
                    Delete
                  </Button>
                ) : source.is_available ? (
                  <Badge className="bg-green-50 text-green-700 border-green-200">Connected</Badge>
                ) : !source.requires_api_key ? (
                  <Badge className="bg-blue-50 text-blue-700 border-blue-200">Free</Badge>
                ) : (
                  <a href={source.signup || "#"} target="_blank" rel="noreferrer">
                    <Button variant="outline" size="sm">+ Connect</Button>
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Add Source Form */}
        {showAddForm ? (
          <div className="mt-4 p-3 border border-dashed rounded-lg space-y-2">
            <Input
              placeholder="Source name (e.g., Greenhouse)"
              value={newSourceName}
              onChange={(event) => setNewSourceName(event.target.value)}
            />
            <Input
              placeholder="API URL (e.g., https://api.greenhouse.io/v1/jobs)"
              value={newSourceUrl}
              onChange={(event) => setNewSourceUrl(event.target.value)}
            />
            <Input
              type="password"
              placeholder="API key (optional)"
              value={newSourceApiKey}
              onChange={(event) => setNewSourceApiKey(event.target.value)}
            />
            <div className="flex gap-2">
              <Button size="sm" onClick={handleAddSource} disabled={isSaving}>
                {isSaving ? "Saving..." : "Save Source"}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setShowAddForm(false)}>Cancel</Button>
            </div>
          </div>
        ) : (
          <div className="mt-4">
            <Button
              variant="outline"
              size="sm"
              disabled={customSourceCount >= MAX_CUSTOM_SOURCES}
              onClick={() => setShowAddForm(true)}
            >
              + Add Source {customSourceCount > 0 && `(${customSourceCount}/${MAX_CUSTOM_SOURCES})`}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
