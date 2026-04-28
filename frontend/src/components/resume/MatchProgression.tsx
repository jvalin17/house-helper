import type { AnalysisData } from "@/types"

interface Props {
  algoScore: number | null
  algoBreakdown: Record<string, number> | null
  analysis: AnalysisData | null
  resumeAnalysis: Record<string, unknown> | undefined
}

/** Displays the match score progression: Algorithmic → LLM → KB → Generated */
export default function MatchProgression({ algoScore, algoBreakdown, analysis, resumeAnalysis }: Props) {
  const aiCurrent = (analysis?.current_resume_match ?? resumeAnalysis?.original_match) as number | undefined
  const kbMatch = analysis?.knowledge_bank_match as number | undefined
  const aiAfter = resumeAnalysis?.new_match as number | undefined
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
        {algoScore != null && aiCurrent != null && <div className="text-muted-foreground">{"\u2192"}</div>}
        {aiCurrent != null && (
          <div className="text-center">
            <div className="text-xl font-bold">{aiCurrent}%</div>
            <div className="text-xs text-muted-foreground">LLM analysis (current resume)</div>
          </div>
        )}
        {aiCurrent != null && kbMatch != null && <div className="text-muted-foreground">{"\u2192"}</div>}
        {kbMatch != null && (
          <div className="text-center">
            <div className="text-xl font-bold">{kbMatch}%</div>
            <div className="text-xs text-muted-foreground">Knowledge bank potential</div>
          </div>
        )}
        {(kbMatch != null || aiCurrent != null) && aiAfter != null && <div className="text-muted-foreground">{"\u2192"}</div>}
        {aiAfter != null && (
          <div className="text-center">
            <div className="text-xl font-bold text-blue-700">{aiAfter}%</div>
            <div className="text-xs text-muted-foreground">Generated resume</div>
          </div>
        )}
      </div>

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
}
