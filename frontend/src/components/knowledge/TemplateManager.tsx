import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { api } from "@/api/client"
import { toast } from "sonner"
import type { ResumeTemplate } from "@/types"

interface Props {
  templates: ResumeTemplate[]
  storedResume: Record<string, unknown> | null
  onUpload: (file: File) => void
  onSetDefault: (id: number) => void
  onDelete: (id: number) => void
  isUploading: boolean
}

export default function TemplateManager({
  templates, storedResume, onUpload, onSetDefault, onDelete, isUploading,
}: Props) {
  const [showResume, setShowResume] = useState(false)

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">Resume Templates ({templates.length}/5)</CardTitle>
        <div className="flex gap-2">
          <input
            id="template-upload"
            type="file"
            accept=".docx,.pdf,.txt"
            aria-label="Upload resume template"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) onUpload(file)
              e.target.value = ""
            }}
          />
          <Button variant="outline" size="sm" disabled={isUploading || templates.length >= 5}
            onClick={() => document.getElementById("template-upload")?.click()}>
            {isUploading ? "Uploading..." : "+ Add Template"}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {templates.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No resume templates yet. Upload your resume to use as a formatting template.
          </p>
        ) : (
          <div className="space-y-2">
            {templates.map((t) => (
              <div key={t.id} className={`flex items-center justify-between p-3 border rounded-lg ${t.is_default ? "border-blue-300 bg-blue-50/30" : ""}`}>
                <div>
                  <div className="text-sm font-medium">{t.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {t.filename} {t.is_default ? " — default" : ""}
                  </div>
                </div>
                <div className="flex gap-1">
                  <Button variant="ghost" size="sm" onClick={async () => {
                    try {
                      const response = await api.previewTemplate(t.id)
                      const blob = await response.blob()
                      const previewUrl = URL.createObjectURL(blob)
                      window.open(previewUrl, "_blank")
                    } catch {
                      toast.error("Preview not available")
                    }
                  }}>Preview</Button>
                  {!t.is_default && (
                    <Button variant="ghost" size="sm" onClick={() => onSetDefault(t.id)}>Set Default</Button>
                  )}
                  <Button variant="ghost" size="sm" onClick={() => onDelete(t.id)}>Delete</Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {storedResume?.has_resume ? (
          <Button variant="ghost" size="sm" className="mt-3" onClick={() => setShowResume(!showResume)}>
            {showResume ? "Hide resume text" : "View stored resume text"}
          </Button>
        ) : null}
        {showResume && storedResume?.has_resume ? (
          <pre className="bg-muted p-4 rounded-lg text-sm whitespace-pre-wrap font-mono max-h-48 overflow-auto mt-2">
            {String(storedResume.text || "No text stored")}
          </pre>
        ) : null}
      </CardContent>
    </Card>
  )
}
