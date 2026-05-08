/**
 * CelebrationOverlay — full-screen achievement celebration with confetti.
 *
 * Triggered when a stage advance unlocks an achievement. Shows the
 * achievement icon, title, and description with CSS-animated confetti
 * particles. Auto-dismisses after 3 seconds or on click.
 */

import { useEffect, useState, useRef, useCallback } from "react"
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

const CONFETTI_COLORS = ["#6366f1", "#a855f7", "#10b981", "#f59e0b", "#ec4899"]
const CONFETTI_PARTICLE_COUNT = 25

interface ConfettiParticle {
  id: number
  left: number
  delay: number
  duration: number
  color: string
  size: number
  rotation: number
}

interface CelebrationOverlayProps {
  achievement: Achievement
  onDismiss: () => void
}

function generateConfettiParticles(): ConfettiParticle[] {
  return Array.from({ length: CONFETTI_PARTICLE_COUNT }, (_, index) => ({
    id: index,
    left: Math.random() * 100,
    delay: Math.random() * 0.8,
    duration: 1.5 + Math.random() * 1,
    color: CONFETTI_COLORS[Math.floor(Math.random() * CONFETTI_COLORS.length)],
    size: 6 + Math.random() * 6,
    rotation: Math.random() * 360,
  }))
}

export default function CelebrationOverlay({ achievement, onDismiss }: CelebrationOverlayProps) {
  const [confettiParticles] = useState<ConfettiParticle[]>(() => generateConfettiParticles())
  const [isVisible, setIsVisible] = useState(false)
  const autoDismissTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const handleDismiss = useCallback(() => {
    setIsVisible(false)
    // Wait for fade-out transition before calling onDismiss
    setTimeout(onDismiss, 200)
  }, [onDismiss])

  useEffect(() => {
    // Fade in on mount
    requestAnimationFrame(() => setIsVisible(true))

    // Auto-dismiss after 3 seconds
    autoDismissTimerRef.current = setTimeout(handleDismiss, 3000)

    return () => {
      if (autoDismissTimerRef.current) {
        clearTimeout(autoDismissTimerRef.current)
      }
    }
  }, [handleDismiss])

  const iconEmoji = ACHIEVEMENT_ICONS[achievement.id] ?? "\u{2B50}"

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center cursor-pointer"
      onClick={handleDismiss}
      role="dialog"
      aria-label={`Achievement unlocked: ${achievement.title}`}
      style={{
        backgroundColor: isVisible ? "rgba(0, 0, 0, 0.4)" : "rgba(0, 0, 0, 0)",
        transition: "background-color 0.3s ease",
      }}
    >
      {/* Confetti particles */}
      {confettiParticles.map((particle) => (
        <div
          key={particle.id}
          className="confetti-particle"
          style={{
            position: "absolute",
            top: -12,
            left: `${particle.left}%`,
            width: particle.size,
            height: particle.size,
            backgroundColor: particle.color,
            borderRadius: particle.size > 9 ? "2px" : "50%",
            animationDelay: `${particle.delay}s`,
            animationDuration: `${particle.duration}s`,
            transform: `rotate(${particle.rotation}deg)`,
          }}
        />
      ))}

      {/* Achievement card */}
      <div
        className="bg-white rounded-2xl shadow-2xl p-8 max-w-sm mx-4 text-center"
        style={{
          transform: isVisible ? "scale(1)" : "scale(0.8)",
          opacity: isVisible ? 1 : 0,
          transition: "transform 0.3s ease, opacity 0.3s ease",
        }}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="text-5xl mb-4 celebration-bounce">
          <span role="img" aria-label={achievement.title}>{iconEmoji}</span>
        </div>
        <p className="text-xs font-semibold text-indigo-500 uppercase tracking-wider mb-1">
          Achievement Unlocked
        </p>
        <h2 className="text-xl font-bold text-gray-800 mb-2">
          {achievement.title}
        </h2>
        <p className="text-sm text-gray-500">
          {achievement.description}
        </p>
        <button
          onClick={handleDismiss}
          className="mt-5 px-5 py-2 text-sm font-medium text-white bg-indigo-500 rounded-lg hover:bg-indigo-600 transition-colors cursor-pointer"
        >
          Awesome!
        </button>
      </div>

      <style>{`
        @keyframes confettiFall {
          0% {
            transform: translateY(0) rotate(0deg);
            opacity: 1;
          }
          100% {
            transform: translateY(100vh) rotate(720deg);
            opacity: 0;
          }
        }
        .confetti-particle {
          animation-name: confettiFall;
          animation-timing-function: cubic-bezier(0.25, 0.46, 0.45, 0.94);
          animation-fill-mode: forwards;
          pointer-events: none;
        }
        @keyframes celebrationBounce {
          0%, 100% { transform: scale(1); }
          30% { transform: scale(1.2); }
          50% { transform: scale(0.95); }
          70% { transform: scale(1.05); }
        }
        .celebration-bounce {
          animation: celebrationBounce 0.6s ease-out 0.3s 1;
        }
      `}</style>
    </div>
  )
}
