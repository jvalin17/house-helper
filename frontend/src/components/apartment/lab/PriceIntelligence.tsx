interface PriceContext {
  listing_price: number
  area_median: number | null
  percentile: number | null
  comparable_count: number
  price_vs_median: number | null
}

interface Props {
  priceContext: PriceContext
}

export default function PriceIntelligence({ priceContext }: Props) {
  if (priceContext.area_median == null) return null

  return (
    <div className="rounded-2xl bg-white border shadow-sm p-6 mb-6">
      <h3 className="text-sm font-medium text-purple-600 uppercase tracking-wider mb-4">Price Intelligence</h3>
      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="bg-gray-50 rounded-xl p-3 text-center">
          <p className="text-[10px] text-gray-400 uppercase">This listing</p>
          <p className="text-lg font-bold text-gray-800">${priceContext.listing_price.toLocaleString()}</p>
        </div>
        <div className="bg-gray-50 rounded-xl p-3 text-center">
          <p className="text-[10px] text-gray-400 uppercase">Area median</p>
          <p className="text-lg font-bold text-gray-800">${priceContext.area_median.toLocaleString()}</p>
        </div>
        <div className="bg-gray-50 rounded-xl p-3 text-center">
          <p className="text-[10px] text-gray-400 uppercase">Percentile</p>
          <p className="text-lg font-bold text-gray-800">{priceContext.percentile}th</p>
          <p className="text-[10px] text-gray-400">{priceContext.comparable_count} comparables</p>
        </div>
      </div>
      {/* Price bar */}
      <div className="relative h-3 bg-gray-100 rounded-full overflow-hidden mb-2">
        <div className="absolute h-full bg-purple-200 rounded-full"
          style={{ width: `${Math.min(priceContext.percentile || 0, 100)}%` }} />
        <div className="absolute h-full w-1 bg-purple-600 rounded-full"
          style={{ left: `${Math.min(priceContext.percentile || 0, 100)}%` }} />
      </div>
      <div className="flex justify-between text-[10px] text-gray-400">
        <span>Cheapest</span>
        <span>{(priceContext.price_vs_median || 0) < 0
          ? `$${Math.abs(priceContext.price_vs_median || 0).toLocaleString()} below median`
          : (priceContext.price_vs_median || 0) > 0
            ? `$${(priceContext.price_vs_median || 0).toLocaleString()} above median`
            : "At median"
        }</span>
        <span>Most expensive</span>
      </div>
    </div>
  )
}
