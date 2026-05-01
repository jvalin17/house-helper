import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Skill } from "@/types"

interface Props {
  skills: Skill[]
  onDelete?: (skillId: number) => void
}

export default function SkillsDisplay({ skills, onDelete }: Props) {
  const skillsByCategory: Record<string, Skill[]> = {}
  for (const skill of skills) {
    const category = skill.category || "other"
    if (!skillsByCategory[category]) skillsByCategory[category] = []
    skillsByCategory[category].push(skill)
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
                    <span key={skill.id} className="inline-flex items-center gap-1">
                      <Badge variant="outline">{skill.name}</Badge>
                      {onDelete && (
                        <button
                          onClick={() => onDelete(skill.id)}
                          className="text-muted-foreground hover:text-destructive text-xs leading-none"
                          aria-label={`Delete ${skill.name}`}
                        >
                          x
                        </button>
                      )}
                    </span>
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
