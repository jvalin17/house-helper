/**
 * ResumeResult — shows the generated resume with download options.
 *
 * Step 3 in the generate flow.
 * Clean resume content, no analysis mixed in.
 */

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { api } from "@/api/client"

interface Props {
  resume: { id: number; content: string; analysis?: Record<string, unknown> }
  coverLetter: { id: number; content: string } | null
  company: string
  onBack: () => void
}

export default function ResumeResult({ resume, coverLetter, company, onBack }: Props) {
  const handleExport = async (type: "resume" | "coverLetter", format: string) => {
    const id = type === "resume" ? resume.id : coverLetter?.id
    if (!id) return
    const response = type === "resume"
      ? await api.exportResume(id, format)
      : await api.exportCoverLetter(id, format)
    const blob = await response.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `${type}_${company}.${format}`
    a.click()
    URL.revokeObjectURL(url)
  }

  const analysis = resume.analysis as Record<string, unknown> | undefined
  const newMatch = analysis?.new_match as number | undefined
  const origMatch = analysis?.original_match as number | undefined
  const improvement = analysis?.improvement as string | undefined

  return (
    <div className="space-y-4">
      {/* Match result */}
      {newMatch && (
        <div className="p-3 rounded-lg bg-blue-50/50 border border-blue-100">
          <span className="text-sm font-semibold">New match: {newMatch}%</span>
          {origMatch && (
            <span className="text-sm text-muted-foreground ml-2">(was {origMatch}%, {improvement})</span>
          )}
        </div>
      )}

      {/* Resume */}
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

      {/* Cover Letter */}
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

      <Button variant="outline" onClick={onBack}>Generate for another job</Button>
    </div>
  )
}
