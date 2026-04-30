import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"

interface Props {
  onGenerate: (preferences: Record<string, unknown>) => void
  loading: boolean
}

const LENGTHS = ["1 page", "2 pages", "No limit"]
const TONES = ["Professional", "Conversational", "Technical"]
const EMPHASES = ["Technical depth", "Leadership", "IC contributions", "Balanced"]
const SECTIONS = [
  { id: "summary", label: "Summary" },
  { id: "experience", label: "Experience" },
  { id: "skills", label: "Skills" },
  { id: "education", label: "Education" },
  { id: "projects", label: "Projects" },
  { id: "achievements", label: "Achievements" },
]

export default function GenerationPrefs({ onGenerate, loading }: Props) {
  const [length, setLength] = useState("1 page")
  const [tone, setTone] = useState("Professional")
  const [emphasis, setEmphasis] = useState("Balanced")
  const [sections, setSections] = useState(SECTIONS.map((section) => section.id))

  const toggleSection = (id: string) => {
    setSections((prev) =>
      prev.includes(id) ? prev.filter((sectionId) => sectionId !== id) : [...prev, id]
    )
  }

  const handleGenerate = () => {
    onGenerate({ length, tone, emphasis, sections })
  }

  return (
    <Card className="mb-4">
      <CardHeader>
        <CardTitle className="text-base">Resume Preferences</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Length */}
        <div>
          <p className="text-sm font-medium mb-2">Length</p>
          <div className="flex gap-2">
            {LENGTHS.map((lengthOption) => (
              <Badge
                key={lengthOption}
                variant={length === lengthOption ? "default" : "outline"}
                className="cursor-pointer"
                onClick={() => setLength(lengthOption)}
              >
                {lengthOption}
              </Badge>
            ))}
          </div>
        </div>

        {/* Tone */}
        <div>
          <p className="text-sm font-medium mb-2">Tone</p>
          <div className="flex gap-2">
            {TONES.map((toneOption) => (
              <Badge
                key={toneOption}
                variant={tone === toneOption ? "default" : "outline"}
                className="cursor-pointer"
                onClick={() => setTone(toneOption)}
              >
                {toneOption}
              </Badge>
            ))}
          </div>
        </div>

        {/* Emphasis */}
        <div>
          <p className="text-sm font-medium mb-2">Emphasis</p>
          <div className="flex gap-2 flex-wrap">
            {EMPHASES.map((e) => (
              <Badge
                key={e}
                variant={emphasis === e ? "default" : "outline"}
                className="cursor-pointer"
                onClick={() => setEmphasis(e)}
              >
                {e}
              </Badge>
            ))}
          </div>
        </div>

        {/* Sections */}
        <div>
          <p className="text-sm font-medium mb-2">Include Sections</p>
          <div className="flex gap-2 flex-wrap">
            {SECTIONS.map((section) => (
              <Badge
                key={section.id}
                variant={sections.includes(section.id) ? "default" : "outline"}
                className="cursor-pointer"
                onClick={() => toggleSection(section.id)}
              >
                {section.label}
              </Badge>
            ))}
          </div>
        </div>

        <Button onClick={handleGenerate} disabled={loading} className="w-full">
          {loading ? "Generating..." : "Generate Resume & Cover Letter"}
        </Button>
      </CardContent>
    </Card>
  )
}
