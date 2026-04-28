/**
 * ResumeBuilderTab — 3-step flow:
 * 1. Select job (paste link or pick from list)
 * 2. Analyze fit (show suggestions with checkboxes)
 * 3. Generate resume (clean content, downloadable)
 */

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { api } from "@/api/client"
import ResumeUpload from "@/components/ResumeUpload"
import KnowledgeBank from "@/components/KnowledgeBank"
import ResumeAnalysis from "@/components/ResumeAnalysis"
import ResumeResult from "@/components/ResumeResult"

interface Job { id: number; title: string; company: string }

type Step = "select" | "analyzing" | "analysis" | "generating" | "result"

export default function ResumeBuilderTab() {
  const [jobs, setJobs] = useState<Job[]>([])
  const [selectedJob, setSelectedJob] = useState<Job | null>(null)
  const [step, setStep] = useState<Step>("select")
  const [analysis, setAnalysis] = useState<Record<string, unknown> | null>(null)
  const [resume, setResume] = useState<{ id: number; content: string; analysis?: Record<string, unknown> } | null>(null)
  const [coverLetter, setCoverLetter] = useState<{ id: number; content: string } | null>(null)
  const [subTab, setSubTab] = useState("superpowers")
  const [refreshKey, setRefreshKey] = useState(0)
  const [jobInput, setJobInput] = useState("")
  const [parsing, setParsing] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => { loadJobs() }, [])

  const loadJobs = () => {
    api.listJobs().then((data) => {
      // #region debug log
      const dbg = (window as unknown as { __dbg?: (l: string, m: string, d: Record<string, unknown>, h?: string) => void }).__dbg
      dbg?.("ResumeBuilderTab.loadJobs", "listJobs response shape", {
        type: Array.isArray(data) ? "array" : typeof data,
        len: Array.isArray(data) ? data.length : -1,
        keys: !Array.isArray(data) && typeof data === "object" && data ? Object.keys(data).slice(0, 5) : null,
        sample: Array.isArray(data) ? JSON.stringify(data[0] ?? null).slice(0, 200) : JSON.stringify(data).slice(0, 200),
      }, "HC")
      // #endregion
      setJobs(data as unknown as Job[])
    }).catch((err) => {
      // #region debug log
      const dbg = (window as unknown as { __dbg?: (l: string, m: string, d: Record<string, unknown>, h?: string) => void }).__dbg
      dbg?.("ResumeBuilderTab.loadJobs", "listJobs rejected", {
        name: (err as Error)?.name, message: (err as Error)?.message,
      }, "HC")
      // #endregion
    })
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

  const handleAnalyze = async () => {
    if (!selectedJob) return
    setStep("analyzing")
    setError("")
    try {
      const result = await api.analyzeResumeFit(selectedJob.id)
      if (result.error) {
        setError(String(result.error))
        setStep("select")
        return
      }
      setAnalysis(result)
      setStep("analysis")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed")
      setStep("select")
    }
  }

  const handleApplyAndGenerate = async (selectedSuggestions: Array<{ type: string; description: string; impact: string; source: string }>, userInstructions?: string) => {
    if (!selectedJob) return
    setStep("generating")
    try {
      const prefs: Record<string, unknown> = { apply_suggestions: selectedSuggestions }
      if (userInstructions) prefs.user_instructions = userInstructions
      const r = await api.generateResume(selectedJob.id, prefs) as { id: number; content: string; analysis?: Record<string, unknown> }
      setResume(r)
      const cl = await api.generateCoverLetter(selectedJob.id, prefs)
      setCoverLetter(cl)
      setStep("result")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed")
      setStep("analysis")
    }
  }

  const handleSkipAnalysis = async () => {
    if (!selectedJob) return
    setStep("generating")
    try {
      const r = await api.generateResume(selectedJob.id, {}) as { id: number; content: string; analysis?: Record<string, unknown> }
      setResume(r)
      const cl = await api.generateCoverLetter(selectedJob.id, {})
      setCoverLetter(cl)
      setStep("result")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed")
      setStep("select")
    }
  }

  const handleReset = () => {
    setStep("select")
    setAnalysis(null)
    setResume(null)
    setCoverLetter(null)
    setError("")
  }

  return (
    <div>
      <h2 className="text-xl font-semibold mb-1">Superpower Lab</h2>
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
          {/* Step 1: Select job */}
          {step === "select" && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader><CardTitle className="text-lg">Build Resume</CardTitle></CardHeader>
                <CardContent>
                  <Textarea
                    placeholder={"Paste a job link or description..."}
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
                    {jobs.map((j) => (
                      <Badge key={j.id} variant={selectedJob?.id === j.id ? "default" : "outline"}
                        className="cursor-pointer" onClick={() => setSelectedJob(j)}>
                        {j.title}{j.company ? ` — ${j.company}` : ""}
                      </Badge>
                    ))}
                  </div>

                  {selectedJob && (
                    <div className="p-3 rounded-lg bg-blue-50/30 border border-blue-100 mb-4">
                      <p className="text-sm">
                        Selected: <strong>{selectedJob.title}</strong>
                        {selectedJob.company && <> at <strong>{selectedJob.company}</strong></>}
                      </p>
                    </div>
                  )}

                  {error && <p className="text-sm text-destructive mb-4">{error}</p>}

                  <div className="flex gap-3">
                    <Button onClick={handleAnalyze} disabled={!selectedJob}>
                      Analyze Fit & Suggest Improvements
                    </Button>
                    <Button variant="outline" onClick={handleSkipAnalysis} disabled={!selectedJob}>
                      Generate without analysis
                    </Button>
                  </div>
                </CardContent>
              </Card>

              <Card className="border-dashed">
                <CardContent className="py-8 text-center">
                  <p className="text-muted-foreground text-sm">
                    Select a job to see fit analysis with actionable suggestions.
                    <br />
                    The AI compares your current resume AND full knowledge bank against the job.
                  </p>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Step 1.5: Analyzing */}
          {step === "analyzing" && (
            <Card>
              <CardContent className="py-12 text-center">
                <p className="text-muted-foreground">
                  Analyzing your resume fit for {selectedJob?.title} at {selectedJob?.company}...
                </p>
                <p className="text-xs text-muted-foreground mt-2">This takes 5-10 seconds</p>
              </CardContent>
            </Card>
          )}

          {/* Step 2: Analysis with suggestions */}
          {step === "analysis" && analysis && selectedJob && (
            <ResumeAnalysis
              analysis={analysis as unknown as Parameters<typeof ResumeAnalysis>[0]["analysis"]}
              jobTitle={selectedJob.title}
              company={selectedJob.company || ""}
              onApplyAndGenerate={handleApplyAndGenerate}
              onSkip={handleSkipAnalysis}
              loading={false}
            />
          )}

          {/* Step 2.5: Generating */}
          {step === "generating" && (
            <Card>
              <CardContent className="py-12 text-center">
                <p className="text-muted-foreground">
                  Generating tailored resume and cover letter...
                </p>
                <p className="text-xs text-muted-foreground mt-2">This takes 10-15 seconds</p>
              </CardContent>
            </Card>
          )}

          {/* Step 3: Result */}
          {step === "result" && resume && (
            <ResumeResult
              resume={resume}
              coverLetter={coverLetter}
              company={selectedJob?.company || ""}
              onBack={handleReset}
            />
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
