interface StatCardProps {
  value: string | number
  label: string
  className?: string
}

/** Reusable stat display card — value on top, label below. */
export default function StatCard({ value, label, className = "" }: StatCardProps) {
  return (
    <div className={`p-3 rounded-lg text-center flex-1 ${className}`}>
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  )
}
