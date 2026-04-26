import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { api } from "@/api/client"
import ResumeUpload from "@/components/ResumeUpload"
import KnowledgeBank from "@/components/KnowledgeBank"
import GenerationPrefs from "@/components/GenerationPrefs"

interface Job { id: number; title: string; company: string }

export default function ResumeBuilderTab() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [selectedJob, setSelectedJob] = useState<Job | null>(null)
  const [resume, setResume] = useState<{ id: number; content: string } | null>(null)
  const [coverLetter, setCoverLetter] = useState<{ id: number; content: string } | null>(null)
  const [loading, setLoading] = useState(false)
  const [showKB, setShowKB] = useState(false)
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    api.listJobs().then((data) => setJobs(data as unknown as Job[]))
  }, [])

  const handleGenerate = async (prefs: Record<string, unknown>) => {
    if (!selectedJob) return
    setLoading(true)
    try {
      const [r, cl] = await Promise.all([
        api.generateResume(selectedJob.id, prefs),
        api.generateCoverLetter(selectedJob.id, prefs),
      ])
      setResume(r)
      setCoverLetter(cl)
    } finally { setLoading(false) }
  }

  const handleExport = async (type: "resume" | "coverLetter", format: string) => {
    const id = type === "resume" ? resume!.id : coverLetter!.id
    const response = type === "resume"
      ? await api.exportResume(id, format)
      : await api.exportCoverLetter(id, format)
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${type}_${selectedJob?.company || "doc"}.${format}`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Left: Resume Builder */}
      <div className="space-y-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Resume Builder</CardTitle>
          </CardHeader>
          <CardContent>
            {/* Job selector */}
            <p className="text-sm font-medium mb-2">Select a job to tailor for:</p>
            <div className="flex flex-wrap gap-2 mb-4 max-h-32 overflow-auto">
              <Badge variant={!selectedJob ? "default" : "outline"} className="cursor-pointer"
                onClick={() => setSelectedJob(null)}>General</Badge>
              {jobs.map((j) => (
                <Badge key={j.id} variant={selectedJob?.id === j.id ? "default" : "outline"}
                  className="cursor-pointer" onClick={() => setSelectedJob(j)}>
                  {j.title} — {j.company}
                </Badge>
              ))}
            </div>

            {selectedJob && (
              <p className="text-sm text-muted-foreground mb-4">
                Tailoring for: <strong>{selectedJob.title}</strong> at <strong>{selectedJob.company}</strong>
              </p>
            )}

            <GenerationPrefs onGenerate={handleGenerate} loading={loading} />
          </CardContent>
        </Card>

        {/* Preview */}
        {resume && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Resume Preview</CardTitle>
              <div className="flex gap-1">
                {["pdf", "docx", "md"].map((fmt) => (
                  <Button key={fmt} variant="ghost" size="sm" onClick={() => handleExport("resume", fmt)}>
                    {fmt.toUpperCase()}
                  </Button>
                ))}
              </div>
            </CardHeader>
            <CardContent>
              <pre className="bg-muted p-4 rounded-lg text-sm whitespace-pre-wrap font-mono max-h-96 overflow-auto">
                {resume.content}
              </pre>
            </CardContent>
          </Card>
        )}

        {coverLetter && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-base">Cover Letter Preview</CardTitle>
              <div className="flex gap-1">
                {["pdf", "docx", "md"].map((fmt) => (
                  <Button key={fmt} variant="ghost" size="sm" onClick={() => handleExport("coverLetter", fmt)}>
                    {fmt.toUpperCase()}
                  </Button>
                ))}
              </div>
            </CardHeader>
            <CardContent>
              <pre className="bg-muted p-4 rounded-lg text-sm whitespace-pre-wrap font-mono max-h-64 overflow-auto">
                {coverLetter.content}
              </pre>
            </CardContent>
          </Card>
        )}

        {!resume && !loading && (
          <p className="text-sm text-muted-foreground text-center py-8">
            Select a job and click "Generate" to build your resume
          </p>
        )}
      </div>

      {/* Right: My Superpowers */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">My Superpowers</h2>
          <Button variant="ghost" size="sm" onClick={() => setShowKB(!showKB)}>
            {showKB ? "Collapse" : "Expand"}
          </Button>
        </div>

        <ResumeUpload onImported={() => setRefreshKey((k) => k + 1)} onViewKnowledge={() => setShowKB(true)} />

        {showKB && <KnowledgeBank key={refreshKey} />}

        {!showKB && (
          <Card className="border-dashed cursor-pointer" onClick={() => setShowKB(true)}>
            <CardContent className="py-6 text-center">
              <p className="text-muted-foreground text-sm">Click to view and manage your experiences, skills, education, and projects</p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
