import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import type { Job } from "@/types"

function LLMAnalysis({ breakdown }: { breakdown: Record<string, number> | null }) {
  if (!breakdown) return null
  const bd = breakdown as Record<string, unknown>
  const analysis = bd.llm_analysis as Record<string, unknown> | undefined
  if (!analysis) return null

  const strengths = (analysis.strengths || []) as string[]
  const gaps = (analysis.gaps || []) as string[]
  const recs = (analysis.recommendations || []) as string[]

  return (
    <div className="mt-3 pt-3 border-t space-y-2">
      {strengths.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground">Strengths</p>
          <ul className="text-xs text-foreground mt-1 space-y-0.5">
            {strengths.map((s, i) => <li key={i}>+ {s}</li>)}
          </ul>
        </div>
      )}
      {gaps.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground">Gaps</p>
          <ul className="text-xs text-foreground mt-1 space-y-0.5">
            {gaps.map((g, i) => <li key={i}>- {g}</li>)}
          </ul>
        </div>
      )}
      {recs.length > 0 && (
        <div>
          <p className="text-xs font-medium text-muted-foreground">Suggestions</p>
          <ul className="text-xs text-foreground mt-1 space-y-0.5">
            {recs.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      )}
    </div>
  )
}

interface Props {
  job: Job
  onClose: () => void
  onGenerate: () => void
  onRate: (rating: string) => void
}

function safeJsonParse(value: unknown, fallback: unknown = {}): unknown {
  if (typeof value !== "string") return value || fallback
  try { return JSON.parse(value) || fallback }
  catch { return fallback }
}

export default function JobDetail({ job, onClose, onGenerate, onRate }: Props) {
  const parsed = safeJsonParse(job.parsed_data, {}) as Record<string, unknown>

  const matchBreakdown = safeJsonParse(job.match_breakdown, null) as Record<string, number> | null

  const requiredSkills = (parsed.required_skills || []) as string[]
  const preferredSkills = (parsed.preferred_skills || []) as string[]
  const description = (parsed.description || "") as string

  return (
    <div role="dialog" aria-label={`Job details: ${String(job.title)}`} className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="max-w-2xl w-full max-h-[85vh] overflow-auto">
        <CardHeader className="flex flex-row items-start justify-between">
          <div>
            <CardTitle>{String(job.title || "Untitled")}</CardTitle>
            <p className="text-muted-foreground">{String(job.company || "Unknown company")}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>Close</Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Job link */}
          {(String(job.url || job.source_url || "")) && String(job.url || job.source_url || "") !== "" && (
            <a href={String(job.url || job.source_url)} target="_blank" rel="noreferrer"
              className="text-sm text-blue-600 hover:underline">
              View original job posting {"\u2192"}
            </a>
          )}

          {/* Match Score */}
          {job.match_score != null && (
            <div className="p-4 bg-muted rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium">Match Score</span>
                <span className="text-2xl font-bold">{Math.round((job.match_score as number) * 100)}%</span>
              </div>
              <p className="text-xs text-muted-foreground mb-2">
                {matchBreakdown && (matchBreakdown as Record<string, unknown>).llm_score
                  ? "Matched with AI — compares your full knowledge bank against job requirements"
                  : "Matched locally — skill overlap + text similarity against your knowledge bank"}
              </p>

              {matchBreakdown && (
                <div className="space-y-2 mt-3">
                  {Object.entries(matchBreakdown).map(([key, value]) => (
                    <div key={key} className="flex items-center gap-2">
                      <span className="text-sm text-muted-foreground w-32">{key.replace(/_/g, " ")}</span>
                      <div className="flex-1 bg-background rounded-full h-2">
                        <div className="bg-primary rounded-full h-2" style={{ width: `${(value as number) * 100}%` }} />
                      </div>
                      <span className="text-sm w-10 text-right">{Math.round((value as number) * 100)}%</span>
                    </div>
                  ))}
                </div>
              )}

              {/* LLM analysis — strengths, gaps */}
              <LLMAnalysis breakdown={matchBreakdown} />

              {/* Rate this match */}
              <div className="mt-3 pt-3 border-t">
                <p className="text-sm text-muted-foreground mb-2">Was this a good match for you?</p>
                <div className="flex gap-2">
                  {["good", "partial", "poor"].map((rating) => (
                    <Button key={rating} variant="outline" size="sm" onClick={() => onRate(rating)}>
                      {rating === "good" ? "Yes" : rating === "partial" ? "Somewhat" : "No"}
                    </Button>
                  ))}
                </div>
              </div>
            </div>
          )}

          <Separator />

          {/* Required Skills */}
          {requiredSkills.length > 0 && (
            <div>
              <h3 className="text-sm font-medium mb-2">Required Skills</h3>
              <div className="flex flex-wrap gap-2">
                {requiredSkills.map((skill) => (
                  <Badge key={skill} variant="default">{skill}</Badge>
                ))}
              </div>
            </div>
          )}

          {/* Preferred Skills */}
          {preferredSkills.length > 0 && (
            <div>
              <h3 className="text-sm font-medium mb-2">Nice to Have</h3>
              <div className="flex flex-wrap gap-2">
                {preferredSkills.map((skill) => (
                  <Badge key={skill} variant="outline">{skill}</Badge>
                ))}
              </div>
            </div>
          )}

          {/* Location / Salary */}
          <div className="flex flex-wrap gap-4 text-sm">
            {parsed.location ? <span>&#128205; {String(parsed.location)}</span> : null}
            {parsed.salary_range ? <span>&#128176; {String(parsed.salary_range)}</span> : null}
            {parsed.remote_status ? <Badge variant="secondary">{String(parsed.remote_status)}</Badge> : null}
          </div>

          {/* Description preview */}
          {description && (
            <div>
              <h3 className="text-sm font-medium mb-2">Description</h3>
              <p className="text-sm text-muted-foreground line-clamp-6">{description}</p>
            </div>
          )}

          <Separator />

          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={onClose}>Close</Button>
            <Button onClick={onGenerate}>Generate Resume & Cover Letter</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
