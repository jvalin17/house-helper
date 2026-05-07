import { toast } from "sonner"
import { api } from "@/api/client"

interface Props {
  listingId: number
  costData: Record<string, number | string>
  setCostData: (updater: (previous: Record<string, number | string>) => Record<string, number | string>) => void
}

export default function CostCalculator({ listingId, costData, setCostData }: Props) {
  const baseRent = Number(costData.base_rent) || 0
  const parkingFee = Number(costData.parking_fee) || 0
  const petFee = Number(costData.pet_fee) || 0
  const utilitiesEstimate = Number(costData.utilities_estimate) || 0
  const leaseMonths = Number(costData.lease_months) || 12
  const specialDiscount = Number(costData.special_discount) || 0
  const effectiveRent = leaseMonths > 0 ? Math.round((baseRent * leaseMonths - specialDiscount) / leaseMonths) : baseRent
  const monthlyTotal = effectiveRent + parkingFee + petFee + utilitiesEstimate

  const handleSave = async () => {
    try {
      const costPayload = {
        base_rent: baseRent, parking_fee: parkingFee, pet_fee: petFee,
        utilities_estimate: utilitiesEstimate, lease_months: leaseMonths,
        special_discount: specialDiscount, special_description: costData.special_description || "",
      }
      const saved = await api.saveListingCost(listingId, costPayload)
      setCostData(() => saved as Record<string, number | string>)
      toast.success("Cost breakdown saved")
    } catch { toast.error("Failed to save") }
  }

  return (
    <div className="rounded-2xl bg-white border shadow-sm p-6 mb-6">
      <h3 className="text-sm font-medium text-purple-600 uppercase tracking-wider mb-4">Monthly Cost Calculator</h3>
      <div className="space-y-3">
        {/* Base rent */}
        <div className="flex items-center justify-between">
          <label className="text-xs text-gray-600">Base rent</label>
          {baseRent > 0 ? (
            <span className="text-sm font-medium text-gray-800">${baseRent.toLocaleString()}/mo</span>
          ) : (
            <div className="relative">
              <span className="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-gray-400">$</span>
              <input type="number" className="w-24 pl-5 pr-2 py-1.5 text-sm text-right border rounded-lg bg-white"
                placeholder="Enter rent" value={costData.base_rent || ""}
                onChange={(event) => setCostData(previous => ({ ...previous, base_rent: parseFloat(event.target.value) || 0 }))} />
            </div>
          )}
        </div>

        {/* Editable fees */}
        {[
          { key: "parking_fee", label: "Parking" },
          { key: "pet_fee", label: "Pet fee" },
          { key: "utilities_estimate", label: "Utilities (est.)" },
          { key: "deposit", label: "Deposit (one-time)" },
          { key: "application_fee", label: "App fee (one-time)" },
        ].map(({ key, label }) => (
          <div key={key} className="flex items-center justify-between">
            <label className="text-xs text-gray-600">{label}</label>
            <div className="relative">
              <span className="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-gray-400">$</span>
              <input type="number" className="w-24 pl-5 pr-2 py-1.5 text-sm text-right border rounded-lg bg-white"
                value={costData[key] || ""} placeholder="0"
                onChange={(event) => setCostData(previous => ({ ...previous, [key]: parseFloat(event.target.value) || 0 }))} />
            </div>
          </div>
        ))}

        {/* Concession */}
        <div className="pt-2 border-t border-gray-100">
          <p className="text-xs text-gray-600 mb-2">Move-in special</p>
          <div className="flex flex-wrap gap-1.5">
            {[
              { label: "None", months: 0 },
              { label: "1 month free", months: 1 },
              { label: "2 months free", months: 2 },
              { label: "3 months free", months: 3 },
              { label: "Half month", months: 0.5 },
            ].map(({ label, months }) => {
              const discountAmount = Math.round(baseRent * months)
              const isSelected = specialDiscount === discountAmount
              return (
                <button key={label}
                  onClick={() => setCostData(previous => ({
                    ...previous, special_discount: discountAmount,
                    special_description: months > 0 ? label : "",
                  }))}
                  className={`text-[11px] px-2.5 py-1 rounded-full transition-all border ${
                    isSelected ? "bg-purple-100 text-purple-700 border-purple-300" : "bg-gray-50 text-gray-500 border-gray-200 hover:border-purple-200"
                  }`}>{label}</button>
              )
            })}
          </div>
          <div className="flex items-center gap-2 mt-2">
            <span className="text-[11px] text-gray-400">Lease:</span>
            {[12, 14, 15, 18].map((months) => (
              <button key={months}
                onClick={() => setCostData(previous => ({ ...previous, lease_months: months }))}
                className={`text-[11px] px-2 py-0.5 rounded transition-all ${
                  leaseMonths === months ? "bg-purple-100 text-purple-700" : "text-gray-400 hover:text-purple-600"
                }`}>{months}mo</button>
            ))}
          </div>
        </div>

        {/* Effective rent */}
        {specialDiscount > 0 && (
          <div className="flex items-center justify-between text-xs">
            <span className="text-gray-500">Effective rent ({costData.special_description || "with discount"})</span>
            <span className="text-green-600 font-medium">${effectiveRent.toLocaleString()}/mo</span>
          </div>
        )}

        {/* Monthly total */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-200">
          <span className="text-sm font-semibold text-gray-800">Monthly total</span>
          <span className="text-lg font-bold text-purple-700">${monthlyTotal.toLocaleString()}/mo</span>
        </div>

        {/* Move-in total */}
        {(() => {
          const deposit = Number(costData.deposit) || 0
          const applicationFee = Number(costData.application_fee) || 0
          const moveInTotal = monthlyTotal + deposit + applicationFee
          return (deposit > 0 || applicationFee > 0) ? (
            <div className="flex items-center justify-between">
              <span className="text-xs text-gray-500">Move-in total</span>
              <span className="text-sm font-semibold text-gray-700">${moveInTotal.toLocaleString()}</span>
            </div>
          ) : null
        })()}

        {/* Save */}
        <button onClick={handleSave}
          className="text-xs text-purple-600 hover:text-purple-800 font-medium">
          Save cost breakdown
        </button>
      </div>
    </div>
  )
}
