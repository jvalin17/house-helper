/**
 * AchievementBadges — row of badge icons for earned hunt achievements.
 *
 * Unlocked badges show filled, colored circles with emoji icons and pulse
 * animation. Locked badges appear gray and dimmed. Hover shows title tooltip.
 */

import type { Achievement } from "@/types"

const ACHIEVEMENT_ICONS: Record<string, string> = {
  first_save: "\u{1F3E0}",
  explorer: "\u{1F50D}",
  triple_visit: "\u{1F440}",
  first_apply: "\u{1F4DD}",
  triple_apply: "\u{1F3AF}",
  approved: "\u{2705}",
  home_sweet_home: "\u{1F3E1}",
}

const ACHIEVEMENT_COLORS: Record<string, { background: string; ring: string }> = {
  first_save: { background: "bg-indigo-100", ring: "ring-indigo-300" },
  explorer: { background: "bg-purple-100", ring: "ring-purple-300" },
  triple_visit: { background: "bg-violet-100", ring: "ring-violet-300" },
  first_apply: { background: "bg-amber-100", ring: "ring-amber-300" },
  triple_apply: { background: "bg-rose-100", ring: "ring-rose-300" },
  approved: { background: "bg-emerald-100", ring: "ring-emerald-300" },
  home_sweet_home: { background: "bg-green-100", ring: "ring-green-300" },
}

interface AchievementBadgesProps {
  achievements: Achievement[]
}

export default function AchievementBadges({ achievements }: AchievementBadgesProps) {
  if (achievements.length === 0) return null

  return (
    <div className="flex items-center gap-2 flex-wrap">
      {achievements.map((achievement) => {
        const iconEmoji = ACHIEVEMENT_ICONS[achievement.id] ?? "\u{2B50}"
        const colors = ACHIEVEMENT_COLORS[achievement.id] ?? { background: "bg-gray-100", ring: "ring-gray-300" }
        const isUnlocked = achievement.unlocked

        return (
          <div
            key={achievement.id}
            title={`${achievement.title}${isUnlocked ? "" : " (locked)"}`}
            className={`
              w-9 h-9 rounded-full flex items-center justify-center text-sm
              transition-all duration-300
              ${isUnlocked
                ? `${colors.background} ring-1 ${colors.ring} achievement-badge-pulse`
                : "bg-gray-100 opacity-40 grayscale"
              }
            `}
          >
            <span role="img" aria-label={achievement.title}>
              {iconEmoji}
            </span>
          </div>
        )
      })}

      <style>{`
        @keyframes achievementPulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.08); }
        }
        .achievement-badge-pulse {
          animation: achievementPulse 2s ease-in-out 1;
        }
      `}</style>
    </div>
  )
}
