import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Skill } from "@/types"

interface Props {
  skills: Skill[]
  onDelete?: (skillId: number) => void
  onDeleteCategory?: (category: string) => void
  onEdit?: (skillId: number, data: Record<string, string>) => void
}

export default function SkillsDisplay({ skills, onDelete, onDeleteCategory, onEdit }: Props) {
  const [editingSkillId, setEditingSkillId] = useState<number | null>(null)
  const [editName, setEditName] = useState("")
  const [editCategory, setEditCategory] = useState("")

  const skillsByCategory: Record<string, Skill[]> = {}
  for (const skill of skills) {
    const category = skill.category || "other"
    if (!skillsByCategory[category]) skillsByCategory[category] = []
    skillsByCategory[category].push(skill)
  }

  const startEdit = (skill: Skill) => {
    setEditingSkillId(skill.id)
    setEditName(skill.name)
    setEditCategory(skill.category)
  }

  const handleSaveEdit = () => {
    if (editingSkillId && onEdit) {
      onEdit(editingSkillId, { name: editName, category: editCategory })
    }
    setEditingSkillId(null)
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
                    <span key={skill.id}>
                      {editingSkillId === skill.id ? (
                        <span className="inline-flex items-center gap-1 rounded-md border border-blue-300 bg-blue-50/30 px-1.5 py-0.5">
                          <Input
                            value={editName}
                            onChange={(event) => setEditName(event.target.value)}
                            className="h-5 w-24 text-xs px-1"
                            aria-label="Skill name"
                            autoFocus
                          />
                          <Button size="sm" variant="ghost" className="h-5 px-1.5 text-xs" onClick={handleSaveEdit}>Save</Button>
                          <Button size="sm" variant="ghost" className="h-5 px-1 text-xs" onClick={() => setEditingSkillId(null)}>x</Button>
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-0.5 rounded-md border px-2.5 py-0.5 text-xs font-semibold transition-colors">
                          {skill.name}
                          {onEdit && (
                            <button
                              onClick={() => startEdit(skill)}
                              className="ml-0.5 text-muted-foreground hover:text-blue-600 transition-colors"
                              aria-label={`Edit ${skill.name}`}
                            >
                              &#9998;
                            </button>
                          )}
                          {onDelete && (
                            <button
                              onClick={() => onDelete(skill.id)}
                              className="ml-0.5 rounded-full hover:bg-muted w-4 h-4 inline-flex items-center justify-center text-muted-foreground hover:text-destructive transition-colors"
                              aria-label={`Remove ${skill.name}`}
                            >
                              &times;
                            </button>
                          )}
                        </span>
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
