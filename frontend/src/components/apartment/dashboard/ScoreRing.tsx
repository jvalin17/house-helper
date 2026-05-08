/**
 * ScoreRing — circular SVG progress indicator.
 *
 * Renders a ring that fills proportionally to `score` (0-100).
 * Used for match scores and completion tracking on dashboard cards.
 */

interface ScoreRingProps {
  score: number
  size?: number
  strokeWidth?: number
  color?: string
}

export default function ScoreRing({
  score,
  size = 48,
  strokeWidth = 4,
  color = "#6366f1",
}: ScoreRingProps) {
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const clampedScore = Math.max(0, Math.min(100, score))
  const strokeDashoffset = circumference - (clampedScore / 100) * circumference

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        {/* Background track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={strokeWidth}
        />
        {/* Progress arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          className="transition-all duration-500 ease-out"
        />
      </svg>
      <span
        className="absolute text-xs font-semibold"
        style={{ color }}
      >
        {clampedScore}
      </span>
    </div>
  )
}
