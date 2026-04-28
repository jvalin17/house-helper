import type { ReactNode } from "react"

interface ModalProps {
  onClose: () => void
  children: ReactNode
  className?: string
}

/** Reusable modal overlay with backdrop click to close and dialog role. */
export default function Modal({ onClose, children, className = "" }: ModalProps) {
  return (
    <div
      role="dialog"
      aria-modal="true"
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div className={className} onClick={(e) => e.stopPropagation()}>
        {children}
      </div>
    </div>
  )
}
