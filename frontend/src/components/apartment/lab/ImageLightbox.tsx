import { useState } from "react"

interface Props {
  images: string[]
  initialIndex: number
  onClose: () => void
}

export default function ImageLightbox({ images, initialIndex, onClose }: Props) {
  const [currentIndex, setCurrentIndex] = useState(initialIndex)

  if (images.length === 0) return null

  return (
    <div className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center"
      onClick={onClose}>
      {/* Close */}
      <button onClick={onClose}
        className="absolute top-4 right-4 text-white/70 hover:text-white text-2xl z-10 w-10 h-10 flex items-center justify-center">
        ✕
      </button>

      {/* Counter */}
      <div className="absolute top-4 left-4 text-white/70 text-sm">
        {currentIndex + 1} / {images.length}
      </div>

      {/* Previous */}
      {currentIndex > 0 && (
        <button
          onClick={(event) => { event.stopPropagation(); setCurrentIndex(currentIndex - 1) }}
          className="absolute left-4 top-1/2 -translate-y-1/2 text-white/70 hover:text-white text-3xl w-12 h-12 flex items-center justify-center rounded-full bg-black/30 hover:bg-black/50">
          ‹
        </button>
      )}

      {/* Image */}
      <img src={images[currentIndex]} alt={`Photo ${currentIndex + 1}`}
        className="max-h-[85vh] max-w-[90vw] object-contain rounded-lg"
        onClick={(event) => event.stopPropagation()} />

      {/* Next */}
      {currentIndex < images.length - 1 && (
        <button
          onClick={(event) => { event.stopPropagation(); setCurrentIndex(currentIndex + 1) }}
          className="absolute right-4 top-1/2 -translate-y-1/2 text-white/70 hover:text-white text-3xl w-12 h-12 flex items-center justify-center rounded-full bg-black/30 hover:bg-black/50">
          ›
        </button>
      )}

      {/* Thumbnail strip */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-1 max-w-[80vw] overflow-x-auto px-2">
        {images.map((thumbnailUrl, thumbnailIndex) => (
          <img key={thumbnailIndex} src={thumbnailUrl} alt={`Thumb ${thumbnailIndex + 1}`}
            className={`h-12 w-16 object-cover rounded cursor-pointer flex-shrink-0 transition-all ${
              thumbnailIndex === currentIndex ? "ring-2 ring-white opacity-100" : "opacity-50 hover:opacity-75"
            }`}
            onClick={(event) => { event.stopPropagation(); setCurrentIndex(thumbnailIndex) }} />
        ))}
      </div>
    </div>
  )
}
