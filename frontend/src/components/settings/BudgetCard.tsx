import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { api } from "@/api/client"
import { toast } from "sonner"

interface Props {
  todayCost: number
  alltimeCost: number
  breakdown: Record<string, { tokens: number; cost: number }>
  dailyLimit: number | null
  onLimitSaved: () => void
}

export default function BudgetCard({ todayCost, alltimeCost, breakdown, dailyLimit, onLimitSaved }: Props) {
  const [editing, setEditing] = useState(false)
  const [limit, setLimit] = useState(dailyLimit?.toString() || "")

  const handleSave = async () => {
    try {
      const value = limit ? parseFloat(limit) : null
      await api.saveBudget({ daily_limit_cost: value })
      toast.success(value ? `Daily limit set to $${value.toFixed(2)}` : "Daily limit removed")
      setEditing(false)
      onLimitSaved()
    } catch {
      toast.error("Failed to save limit")
    }
  }

  return (
    <Card>
      <CardHeader><CardTitle className="text-lg">AI Usage</CardTitle></CardHeader>
      <CardContent>
        <div className="flex items-center gap-6 mb-4 p-3 rounded-lg bg-muted/50">
          <div>
            <span className="text-sm font-medium">Today</span>
            <div className="text-2xl font-bold">${(todayCost ?? 0).toFixed(4)}</div>
          </div>
          <div>
            <span className="text-sm font-medium">All Time</span>
            <div className="text-2xl font-bold">${(alltimeCost ?? 0).toFixed(4)}</div>
          </div>
          <div className="ml-auto">
            <span className="text-sm font-medium">Daily Limit</span>
            {editing ? (
              <div className="flex items-center gap-1 mt-1">
                <span className="text-sm">$</span>
                <Input
                  type="number" step="0.10" min="0" placeholder="No limit"
                  value={limit} onChange={e => setLimit(e.target.value)}
                  className="w-20 h-7 text-sm"
                />
                <Button size="sm" variant="outline" className="h-7 text-xs" onClick={handleSave}>Save</Button>
                <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setEditing(false)}>Cancel</Button>
              </div>
            ) : (
              <div className="text-2xl font-bold cursor-pointer hover:text-purple-600 transition-colors" onClick={() => { setEditing(true); setLimit(dailyLimit?.toString() || "") }}>
                {dailyLimit ? `$${dailyLimit.toFixed(2)}` : "None"}
              </div>
            )}
          </div>
        </div>
        {dailyLimit && todayCost >= dailyLimit && (
          <div className="mb-3 p-2 rounded bg-orange-50 text-orange-700 text-xs font-medium">
            Daily limit reached. AI features paused until tomorrow.
          </div>
        )}
        {Object.keys(breakdown).length > 0 && (
          <div className="space-y-1 text-sm">
            <p className="font-medium text-xs text-muted-foreground mb-1">Today by feature:</p>
            {Object.entries(breakdown).map(([feature, data]) => (
              <div key={feature} className="flex justify-between">
                <span className="text-muted-foreground">{feature.replace(/_/g, " ")}</span>
                <span>${data.cost.toFixed(4)} ({data.tokens} tokens)</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
