import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Skill } from "@/types"

interface Props {
  skills: Skill[]
  onDelete?: (skillId: number) => void
  onDeleteCategory?: (category: string) => void
}

export default function SkillsDisplay({ skills, onDelete, onDeleteCategory }: Props) {
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
                <div className="flex items-center justify-between mb-1">
                  <p className="text-sm font-medium capitalize">{category.replace(/_/g, " ")}</p>
                  {onDeleteCategory && (
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-xs text-muted-foreground hover:text-destructive h-6 px-2"
                      aria-label={`Delete all ${category}`}
                      onClick={() => onDeleteCategory(category)}
                    >
                      Delete all
                    </Button>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {categorySkills.map((skill) => (
                    <span
                      key={skill.id}
                      className="inline-flex items-center gap-0.5 rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors"
                    >
                      {skill.name}
                      {onDelete && (
                        <button
                          onClick={() => onDelete(skill.id)}
                          className="ml-1 rounded-full hover:bg-muted w-4 h-4 inline-flex items-center justify-center text-muted-foreground hover:text-destructive transition-colors"
                          aria-label={`Remove ${skill.name}`}
                        >
                          &times;
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
