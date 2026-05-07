interface Props {
  title: string
  address: string | null
  price: number | null
  bedrooms: number | null
  bathrooms: number | null
}

export default function KeyFactsBar({ title, address, price, bedrooms, bathrooms }: Props) {
  return (
    <div className="sticky top-0 z-10 bg-white/95 backdrop-blur-sm border-b py-3 -mx-6 px-6 mb-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">{title}</h2>
          {address && <p className="text-sm text-gray-400">{address}</p>}
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            {price != null && (
              <span className="text-2xl font-bold text-gray-800">
                ${price.toLocaleString()}
                <span className="text-sm text-gray-400 font-normal">/mo</span>
              </span>
            )}
          </div>
          <div className="flex items-center gap-3 text-sm text-gray-500">
            {bedrooms != null && <span>🛏 {bedrooms === 0 ? "Studio" : bedrooms}</span>}
            {bathrooms != null && <span>🚿 {bathrooms}</span>}
          </div>
        </div>
      </div>
    </div>
  )
}
