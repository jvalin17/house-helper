import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { api } from "@/api/client"

interface Props {
  onImported: () => void
  onViewKnowledge: () => void
}

export default function ResumeUpload({ onImported, onViewKnowledge }: Props) {
  const [isDragging, setIsDragging] = useState(false)
  const [importing, setImporting] = useState(false)
  const [result, setResult] = useState<Record<string, number> | null>(null)
  const [error, setError] = useState("")

  const handleFile = async (file: File) => {
    setImporting(true)
    setError("")
    setResult(null)
    try {
      const data = await api.importResume(file) as Record<string, number>
      setResult(data)
      onImported()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed")
    } finally {
      setImporting(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
  }

  return (
    <Card className="mb-6 border-primary/20">
      <CardHeader>
        <CardTitle className="text-lg">Import Your Resume</CardTitle>
      </CardHeader>
      <CardContent>
        <div
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-6 text-center transition-colors ${
            isDragging ? "border-primary bg-primary/5" : "border-muted-foreground/25 hover:border-primary/50"
          }`}
        >
          <input
            id="resume-upload"
            type="file"
            accept=".docx,.pdf,.txt"
            className="hidden"
            onChange={handleFileSelect}
          />

          {importing ? (
            <p className="text-muted-foreground py-2">Extracting data from your resume...</p>
          ) : result ? (
            <div className="py-2">
              <div className="text-2xl mb-2">&#9989;</div>
              <p className="font-medium mb-2">Resume imported successfully</p>
              <div className="flex flex-wrap gap-2 justify-center mb-3">
                {result.experiences > 0 && <Badge variant="secondary">{result.experiences} experiences</Badge>}
                {result.skills > 0 && <Badge variant="secondary">{result.skills} skills</Badge>}
                {result.education > 0 && <Badge variant="secondary">{result.education} education</Badge>}
                {result.projects > 0 && <Badge variant="secondary">{result.projects} projects</Badge>}
                {result.duplicates_skipped > 0 && <Badge variant="outline">{result.duplicates_skipped} duplicates skipped</Badge>}
              </div>
              <div className="flex gap-2 justify-center">
                <Button variant="outline" size="sm" onClick={onViewKnowledge}>
                  View My Superpowers
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => { setResult(null); setError("") }}
                >
                  Import Another
                </Button>
              </div>
            </div>
          ) : (
            <div
              className="cursor-pointer py-2"
              onClick={() => document.getElementById("resume-upload")?.click()}
            >
              <div className="text-3xl mb-2">&#128196;</div>
              <p className="font-medium mb-1">Drop your resume here or click to browse</p>
              <p className="text-sm text-muted-foreground">DOCX, PDF, or TXT</p>
            </div>
          )}
        </div>

        {error && (
          <p className="text-sm mt-3 text-destructive">{error}</p>
        )}
      </CardContent>
    </Card>
  )
}
