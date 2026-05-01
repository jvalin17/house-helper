import { useState } from "react"
import { Button } from "@/components/ui/button"

export const KNOWLEDGE_CATEGORIES = [
  { type: "job", label: "Experience" },
  { type: "project", label: "Project" },
  { type: "volunteering", label: "Volunteering" },
  { type: "education", label: "Education" },
  { type: "certification", label: "Certification" },
  { type: "other", label: "Other" },
] as const

interface Props {
  data: Record<string, string>
  onSave: (categoryType: string, data: Record<string, string>) => void
}

export default function CategorySaveButton({ data, onSave }: Props) {
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  const handleSelect = (categoryType: string) => {
    onSave(categoryType, data)
    setIsMenuOpen(false)
  }

  return (
    <div className="relative inline-block">
      <Button
        size="sm"
        variant="outline"
        onClick={() => setIsMenuOpen(!isMenuOpen)}
      >
        Save as...
      </Button>
      {isMenuOpen && (
        <div className="absolute left-0 mt-1 z-10 bg-white border rounded-lg shadow-lg py-1 min-w-[140px]">
          {KNOWLEDGE_CATEGORIES.map((category) => (
            <button
              key={category.type}
              className="w-full text-left px-3 py-1.5 text-sm hover:bg-muted transition-colors"
              onClick={() => handleSelect(category.type)}
            >
              {category.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
