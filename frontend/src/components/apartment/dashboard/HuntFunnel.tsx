/**
 * HuntFunnel — SVG-based funnel visualization for apartment hunt stages.
 *
 * Renders 5 horizontal bands (one per stage) with widths proportional to
 * listing counts. Selected band shows brighter fill with a subtle glow.
 * Uses CSS transitions for smooth width changes.
 */

const STAGE_ORDER = ["interested", "visited", "applied", "approved", "moved_in"]

const STAGE_LABELS: Record<string, string> = {
  interested: "Interested",
  visited: "Visited",
  applied: "Applied",
  approved: "Approved",
  moved_in: "Moved In",
}

const STAGE_FILL_COLORS: Record<string, { normal: string; selected: string; glow: string }> = {
  interested: { normal: "#a5b4fc", selected: "#818cf8", glow: "#6366f1" },
  visited: { normal: "#d8b4fe", selected: "#c084fc", glow: "#a855f7" },
  applied: { normal: "#fcd34d", selected: "#fbbf24", glow: "#f59e0b" },
  approved: { normal: "#6ee7b7", selected: "#34d399", glow: "#10b981" },
  moved_in: { normal: "#4ade80", selected: "#22c55e", glow: "#16a34a" },
}

interface HuntFunnelProps {
  stages: Record<string, { count: number }>
  selectedStage: string
  onSelectStage: (stage: string) => void
}

const FUNNEL_HEIGHT = 48
const BAND_HEIGHT = FUNNEL_HEIGHT
const MIN_BAND_WIDTH = 60
const BAND_GAP = 2
const BAND_RADIUS = 6

export default function HuntFunnel({ stages, selectedStage, onSelectStage }: HuntFunnelProps) {
  const totalCount = STAGE_ORDER.reduce(
    (total, stage) => total + (stages[stage]?.count ?? 0),
    0,
  )

  // Calculate proportional widths with minimum
  const rawWidths = STAGE_ORDER.map((stage) => {
    const count = stages[stage]?.count ?? 0
    if (totalCount === 0) return 1
    return Math.max(count / totalCount, 0)
  })

  // Normalize so all add up to 1 (after applying minimums)
  const totalRaw = rawWidths.reduce((sum, width) => sum + width, 0)
  const normalizedWidths = rawWidths.map((width) => (totalRaw > 0 ? width / totalRaw : 0.2))

  return (
    <div className="rounded-2xl bg-white border shadow-sm p-5">
      <h3 className="text-sm font-medium text-gray-500 mb-3">Hunt Progress</h3>
      <div
        className="flex items-center gap-[2px]"
        style={{ height: FUNNEL_HEIGHT }}
        role="group"
        aria-label="Hunt funnel stages"
      >
        {STAGE_ORDER.map((stage, stageIndex) => {
          const stageCount = stages[stage]?.count ?? 0
          const isSelected = selectedStage === stage
          const colors = STAGE_FILL_COLORS[stage] ?? STAGE_FILL_COLORS.interested
          const widthPercent = normalizedWidths[stageIndex] * 100

          return (
            <button
              key={stage}
              onClick={() => onSelectStage(stage)}
              className="relative flex items-center justify-center overflow-hidden cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
              style={{
                width: `${widthPercent}%`,
                minWidth: MIN_BAND_WIDTH,
                height: BAND_HEIGHT,
                backgroundColor: isSelected ? colors.selected : colors.normal,
                borderRadius: BAND_RADIUS,
                boxShadow: isSelected ? `0 0 12px 2px ${colors.glow}40` : "none",
                opacity: isSelected ? 1 : 0.75,
                transition: "width 0.4s ease, background-color 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease",
              }}
              title={`${STAGE_LABELS[stage]}: ${stageCount}`}
              aria-label={`${STAGE_LABELS[stage]}: ${stageCount} listings`}
              aria-pressed={isSelected}
            >
              <span className="text-xs font-semibold text-white truncate px-2 drop-shadow-sm">
                {STAGE_LABELS[stage]} ({stageCount})
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
