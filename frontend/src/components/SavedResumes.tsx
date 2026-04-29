import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { api } from "@/api/client"
import type { SavedResume } from "@/types"

export default function SavedResumes() {
  const [resumes, setResumes] = useState<SavedResume[]>([])
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState<number | null>(null)

  useEffect(() => { loadResumes() }, [])

  const loadResumes = async () => {
    try {
      const data = await api.listSavedResumes()
      setResumes(Array.isArray(data) ? data : [])
    } catch { /* silent */ }
    finally { setLoading(false) }
  }

  const handleExport = async (resumeId: number, format: string) => {
    setExporting(resumeId)
    try {
      const response = await api.exportResume(resumeId, format)
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `resume_${resumeId}.${format}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Export failed")
    } finally { setExporting(null) }
  }

  const handleDelete = async (resumeId: number) => {
    try {
      await api.deleteResume(resumeId)
      loadResumes()
      toast.success("Resume deleted")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to delete")
    }
  }

  if (loading) return <p className="text-muted-foreground">Loading saved resumes...</p>

  if (resumes.length === 0) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-8 text-center">
          <p className="text-muted-foreground text-sm">
            No saved resumes yet. Generate a tailored resume from the Job Search tab.
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">Saved Resumes ({resumes.length})</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {resumes.map((r) => (
            <div key={r.id} className="flex items-center justify-between p-3 border rounded-lg">
              <div className="flex-1">
                <div className="text-sm font-medium">{r.job_title || "Untitled"}</div>
                <div className="text-xs text-muted-foreground">
                  {r.job_company || "Unknown"} {" · "}
                  {new Date(r.created_at).toLocaleDateString()}
                </div>
              </div>
              <div className="flex items-center gap-1">
                {r.has_docx && (
                  <Badge variant="outline" className="text-xs">DOCX</Badge>
                )}
                <Button variant="ghost" size="sm" disabled={exporting === r.id}
                  onClick={() => handleExport(r.id, "pdf")}>
                  PDF
                </Button>
                {r.has_docx && (
                  <Button variant="ghost" size="sm" disabled={exporting === r.id}
                    onClick={() => handleExport(r.id, "docx")}>
                    DOCX
                  </Button>
                )}
                <Button variant="ghost" size="sm" disabled={exporting === r.id}
                  onClick={() => handleExport(r.id, "md")}>
                  MD
                </Button>
                <Button variant="ghost" size="sm" className="text-destructive"
                  onClick={() => handleDelete(r.id)}>
                  Delete
                </Button>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
