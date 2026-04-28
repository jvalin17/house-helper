/**
 * ResumeAnalysis — shows fit analysis with selectable improvements.
 *
 * Step 2 in the generate flow:
 * 1. User clicks Generate → analyze endpoint called
 * 2. This component shows results with checkboxes
 * 3. User picks suggestions → clicks Apply & Generate
 */

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { api } from "@/api/client"
import type { Suggestion, AnalysisData } from "@/types"

interface Props {
  analysis: AnalysisData
  jobTitle: string
  company: string
  onApplyAndGenerate: (selectedSuggestions: Suggestion[], userInstructions?: string) => void
  onSkip: (userInstructions?: string) => void
  loading: boolean
}

export default function ResumeAnalysis({
  analysis, jobTitle, company, onApplyAndGenerate, onSkip, loading,
}: Props) {
  const [selected, setSelected] = useState<Set<number>>(
    new Set(analysis.suggested_improvements.map((_, i) => i))
  )
  const [userInstructions, setUserInstructions] = useState("")
  const [flagged, setFlagged] = useState<Set<number>>(new Set())

  const toggle = (idx: number) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx); else next.add(idx)
      return next
    })
  }

  const handleApply = () => {
    const picks = analysis.suggested_improvements.filter((_, i) => selected.has(i))
    onApplyAndGenerate(picks, userInstructions.trim() || undefined)
  }

  return (
    <div className="space-y-4">
      {/* Match overview */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{jobTitle} at {company}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-6 mb-4">
            <div>
              <div className="text-2xl font-bold">{analysis.current_resume_match}%</div>
              <div className="text-xs text-muted-foreground">Current resume</div>
            </div>
            <div className="text-muted-foreground self-center">{"\u2192"}</div>
            <div>
              <div className="text-2xl font-bold text-blue-700">{analysis.knowledge_bank_match}%</div>
              <div className="text-xs text-muted-foreground">Possible with edits</div>
            </div>
            <div className="self-center text-sm text-muted-foreground">{analysis.match_gap}</div>
          </div>

          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="font-medium mb-1">Strengths</p>
              <ul className="space-y-0.5">
                {analysis.strengths.map((s, i) => (
                  <li key={i} className="text-muted-foreground">+ {s}</li>
                ))}
              </ul>
            </div>
            <div>
              <p className="font-medium mb-1">Gaps</p>
              <ul className="space-y-0.5">
                {analysis.gaps.map((g, i) => (
                  <li key={i} className="text-muted-foreground">- {g}</li>
                ))}
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Suggested improvements with checkboxes */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Suggested Improvements</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {analysis.suggested_improvements.map((suggestion, idx) => (
              <label key={idx}
                className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                  flagged.has(idx) ? "border-destructive/30 bg-destructive/5 opacity-50" :
                  selected.has(idx) ? "border-blue-300 bg-blue-50/30" : "border-border hover:border-border/80"
                }`}>
                <input type="checkbox" checked={selected.has(idx)}
                  onChange={() => toggle(idx)}
                  aria-label={suggestion.description}
                  className="mt-0.5 w-4 h-4 accent-primary" />
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs px-1.5 py-0.5 rounded bg-muted text-muted-foreground">{suggestion.type.replace(/_/g, " ")}</span>
                    <span className="text-xs text-blue-600 font-medium">{suggestion.impact}</span>
                    {flagged.has(idx) ? (
                      <span className="ml-auto text-xs text-destructive">Flagged</span>
                    ) : (
                      <button
                        type="button"
                        className="ml-auto text-xs text-muted-foreground hover:text-destructive transition-colors"
                        title="Flag as incorrect — this suggestion won't appear again"
                        onClick={(e) => {
                          e.preventDefault()
                          e.stopPropagation()
                          api.rejectSuggestion({
                            suggestion_text: suggestion.description,
                            original_bullet: suggestion.source,
                          }).then(() => {
                            setFlagged((prev) => new Set(prev).add(idx))
                            setSelected((prev) => { const next = new Set(prev); next.delete(idx); return next })
                          }).catch(() => {})
                        }}
                      >
                        Flag incorrect
                      </button>
                    )}
                  </div>
                  <p className="text-sm mt-1">{suggestion.description}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">Source: {suggestion.source}</p>
                </div>
              </label>
            ))}
          </div>

          {analysis.summary && (
            <p className="text-xs text-muted-foreground mt-4 p-3 bg-muted/50 rounded-lg">
              {analysis.summary}
            </p>
          )}

          <div className="mt-4">
            <Textarea
              placeholder="Additional instructions (optional) — e.g., &quot;Show only 6 years of experience&quot;, &quot;Focus on backend only&quot;, &quot;Target as mid-level role&quot;"
              value={userInstructions}
              onChange={(e) => setUserInstructions(e.target.value)}
              rows={2}
              className="text-sm"
            />
          </div>

          <div className="flex gap-3 mt-3">
            {(() => {
              const resumeChanges = analysis.suggested_improvements.filter(
                (s, i) => selected.has(i) && s.type !== "consider" && s.type !== "cover_letter_only"
              ).length
              const label = resumeChanges > 0
                ? `Apply ${resumeChanges} Change${resumeChanges !== 1 ? "s" : ""} & Generate Resume`
                : "Generate Resume"
              return (
                <Button onClick={handleApply} disabled={loading || selected.size === 0}>
                  {loading ? "Generating..." : label}
                </Button>
              )
            })()}
            <Button variant="outline" onClick={() => onSkip(userInstructions.trim() || undefined)} disabled={loading}>
              Generate without changes
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
