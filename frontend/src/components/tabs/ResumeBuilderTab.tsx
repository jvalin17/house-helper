import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
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
  const [subTab, setSubTab] = useState("superpowers")
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
    <div>
      <h2 className="text-xl font-bold mb-1">Superpower Lab</h2>
      <p className="text-muted-foreground text-sm mb-4">Build your knowledge bank, then generate tailored resumes</p>

      <Tabs value={subTab} onValueChange={setSubTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="superpowers">My Superpowers</TabsTrigger>
          <TabsTrigger value="builder">Resume Builder</TabsTrigger>
        </TabsList>

        <TabsContent value="superpowers">
          <ResumeUpload onImported={() => setRefreshKey((k) => k + 1)} onViewKnowledge={() => {}} />
          <KnowledgeBank key={refreshKey} />
        </TabsContent>

        <TabsContent value="builder">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Left: Builder */}
            <div className="space-y-4">
              <Card>
                <CardHeader><CardTitle className="text-lg">Build Resume</CardTitle></CardHeader>
                <CardContent>
                  <p className="text-sm font-medium mb-2">Tailor for a job:</p>
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
            </div>

            {/* Right: Preview */}
            <div className="space-y-4">
              {resume ? (
                <>
                  <Card>
                    <CardHeader className="flex flex-row items-center justify-between">
                      <CardTitle className="text-base">Resume</CardTitle>
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

                  {coverLetter && (
                    <Card>
                      <CardHeader className="flex flex-row items-center justify-between">
                        <CardTitle className="text-base">Cover Letter</CardTitle>
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

                  <p className="text-xs text-muted-foreground text-center">
                    To convert .md to other formats: open in any text editor, or use pandoc/Google Docs
                  </p>
                </>
              ) : (
                <Card className="border-dashed">
                  <CardContent className="py-16 text-center">
                    <div className="text-3xl mb-2">&#128196;</div>
                    <p className="text-muted-foreground">Select a job and click Generate to preview your resume</p>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
