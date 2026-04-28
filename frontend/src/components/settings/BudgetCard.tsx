import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"

interface Props {
  budgetLimit: string
  totalCost: number
  onBudgetChange: (v: string) => void
  onSave: () => void
  message: string
}

export default function BudgetCard({ budgetLimit, totalCost, onBudgetChange, onSave, message }: Props) {
  const parsedLimit = parseFloat(budgetLimit)
  const hasValidLimit = budgetLimit && !isNaN(parsedLimit)

  return (
    <Card>
      <CardHeader><CardTitle className="text-lg">Usage Limit</CardTitle></CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-3">
          Set a daily spending limit. The app will pause AI features when the limit is reached.
        </p>
        <div className="flex items-center gap-4 mb-4 p-3 rounded-lg bg-muted/50">
          <div>
            <span className="text-sm font-medium">Today</span>
            <div className="text-2xl font-bold">${totalCost.toFixed(4)}</div>
          </div>
          {hasValidLimit && (
            <>
              <div className="text-muted-foreground">/</div>
              <div>
                <span className="text-sm font-medium">Limit</span>
                <div className="text-2xl font-bold">${parsedLimit.toFixed(2)}</div>
              </div>
            </>
          )}
        </div>
        <div className="flex gap-2 items-end">
          <div className="flex-1">
            <p className="text-sm font-medium mb-1">Daily limit ($)</p>
            <Input placeholder="e.g., 1.00 (leave empty for no limit)"
              value={budgetLimit} onChange={(e) => onBudgetChange(e.target.value)} />
          </div>
          <Button onClick={onSave}>Set Limit</Button>
        </div>
        {message && <p className="text-sm text-muted-foreground mt-2">{message}</p>}
        <p className="text-xs text-muted-foreground mt-2">
          {hasValidLimit ? `At ~$0.006/resume, that's ~${Math.floor(parsedLimit / 0.006)} resumes per day` : "No limit set"}
        </p>
      </CardContent>
    </Card>
  )
}
