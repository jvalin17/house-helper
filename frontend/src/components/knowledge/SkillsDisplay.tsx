import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Skill } from "@/types"

interface Props {
  skills: Skill[]
}

export default function SkillsDisplay({ skills }: Props) {
  const skillsByCategory: Record<string, Skill[]> = {}
  for (const skill of skills) {
    const cat = skill.category || "other"
    if (!skillsByCategory[cat]) skillsByCategory[cat] = []
    skillsByCategory[cat].push(skill)
  }

  return (
    <Card>
      <CardHeader><CardTitle className="text-lg">Skills ({skills.length})</CardTitle></CardHeader>
      <CardContent>
        {skills.length === 0 ? (
          <p className="text-muted-foreground text-sm">No skills yet.</p>
        ) : (
          <div className="space-y-3">
            {Object.entries(skillsByCategory).map(([category, categorySkills]) => (
              <div key={category}>
                <p className="text-sm font-medium mb-1 capitalize">{category.replace(/_/g, " ")}</p>
                <div className="flex flex-wrap gap-2">
                  {categorySkills.map((skill) => (
                    <Badge key={skill.id} variant="outline">{skill.name}</Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
