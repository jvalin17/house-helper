import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { api } from "@/api/client"
import GenerationPrefs from "@/components/GenerationPrefs"

interface Props {
  jobId: number
  jobTitle: string
  company: string
  onClose: () => void
}

export default function PreviewModal({ jobId, jobTitle, company, onClose }: Props) {
  const [resume, setResume] = useState<{ id: number; content: string } | null>(null)
  const [coverLetter, setCoverLetter] = useState<{ id: number; content: string } | null>(null)
  const [clContent, setClContent] = useState("")
  const [loading, setLoading] = useState(false)
  const [applied, setApplied] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [emptyKB, setEmptyKB] = useState(false)
  const [showPrefs, setShowPrefs] = useState(true)
  const [feedbackGiven, setFeedbackGiven] = useState<Record<string, number>>({})

  useEffect(() => {
    checkKnowledgeBank()
  }, [])

  const checkKnowledgeBank = async () => {
    const kb = await api.listEntries() as { experiences: unknown[] }
    // #region agent log
    ;(window as unknown as { __dbgLog?: (l: string, m: string, d?: Record<string, unknown>) => void }).__dbgLog?.(
      'PreviewModal.tsx:checkKnowledgeBank',
      'kb response',
      {
        hypothesisId: 'CRASH-4',
        kb_typeof: typeof kb,
        kb_is_array: Array.isArray(kb),
        kb_keys: kb && typeof kb === 'object' && !Array.isArray(kb) ? Object.keys(kb as object) : null,
        experiences_typeof: typeof (kb as { experiences?: unknown }).experiences,
        experiences_is_array: Array.isArray((kb as { experiences?: unknown }).experiences),
      }
    )
    // #endregion
    if (!kb.experiences || kb.experiences.length === 0) {
      setEmptyKB(true)
    }
  }

  const generateDocs = async (preferences: Record<string, unknown>) => {
    setLoading(true)
    setShowPrefs(false)
    try {
      const [r, cl] = await Promise.all([
        api.generateResume(jobId, preferences),
        api.generateCoverLetter(jobId, preferences),
      ])
      setResume(r)
      setCoverLetter(cl)
      setClContent(cl.content)
    } catch (err) {
      console.error("Generation failed:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleApply = async () => {
    if (!resume || !coverLetter) return
    if (clContent !== coverLetter.content) {
      await api.updateCoverLetter(coverLetter.id, clContent)
    }
    await api.createApplication(jobId, resume.id, coverLetter.id)
    setApplied(true)
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

  const handleFeedback = async (type: "resume" | "coverLetter", rating: number) => {
    const id = type === "resume" ? resume!.id : coverLetter!.id
    await api.resumeFeedback(id, rating)
    setFeedbackGiven((prev) => ({ ...prev, [type]: rating }))
  }

  // Applied confirmation
  if (applied) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <Card className="max-w-md w-full text-center">
          <CardContent className="py-12">
            <div className="text-5xl mb-4">&#127881;</div>
            <h2 className="text-2xl font-bold mb-2">Thank you for applying!</h2>
            <p className="text-muted-foreground mb-6">
              Your application to <strong>{company}</strong> for <strong>{jobTitle}</strong> has been tracked.
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
            <CardTitle>Preview: {jobTitle} at {company}</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              {showPrefs ? "Configure your preferences" : "Review before applying"}
            </p>
          </div>
          <Button variant="ghost" onClick={onClose}>Close</Button>
        </CardHeader>

        {emptyKB ? (
          <CardContent className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="text-4xl mb-3">&#128221;</div>
              <h3 className="font-semibold mb-2">Knowledge Bank is Empty</h3>
              <p className="text-muted-foreground mb-4">
                Import your resume first so the agent can generate tailored documents.
              </p>
              <p className="text-sm text-muted-foreground">
                Go to the <strong>Jobs</strong> tab and use "Import Your Resume" at the top.
              </p>
            </div>
          </CardContent>
        ) : showPrefs ? (
          <CardContent className="flex-1 overflow-auto">
            <GenerationPrefs onGenerate={generateDocs} loading={loading} />
          </CardContent>
        ) : loading ? (
          <CardContent className="flex-1 flex items-center justify-center">
            <p className="text-muted-foreground">Generating resume and cover letter...</p>
          </CardContent>
        ) : (
          <>
            <CardContent className="flex-1 overflow-auto">
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
                    {resume?.content}
                  </pre>
                  {/* Feedback */}
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-sm text-muted-foreground">Rate:</span>
                    {[{ icon: "\uD83D\uDC4D", val: 1 }, { icon: "\uD83D\uDC4E", val: -1 }].map(({ icon, val }) => (
                      <Button
                        key={val}
                        variant={feedbackGiven.resume === val ? "default" : "ghost"}
                        size="sm"
                        onClick={() => handleFeedback("resume", val)}
                      >
                        {icon}
                      </Button>
                    ))}
                  </div>
                </div>

                {/* Cover Letter */}
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
                  <Textarea
                    value={clContent}
                    onChange={(e) => setClContent(e.target.value)}
                    rows={16}
                    className="font-mono text-sm"
                  />
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-sm text-muted-foreground">Rate:</span>
                    {[{ icon: "\uD83D\uDC4D", val: 1 }, { icon: "\uD83D\uDC4E", val: -1 }].map(({ icon, val }) => (
                      <Button
                        key={val}
                        variant={feedbackGiven.coverLetter === val ? "default" : "ghost"}
                        size="sm"
                        onClick={() => handleFeedback("coverLetter", val)}
                      >
                        {icon}
                      </Button>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>

            <div className="p-4 border-t flex justify-between shrink-0">
              <Button variant="ghost" onClick={() => setShowPrefs(true)}>
                ← Change Preferences
              </Button>
              <div className="flex gap-3">
                <Button variant="outline" onClick={onClose}>Cancel</Button>
                <Button onClick={handleApply} className="bg-green-600 hover:bg-green-700">
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
