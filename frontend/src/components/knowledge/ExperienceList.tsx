import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import type { Experience } from "@/types"

interface Props {
  experiences: Experience[]
  onSave: (form: Record<string, string>) => void
  onEdit: (exp: Experience) => void
  onDelete: (id: number) => void
}

export default function ExperienceList({ experiences, onSave, onEdit, onDelete }: Props) {
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [expandedId, setExpandedId] = useState<number | null>(null)
  const [form, setForm] = useState({ type: "job", title: "", company: "", start_date: "", end_date: "", description: "" })

  const handleSave = () => {
    onSave(form)
    setForm({ type: "job", title: "", company: "", start_date: "", end_date: "", description: "" })
    setShowForm(false)
    setEditingId(null)
  }

  const startEdit = (exp: Experience) => {
    setForm({
      type: "job", title: exp.title, company: exp.company,
      start_date: exp.start_date || "", end_date: exp.end_date || "",
      description: exp.description || "",
    })
    setEditingId(exp.id)
    setShowForm(true)
    onEdit(exp)
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-lg">Experiences ({experiences.length})</CardTitle>
        <Button variant="outline" size="sm" onClick={() => {
          setShowForm(!showForm); setEditingId(null)
          setForm({ type: "job", title: "", company: "", start_date: "", end_date: "", description: "" })
        }}>
          {showForm ? "Cancel" : "+ Add"}
        </Button>
      </CardHeader>
      <CardContent>
        {showForm && (
          <div className="grid grid-cols-2 gap-3 mb-4 p-4 bg-muted rounded-lg">
            <Input placeholder="Job Title" value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })} />
            <Input placeholder="Company" value={form.company}
              onChange={(e) => setForm({ ...form, company: e.target.value })} />
            <Input placeholder="Start (2020-01)" value={form.start_date}
              onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
            <Input placeholder="End (or empty)" value={form.end_date}
              onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
            <div className="col-span-2">
              <Textarea placeholder="What did you do?" value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} />
            </div>
            <Button onClick={handleSave} disabled={!form.title}>
              {editingId ? "Update" : "Save"}
            </Button>
          </div>
        )}
        <div className="space-y-3">
          {experiences.map((exp) => {
            const isExpanded = expandedId === exp.id
            const bullets = (exp.description || "").split("\n").filter(Boolean)
            return (
              <div key={exp.id} className="p-3 border rounded-lg">
                <div className="flex items-start justify-between">
                  <div className="flex-1 cursor-pointer" onClick={() => setExpandedId(isExpanded ? null : exp.id)}>
                    <div className="font-medium">{exp.title} — {exp.company}</div>
                    <div className="text-xs text-muted-foreground">
                      {exp.start_date} — {exp.end_date || "Present"}
                      {bullets.length > 0 && <span className="ml-2">{bullets.length} bullet{bullets.length !== 1 ? "s" : ""}</span>}
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="sm" onClick={() => startEdit(exp)}>Edit</Button>
                    <Button variant="ghost" size="sm" onClick={() => onDelete(exp.id)}>Delete</Button>
                  </div>
                </div>
                {isExpanded && bullets.length > 0 && (
                  <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                    {bullets.map((b, i) => (
                      <li key={i} className="flex gap-2">
                        <span className="shrink-0">-</span>
                        <span>{b.replace(/^[-•]\s*/, "")}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )
          })}
          {experiences.length === 0 && !showForm && (
            <p className="text-muted-foreground text-sm">No experiences yet.</p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
