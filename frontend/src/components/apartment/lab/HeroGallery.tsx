interface Props {
  images: string[]
  onPhotoClick: (index: number) => void
}

export default function HeroGallery({ images, onPhotoClick }: Props) {
  if (images.length === 0) return null

  return (
    <div className="relative -mx-6 mb-6">
      <div className="flex gap-1 overflow-x-auto pb-2">
        {images.slice(0, 8).map((imageUrl, imageIndex) => (
          <img
            key={imageIndex}
            src={imageUrl}
            alt={`Photo ${imageIndex + 1}`}
            className="h-64 rounded-lg object-cover flex-shrink-0 cursor-pointer hover:opacity-90 transition-opacity"
            loading="lazy"
            onClick={() => onPhotoClick(imageIndex)}
          />
        ))}
      </div>
      {images.length > 8 && (
        <button
          onClick={() => onPhotoClick(0)}
          className="absolute bottom-4 right-2 bg-black/60 text-white text-xs px-3 py-1.5 rounded-full hover:bg-black/80 transition-colors cursor-pointer"
        >
          📷 View all {images.length} photos
        </button>
      )}
    </div>
  )
}
