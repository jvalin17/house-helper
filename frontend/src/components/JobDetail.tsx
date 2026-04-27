import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"

interface Props {
  job: Record<string, unknown>
  onClose: () => void
  onGenerate: () => void
  onRate: (rating: string) => void
}

export default function JobDetail({ job, onClose, onGenerate, onRate }: Props) {
  // #region agent log
  ;(window as unknown as { __dbgLog?: (l: string, m: string, d?: Record<string, unknown>) => void }).__dbgLog?.(
    'JobDetail.tsx:render',
    'JobDetail render input',
    {
      hypothesisId: 'CRASH-1',
      job_id: job.id,
      parsed_data_type: typeof job.parsed_data,
      parsed_data_preview: typeof job.parsed_data === 'string' ? (job.parsed_data as string).slice(0, 200) : null,
      match_breakdown_type: typeof job.match_breakdown,
      match_breakdown_preview: typeof job.match_breakdown === 'string' ? (job.match_breakdown as string).slice(0, 200) : null,
    }
  )
  // #endregion

  const parsed = typeof job.parsed_data === "string"
    ? JSON.parse(job.parsed_data as string)
    : (job.parsed_data || {}) as Record<string, unknown>

  const matchBreakdown = typeof job.match_breakdown === "string"
    ? JSON.parse(job.match_breakdown as string)
    : (job.match_breakdown || null) as Record<string, number> | null

  // #region agent log
  ;(window as unknown as { __dbgLog?: (l: string, m: string, d?: Record<string, unknown>) => void }).__dbgLog?.(
    'JobDetail.tsx:after-parse',
    'JobDetail post-parse',
    {
      hypothesisId: 'CRASH-1',
      parsed_is_null: parsed === null,
      parsed_typeof: typeof parsed,
      parsed_keys: parsed && typeof parsed === 'object' ? Object.keys(parsed as object).slice(0, 20) : null,
      matchBreakdown_is_null: matchBreakdown === null,
      matchBreakdown_typeof: typeof matchBreakdown,
    }
  )
  // #endregion

  const requiredSkills = (parsed.required_skills || []) as string[]
  const preferredSkills = (parsed.preferred_skills || []) as string[]
  const description = (parsed.description || "") as string

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <Card className="max-w-2xl w-full max-h-[85vh] overflow-auto">
        <CardHeader className="flex flex-row items-start justify-between">
          <div>
            <CardTitle>{String(job.title || "Untitled")}</CardTitle>
            <p className="text-muted-foreground">{String(job.company || "Unknown company")}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>Close</Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Match Score */}
          {job.match_score != null && (
            <div className="p-4 bg-muted rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium">Match Score</span>
                <span className="text-2xl font-bold">{Math.round((job.match_score as number) * 100)}%</span>
              </div>

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
            {parsed.location && <span>&#128205; {String(parsed.location)}</span>}
            {parsed.salary_range && <span>&#128176; {String(parsed.salary_range)}</span>}
            {parsed.remote_status && <Badge variant="secondary">{String(parsed.remote_status)}</Badge>}
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
