import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Project } from "@/types"

interface Props {
  projects: Project[]
  onDelete: (id: number) => void
  onEdit?: (id: number, data: Record<string, string>) => void
}

export default function ProjectList({ projects, onDelete, onEdit }: Props) {
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editForm, setEditForm] = useState({ name: "", description: "", tech_stack: "", url: "" })

  const startEdit = (project: Project) => {
    setEditingId(project.id)
    setEditForm({
      name: project.name || "",
      description: project.description || "",
      tech_stack: project.tech_stack || "",
      url: project.url || "",
    })
  }

  const handleSave = () => {
    if (editingId && onEdit) {
      onEdit(editingId, editForm)
    }
    setEditingId(null)
  }

  const handleCancel = () => {
    setEditingId(null)
  }

  return (
    <Card>
      <CardHeader><CardTitle className="text-lg">Projects ({projects.length})</CardTitle></CardHeader>
      <CardContent>
        {projects.length === 0 ? (
          <p className="text-muted-foreground text-sm">No projects. Import your resume or add manually.</p>
        ) : (
          <div className="space-y-2">
            {projects.map((project) => (
              <div key={project.id} className="p-3 border rounded-lg">
                {editingId === project.id ? (
                  <div className="space-y-2">
                    <Input
                      value={editForm.name}
                      onChange={(event) => setEditForm({ ...editForm, name: event.target.value })}
                      placeholder="Project name"
                      aria-label="Project name"
                    />
                    <Textarea
                      value={editForm.description}
                      onChange={(event) => setEditForm({ ...editForm, description: event.target.value })}
                      placeholder="Description"
                      aria-label="Description"
                      rows={2}
                    />
                    <div className="grid grid-cols-2 gap-2">
                      <Input
                        value={editForm.tech_stack}
                        onChange={(event) => setEditForm({ ...editForm, tech_stack: event.target.value })}
                        placeholder="Tech stack"
                        aria-label="Tech stack"
                      />
                      <Input
                        value={editForm.url}
                        onChange={(event) => setEditForm({ ...editForm, url: event.target.value })}
                        placeholder="URL"
                        aria-label="URL"
                      />
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={handleSave}>Save</Button>
                      <Button size="sm" variant="ghost" onClick={handleCancel}>Cancel</Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="font-medium">{project.name}</div>
                      {project.description && <p className="text-sm mt-1">{project.description}</p>}
                      {project.tech_stack && <p className="text-xs text-muted-foreground mt-1">{project.tech_stack}</p>}
                      {project.url && /^https?:\/\//i.test(project.url) && (
                        <a href={project.url} target="_blank" rel="noreferrer" className="text-sm text-primary">{project.url}</a>
                      )}
                    </div>
                    <div className="flex gap-1">
                      {onEdit && <Button variant="ghost" size="sm" onClick={() => startEdit(project)}>Edit</Button>}
                      <Button variant="ghost" size="sm" onClick={() => onDelete(project.id)}>Delete</Button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
