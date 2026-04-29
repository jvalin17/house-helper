import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface Props {
  todayCost: number
  alltimeCost: number
  breakdown: Record<string, { tokens: number; cost: number }>
}

export default function BudgetCard({ todayCost, alltimeCost, breakdown }: Props) {
  return (
    <Card>
      <CardHeader><CardTitle className="text-lg">AI Usage</CardTitle></CardHeader>
      <CardContent>
        <div className="flex items-center gap-6 mb-4 p-3 rounded-lg bg-muted/50">
          <div>
            <span className="text-sm font-medium">Today</span>
            <div className="text-2xl font-bold">${todayCost.toFixed(4)}</div>
          </div>
          <div>
            <span className="text-sm font-medium">All Time</span>
            <div className="text-2xl font-bold">${alltimeCost.toFixed(4)}</div>
          </div>
        </div>
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
