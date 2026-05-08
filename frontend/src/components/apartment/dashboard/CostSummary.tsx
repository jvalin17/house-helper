/**
 * CostSummary — compact cost breakdown display for a listing.
 *
 * Shows base rent, fees, effective monthly (highlighted), and any concession savings.
 * Fetches cost data from the API on mount.
 */

import { useEffect, useState } from "react"
import { api } from "@/api/client"

interface CostSummaryProps {
  listingId: number
}

interface CostData {
  base_rent: number | null
  effective_monthly: number | null
  fees: Array<{ label: string; amount: number }> | null
  concession_monthly_savings: number | null
  total_fees_monthly: number | null
}

export default function CostSummary({ listingId }: CostSummaryProps) {
  const [costData, setCostData] = useState<CostData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function loadCostData() {
      try {
        const response = await api.getListingCost(listingId)
        if (!cancelled) {
          setCostData(response as unknown as CostData)
        }
      } catch {
        // No cost data available
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    loadCostData()
    return () => { cancelled = true }
  }, [listingId])

  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="h-16 rounded-lg bg-gray-100" />
      </div>
    )
  }

  if (!costData || (costData.base_rent == null && costData.effective_monthly == null)) {
    return (
      <div className="px-3 py-3 rounded-lg bg-gray-50 border border-gray-100">
        <p className="text-xs text-gray-400 text-center">No cost data yet</p>
      </div>
    )
  }

  const feesList = costData.fees ?? []
  const hasConcession = costData.concession_monthly_savings != null && costData.concession_monthly_savings > 0

  return (
    <div>
      <label className="text-xs font-medium text-gray-500 mb-1.5 block">Cost Breakdown</label>
      <div className="rounded-lg border border-gray-200 bg-white overflow-hidden">
        {/* Base rent */}
        {costData.base_rent != null && (
          <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100">
            <span className="text-xs text-gray-500">Base Rent</span>
            <span className="text-xs font-mono text-gray-700">${costData.base_rent.toLocaleString()}/mo</span>
          </div>
        )}

        {/* Fee lines */}
        {feesList.map((feeItem, feeIndex) => (
          <div key={feeIndex} className="flex items-center justify-between px-3 py-1.5 border-b border-gray-50">
            <span className="text-[11px] text-gray-400">{feeItem.label}</span>
            <span className="text-[11px] font-mono text-gray-500">${feeItem.amount.toLocaleString()}</span>
          </div>
        ))}

        {/* Concession savings */}
        {hasConcession && (
          <div className="flex items-center justify-between px-3 py-1.5 border-b border-emerald-50 bg-emerald-50/50">
            <span className="text-[11px] text-emerald-600">Concession Savings</span>
            <span className="text-[11px] font-mono text-emerald-600 font-medium">
              -${costData.concession_monthly_savings!.toLocaleString()}/mo
            </span>
          </div>
        )}

        {/* Effective monthly — highlighted */}
        {costData.effective_monthly != null && (
          <div className="flex items-center justify-between px-3 py-2.5 bg-indigo-50/50">
            <span className="text-xs font-semibold text-indigo-700">Effective Monthly</span>
            <span className="text-sm font-bold font-mono text-indigo-700">
              ${Math.round(costData.effective_monthly).toLocaleString()}/mo
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
