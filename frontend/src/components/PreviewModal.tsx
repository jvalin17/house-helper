import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { api } from "@/api/client"
import ResumeAnalysis from "@/components/ResumeAnalysis"

interface Props {
  jobId: number
  jobTitle: string
  company: string
  onClose: () => void
}

interface Suggestion {
  type: string
  description: string
  impact: string
  source: string
}

type Step = "checking" | "empty-kb" | "analyzing" | "analysis" | "generating" | "result" | "applied"

export default function PreviewModal({ jobId, jobTitle, company, onClose }: Props) {
  const [step, setStep] = useState<Step>("checking")
  const [algoScore, setAlgoScore] = useState<number | null>(null)
  const [algoBreakdown, setAlgoBreakdown] = useState<Record<string, number> | null>(null)
  const [analysis, setAnalysis] = useState<Record<string, unknown> | null>(null)
  const [resume, setResume] = useState<{ id: number; content: string; analysis?: Record<string, unknown> } | null>(null)
  const [coverLetter, setCoverLetter] = useState<{ id: number; content: string } | null>(null)
  const [error, setError] = useState("")
  const [exporting, setExporting] = useState(false)
  const [applyError, setApplyError] = useState("")

  useEffect(() => {
    checkAndAnalyze()
  }, [])

  const checkAndAnalyze = async () => {
    // Fetch job's algorithmic score in parallel with KB check
    try {
      const [kb, job] = await Promise.all([
        api.listEntries() as Promise<Record<string, unknown>>,
        api.getJob(jobId) as Promise<Record<string, unknown>>,
      ])
      if (typeof job?.match_score === "number") {
        setAlgoScore(job.match_score as number)
      }
      if (job?.match_breakdown) {
        try {
          const bd = typeof job.match_breakdown === "string"
            ? JSON.parse(job.match_breakdown as string)
            : job.match_breakdown
          if (bd && typeof bd === "object") setAlgoBreakdown(bd as Record<string, number>)
        } catch { /* ignore */ }
      }
      const experiences = Array.isArray(kb?.experiences) ? kb.experiences : []
      if (experiences.length === 0) {
        setStep("empty-kb")
        return
      }
    } catch {
      setStep("empty-kb")
      return
    }

    // KB has data — run analysis automatically
    setStep("analyzing")
    try {
      const result = await api.analyzeResumeFit(jobId)
      if (result.error) {
        setError(String(result.error))
        setStep("checking")
        return
      }
      setAnalysis(result)
      setStep("analysis")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed")
      setStep("checking")
    }
  }

  const handleGenerate = async (selectedSuggestions: Suggestion[]) => {
    setStep("generating")
    setError("")
    try {
      const prefs = {
        apply_suggestions: selectedSuggestions,
        analysis_baseline: {
          current_resume_match: analysis?.current_resume_match,
          knowledge_bank_match: analysis?.knowledge_bank_match,
        },
      }
      const r = await api.generateResume(jobId, prefs) as { id: number; content: string; analysis?: Record<string, unknown> }
      setResume(r)
      const cl = await api.generateCoverLetter(jobId, prefs)
      setCoverLetter(cl)
      setStep("result")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed")
      setStep("analysis")
    }
  }

  const handleSkipAnalysis = async () => {
    setStep("generating")
    setError("")
    try {
      const r = await api.generateResume(jobId, {}) as { id: number; content: string; analysis?: Record<string, unknown> }
      setResume(r)
      const cl = await api.generateCoverLetter(jobId, {})
      setCoverLetter(cl)
      setStep("result")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Generation failed")
      setStep("analysis")
    }
  }

  const handleApply = async () => {
    if (!resume || !coverLetter) return
    setApplyError("")
    try {
      await api.createApplication(jobId, resume.id, coverLetter.id)
      setStep("applied")
    } catch (err) {
      setApplyError(err instanceof Error ? err.message : "Failed to track application")
    }
  }

  const handleExport = async (type: "resume" | "coverLetter", format: string) => {
    setExporting(true)
    try {
      const id = type === "resume" ? resume!.id : coverLetter!.id
      const response = type === "resume"
        ? await api.exportResume(id, format)
        : await api.exportCoverLetter(id, format)
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `${type === "resume" ? "resume" : "cover_letter"}_${company}.${format}`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setExporting(false)
    }
  }

  const stepLabel: Record<Step, string> = {
    "checking": "Checking knowledge bank...",
    "empty-kb": "",
    "analyzing": "Analyzing your fit...",
    "analysis": "Review suggested improvements",
    "generating": "Generating resume and cover letter...",
    "result": "Review and download",
    "applied": "",
  }

  // Applied confirmation
  if (step === "applied") {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <Card className="max-w-md w-full text-center">
          <CardContent className="py-12">
            <h2 className="text-2xl font-bold mb-2">Application tracked</h2>
            <p className="text-muted-foreground mb-6">
              <strong>{jobTitle}</strong> at <strong>{company}</strong> has been added to your dashboard.
            </p>
            <Button onClick={onClose}>Back to Jobs</Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        <CardHeader className="flex flex-row items-center justify-between shrink-0">
          <div>
            <CardTitle>{jobTitle} at {company}</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">{stepLabel[step]}</p>
          </div>
          <Button variant="ghost" onClick={onClose}>Close</Button>
        </CardHeader>

        {/* Empty KB */}
        {step === "empty-kb" && (
          <CardContent className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <h3 className="font-semibold mb-2">Knowledge Bank is Empty</h3>
              <p className="text-muted-foreground mb-4">
                Import your resume first so the agent can generate tailored documents.
              </p>
              <p className="text-sm text-muted-foreground">
                Go to <strong>Superpower Lab</strong> and use "Import Your Resume" at the top.
              </p>
            </div>
          </CardContent>
        )}

        {/* Checking / Analyzing */}
        {(step === "checking" || step === "analyzing") && (
          <CardContent className="flex-1 flex items-center justify-center">
            {error ? (
              <div className="text-center">
                <p className="text-destructive mb-2">{error}</p>
                <Button variant="outline" onClick={checkAndAnalyze}>Try Again</Button>
              </div>
            ) : (
              <p className="text-muted-foreground">
                {step === "checking" ? "Checking knowledge bank..." : "Analyzing your resume fit... this takes 5-10 seconds"}
              </p>
            )}
          </CardContent>
        )}

        {/* Analysis — select improvements */}
        {step === "analysis" && analysis && (
          <CardContent className="flex-1 overflow-auto">
            {error && (
              <div className="mb-4 p-3 rounded-lg bg-destructive/10 border border-destructive/20">
                <p className="text-sm text-destructive">{error}</p>
              </div>
            )}
            <ResumeAnalysis
              analysis={analysis as unknown as Parameters<typeof ResumeAnalysis>[0]["analysis"]}
              jobTitle={jobTitle}
              company={company}
              onApplyAndGenerate={handleGenerate}
              onSkip={handleSkipAnalysis}
              loading={false}
            />
          </CardContent>
        )}

        {/* Generating */}
        {step === "generating" && (
          <CardContent className="flex-1 flex items-center justify-center">
            <p className="text-muted-foreground">Generating resume and cover letter... this takes 10-15 seconds</p>
          </CardContent>
        )}

        {/* Result — resume + cover letter + download + apply */}
        {step === "result" && resume && (
          <>
            <CardContent className="flex-1 overflow-auto">
              {/* Match progression */}
              {(() => {
                const a = resume.analysis || {}
                const aiCurrent = (analysis?.current_resume_match ?? a.original_match) as number | undefined
                const kbMatch = analysis?.knowledge_bank_match as number | undefined
                const aiAfter = a.new_match as number | undefined
                const hasAnyScore = algoScore != null || aiCurrent != null || aiAfter != null

                if (!hasAnyScore) return null

                return (
                  <div className="mb-4 p-4 rounded-lg bg-blue-50/50 border border-blue-100">
                    <div className="flex items-center gap-4 text-sm">
                      {algoScore != null && (
                        <div className="text-center">
                          <div className="text-xl font-bold text-muted-foreground">{Math.round(algoScore * 100)}%</div>
                          <div className="text-xs text-muted-foreground">Algorithmic</div>
                        </div>
                      )}
                      {algoScore != null && aiCurrent != null && (
                        <div className="text-muted-foreground">{"\u2192"}</div>
                      )}
                      {aiCurrent != null && (
                        <div className="text-center">
                          <div className="text-xl font-bold">{aiCurrent}%</div>
                          <div className="text-xs text-muted-foreground">LLM analysis (current resume)</div>
                        </div>
                      )}
                      {aiCurrent != null && kbMatch != null && (
                        <div className="text-muted-foreground">{"\u2192"}</div>
                      )}
                      {kbMatch != null && (
                        <div className="text-center">
                          <div className="text-xl font-bold">{kbMatch}%</div>
                          <div className="text-xs text-muted-foreground">Knowledge bank potential</div>
                        </div>
                      )}
                      {(kbMatch != null || aiCurrent != null) && aiAfter != null && (
                        <div className="text-muted-foreground">{"\u2192"}</div>
                      )}
                      {aiAfter != null && (
                        <div className="text-center">
                          <div className="text-xl font-bold text-blue-700">{aiAfter}%</div>
                          <div className="text-xs text-muted-foreground">Generated resume</div>
                        </div>
                      )}
                    </div>

                    {/* Algorithmic breakdown */}
                    {algoBreakdown && (
                      <div className="mt-3 pt-3 border-t border-blue-100 grid grid-cols-2 md:grid-cols-4 gap-3">
                        {[
                          { key: "skills_overlap", label: "Skills match" },
                          { key: "experience_years", label: "Experience" },
                          { key: "tfidf", label: "Text similarity" },
                          { key: "semantic_sim", label: "Semantic match" },
                        ].map(({ key, label }) => {
                          const val = algoBreakdown[key]
                          if (val == null) return null
                          const pct = Math.round(val * 100)
                          return (
                            <div key={key}>
                              <div className="flex items-center justify-between mb-1">
                                <span className="text-xs text-muted-foreground">{label}</span>
                                <span className="text-xs font-medium">{pct}%</span>
                              </div>
                              <div className="bg-white rounded-full h-1.5">
                                <div className="bg-blue-400 rounded-full h-1.5 transition-all" style={{ width: `${pct}%` }} />
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                )
              })()}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Resume */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold">Resume</h3>
                    <div className="flex gap-1">
                      {["pdf", "docx", "md"].map((fmt) => (
                        <Button key={fmt} variant="ghost" size="sm" disabled={exporting}
                          onClick={() => handleExport("resume", fmt)}>
                          {fmt.toUpperCase()}
                        </Button>
                      ))}
                    </div>
                  </div>
                  <pre className="bg-muted p-4 rounded-lg text-sm whitespace-pre-wrap font-mono overflow-auto max-h-96">
                    {resume.content}
                  </pre>
                </div>

                {/* Cover Letter */}
                {coverLetter && (
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-semibold">Cover Letter</h3>
                      <div className="flex gap-1">
                        {["pdf", "docx", "md"].map((fmt) => (
                          <Button key={fmt} variant="ghost" size="sm" disabled={exporting}
                            onClick={() => handleExport("coverLetter", fmt)}>
                            {fmt.toUpperCase()}
                          </Button>
                        ))}
                      </div>
                    </div>
                    <pre className="bg-muted p-4 rounded-lg text-sm whitespace-pre-wrap font-mono overflow-auto max-h-96">
                      {coverLetter.content}
                    </pre>
                  </div>
                )}
              </div>
            </CardContent>

            <div className="p-4 border-t flex justify-between shrink-0">
              <Button variant="ghost" onClick={() => setStep("analysis")}>
                {"\u2190"} Back to analysis
              </Button>
              <div className="flex items-center gap-3">
                {applyError && <span className="text-sm text-destructive">{applyError}</span>}
                <Button variant="outline" onClick={onClose}>Cancel</Button>
                <Button onClick={handleApply} className="bg-blue-600 hover:bg-blue-700">
                  Apply & Track
                </Button>
              </div>
            </div>
          </>
        )}
      </Card>
    </div>
  )
}
