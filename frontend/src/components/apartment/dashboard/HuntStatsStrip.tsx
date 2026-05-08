/**
 * HuntStatsStrip — horizontal stats strip with key hunt metrics.
 *
 * Shows total saved, visited, applied, average rent, hunt duration,
 * a completion ring, and achievement badges below.
 */

import ScoreRing from "@/components/apartment/dashboard/ScoreRing"
import AchievementBadges from "@/components/apartment/dashboard/AchievementBadges"
import type { DashboardStats, Achievement } from "@/types"

interface HuntStatsStripProps {
  stats: DashboardStats
  achievements: Achievement[]
}

function calculateHuntDurationDays(huntStartedAt: string | null): number | null {
  if (!huntStartedAt) return null
  const startDate = new Date(huntStartedAt)
  const currentDate = new Date()
  const millisecondsDifference = currentDate.getTime() - startDate.getTime()
  const daysDifference = Math.floor(millisecondsDifference / (1000 * 60 * 60 * 24))
  return Math.max(daysDifference, 0)
}

function calculateCompletionPercentage(stats: DashboardStats): number {
  const totalListings = stats.total_saved
  if (totalListings === 0) return 0
  const listingsPastInterested =
    stats.visited_count + stats.applied_count + stats.approved_count + stats.moved_in_count
  return Math.round((listingsPastInterested / totalListings) * 100)
}

export default function HuntStatsStrip({ stats, achievements }: HuntStatsStripProps) {
  const huntDurationDays = calculateHuntDurationDays(stats.hunt_started_at)
  const completionPercentage = calculateCompletionPercentage(stats)
  const unlockedAchievements = achievements.filter((achievement) => achievement.unlocked)

  return (
    <div className="rounded-2xl bg-white border shadow-sm p-5 space-y-4">
      <div className="flex items-center gap-6 flex-wrap">
        {/* Stats mini cards */}
        <div className="flex items-center gap-5 flex-wrap flex-1">
          <StatsMiniCard
            label="Total Saved"
            value={stats.total_saved}
            valueColor="text-indigo-600"
          />
          <StatsMiniCard
            label="Visited"
            value={stats.visited_count}
            valueColor="text-purple-600"
          />
          <StatsMiniCard
            label="Applied"
            value={stats.applied_count}
            valueColor="text-amber-600"
          />
          <StatsMiniCard
            label="Avg Rent"
            value={stats.average_rent ? `$${Math.round(stats.average_rent).toLocaleString()}/mo` : "--"}
            valueColor="text-gray-600"
          />
          {huntDurationDays !== null && (
            <StatsMiniCard
              label="Hunt Duration"
              value={`${huntDurationDays} day${huntDurationDays !== 1 ? "s" : ""}`}
              valueColor="text-gray-600"
            />
          )}
        </div>

        {/* Completion ring */}
        <div className="flex flex-col items-center gap-1">
          <ScoreRing score={completionPercentage} size={48} strokeWidth={4} color="#8b5cf6" />
          <span className="text-[10px] text-gray-400">Progress</span>
        </div>
      </div>

      {/* Achievement badges row */}
      {unlockedAchievements.length > 0 && (
        <div className="pt-2 border-t border-gray-100">
          <p className="text-xs text-gray-400 mb-2">Achievements</p>
          <AchievementBadges achievements={achievements} />
        </div>
      )}
    </div>
  )
}

// ── Sub-component ───────────────────────────────

interface StatsMiniCardProps {
  label: string
  value: number | string
  valueColor: string
}

function StatsMiniCard({ label, value, valueColor }: StatsMiniCardProps) {
  return (
    <div className="text-center min-w-[60px]">
      <p className={`text-xl font-bold ${valueColor}`}>{value}</p>
      <p className="text-[10px] text-gray-400 mt-0.5">{label}</p>
    </div>
  )
}
