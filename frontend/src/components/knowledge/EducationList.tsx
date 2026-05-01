import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Education } from "@/types"

interface Props {
  education: Education[]
  onDelete: (id: number) => void
  onEdit?: (id: number, data: Record<string, string>) => void
}

export default function EducationList({ education, onDelete, onEdit }: Props) {
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editForm, setEditForm] = useState({ institution: "", degree: "", field: "", end_date: "" })

  const startEdit = (entry: Education) => {
    setEditingId(entry.id)
    setEditForm({
      institution: entry.institution || "",
      degree: entry.degree || "",
      field: entry.field || "",
      end_date: entry.end_date || "",
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
      <CardHeader><CardTitle className="text-lg">Education ({education.length})</CardTitle></CardHeader>
      <CardContent>
        {education.length === 0 ? (
          <p className="text-muted-foreground text-sm">No education entries. Import your resume to populate.</p>
        ) : (
          <div className="space-y-2">
            {education.map((entry) => (
              <div key={entry.id} className="p-3 border rounded-lg">
                {editingId === entry.id ? (
                  <div className="space-y-2">
                    <Input
                      value={editForm.institution}
                      onChange={(event) => setEditForm({ ...editForm, institution: event.target.value })}
                      placeholder="Institution"
                      aria-label="Institution"
                    />
                    <div className="grid grid-cols-3 gap-2">
                      <Input
                        value={editForm.degree}
                        onChange={(event) => setEditForm({ ...editForm, degree: event.target.value })}
                        placeholder="Degree"
                        aria-label="Degree"
                      />
                      <Input
                        value={editForm.field}
                        onChange={(event) => setEditForm({ ...editForm, field: event.target.value })}
                        placeholder="Field of study"
                        aria-label="Field"
                      />
                      <Input
                        value={editForm.end_date}
                        onChange={(event) => setEditForm({ ...editForm, end_date: event.target.value })}
                        placeholder="Year"
                        aria-label="End date"
                      />
                    </div>
                    <div className="flex gap-2">
                      <Button size="sm" onClick={handleSave}>Save</Button>
                      <Button size="sm" variant="ghost" onClick={handleCancel}>Cancel</Button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-medium">{entry.degree} {entry.field ? `in ${entry.field}` : ""}</div>
                      <div className="text-sm text-muted-foreground">
                        {entry.institution}{entry.end_date ? ` (${entry.end_date})` : ""}
                      </div>
                    </div>
                    <div className="flex gap-1">
                      {onEdit && <Button variant="ghost" size="sm" onClick={() => startEdit(entry)}>Edit</Button>}
                      <Button variant="ghost" size="sm" onClick={() => onDelete(entry.id)}>Delete</Button>
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
