import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { api } from "@/api/client"

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
  const [loading, setLoading] = useState(true)
  const [applied, setApplied] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [emptyKB, setEmptyKB] = useState(false)

  useEffect(() => {
    generateDocs()
  }, [jobId])

  const generateDocs = async () => {
    setLoading(true)
    try {
      // Check if knowledge bank has data
      const kb = await api.listEntries() as { experiences: unknown[] }
      if (!kb.experiences || kb.experiences.length === 0) {
        setEmptyKB(true)
        setLoading(false)
        return
      }

      const [r, cl] = await Promise.all([
        api.generateResume(jobId),
        api.generateCoverLetter(jobId),
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

    // Save edited cover letter if changed
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
            <p className="text-sm text-muted-foreground mt-1">Review before applying</p>
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
                Go to <strong>Knowledge Bank</strong> tab and use "Import Resume" or add experiences manually.
              </p>
            </div>
          </CardContent>
        ) : loading ? (
          <CardContent className="flex-1 flex items-center justify-center">
            <p className="text-muted-foreground">Generating resume and cover letter...</p>
          </CardContent>
        ) : (
          <>
            <CardContent className="flex-1 overflow-auto">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Resume Preview */}
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
                </div>

                {/* Cover Letter Preview (editable) */}
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
                </div>
              </div>
            </CardContent>

            <div className="p-4 border-t flex justify-end gap-3 shrink-0">
              <Button variant="outline" onClick={onClose}>Cancel</Button>
              <Button onClick={handleApply} className="bg-green-600 hover:bg-green-700">
                Apply & Track
              </Button>
            </div>
          </>
        )}
      </Card>
    </div>
  )
}
