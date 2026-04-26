import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
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
  const [jobInput, setJobInput] = useState("")
  const [parsing, setParsing] = useState(false)

  useEffect(() => {
    loadJobs()
  }, [])

  const loadJobs = () => {
    api.listJobs().then((data) => setJobs(data as unknown as Job[]))
  }

  const handleParseJob = async () => {
    if (!jobInput.trim()) return
    setParsing(true)
    try {
      const lines = jobInput.split("\n").map((l: string) => l.trim()).filter(Boolean)
      const result = await api.parseJobs(lines)
      if (result.jobs.length > 0) {
        const newJob = result.jobs[0] as unknown as Job
        loadJobs()
        setSelectedJob(newJob)
        setJobInput("")
      }
    } catch { /* silent */ }
    finally { setParsing(false) }
  }

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
              {/* Paste job link or description */}
              <Card>
                <CardHeader><CardTitle className="text-lg">What job is this for?</CardTitle></CardHeader>
                <CardContent>
                  <Textarea
                    placeholder={"Paste a job link or description...\n\nhttps://careers.example.com/job/123\n\nOr paste the full job description text"}
                    value={jobInput}
                    onChange={(e) => setJobInput(e.target.value)}
                    rows={3}
                    className="mb-3 font-mono text-sm"
                  />
                  <div className="flex items-center gap-3 mb-4">
                    <Button onClick={handleParseJob} disabled={parsing || !jobInput.trim()} size="sm">
                      {parsing ? "Parsing..." : "Parse & Select"}
                    </Button>
                    <span className="text-xs text-muted-foreground">Or pick from existing jobs below</span>
                  </div>

                  <div className="flex flex-wrap gap-2 mb-4 max-h-24 overflow-auto">
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
                    <p className="text-sm text-green-600 mb-4">
                      Building resume for: <strong>{selectedJob.title}</strong> at <strong>{selectedJob.company}</strong>
                    </p>
                  )}
                </CardContent>
              </Card>

              {/* Preferences + Generate */}
              <Card>
                <CardHeader><CardTitle className="text-lg">Resume Preferences</CardTitle></CardHeader>
                <CardContent>
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
