import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { api } from "@/api/client"

interface Experience {
  id: number; title: string; company: string
  start_date: string; end_date: string; description: string
}

interface Skill {
  id: number; name: string; category: string
}

interface Education {
  id: number; institution: string; degree: string; field: string; end_date: string
}

interface Project {
  id: number; name: string; description: string; tech_stack: string; url: string
}

export default function KnowledgeBank() {
  const [experiences, setExperiences] = useState<Experience[]>([])
  const [skills, setSkills] = useState<Skill[]>([])
  const [education, setEducation] = useState<Education[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [freeText, setFreeText] = useState("")
  const [extractedSkills, setExtractedSkills] = useState<string[]>([])
  const [showExpForm, setShowExpForm] = useState(false)
  const [editingExp, setEditingExp] = useState<number | null>(null)
  const [form, setForm] = useState({ type: "job", title: "", company: "", start_date: "", end_date: "", description: "" })
  const [loading, setLoading] = useState(true)

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    try {
      const data = await api.listEntries() as {
        experiences: Experience[]; skills: Skill[]
        education: Education[]; projects: Project[]
      }
      // #region agent log
      ;(window as unknown as { __dbgLog?: (l: string, m: string, d?: Record<string, unknown>) => void }).__dbgLog?.(
        'KnowledgeBank.tsx:loadData',
        'listEntries response',
        {
          hypothesisId: 'CRASH-3',
          data_typeof: typeof data,
          data_is_array: Array.isArray(data),
          data_keys: data && typeof data === 'object' && !Array.isArray(data) ? Object.keys(data as object) : null,
          experiences_is_array: Array.isArray((data as { experiences?: unknown }).experiences),
          education_is_array: Array.isArray((data as { education?: unknown }).education),
          projects_is_array: Array.isArray((data as { projects?: unknown }).projects),
        }
      )
      // #endregion
      setExperiences(data.experiences || [])
      setEducation(data.education || [])
      setProjects(data.projects || [])
      const skillData = await api.listSkills() as Skill[]
      // #region agent log
      ;(window as unknown as { __dbgLog?: (l: string, m: string, d?: Record<string, unknown>) => void }).__dbgLog?.(
        'KnowledgeBank.tsx:loadData',
        'listSkills response',
        {
          hypothesisId: 'CRASH-3',
          skillData_typeof: typeof skillData,
          skillData_is_array: Array.isArray(skillData),
          skillData_keys: skillData && typeof skillData === 'object' && !Array.isArray(skillData) ? Object.keys(skillData as object) : null,
          length: Array.isArray(skillData) ? skillData.length : null,
        }
      )
      // #endregion
      setSkills(skillData)
    } catch (err) {
      // #region agent log
      ;(window as unknown as { __dbgLog?: (l: string, m: string, d?: Record<string, unknown>) => void }).__dbgLog?.(
        'KnowledgeBank.tsx:loadData',
        'loadData caught',
        { hypothesisId: 'CRASH-3', error: err instanceof Error ? err.message : String(err) }
      )
      // #endregion
    } finally { setLoading(false) }
  }

  const handleExtract = async () => {
    if (!freeText.trim()) return
    const result = await api.extractSkills(freeText) as { extracted_skills: string[] }
    setExtractedSkills(result.extracted_skills)
  }

  const handleSaveSkills = async () => {
    for (const skill of extractedSkills) {
      await api.createSkill({ name: skill, category: "extracted" })
    }
    setExtractedSkills([])
    setFreeText("")
    loadData()
  }

  const handleSaveExperience = async () => {
    if (editingExp) {
      await api.updateEntry(editingExp, form)
      setEditingExp(null)
    } else {
      await api.createEntry(form)
    }
    setForm({ type: "job", title: "", company: "", start_date: "", end_date: "", description: "" })
    setShowExpForm(false)
    loadData()
  }

  const startEdit = (exp: Experience) => {
    setForm({
      type: "job", title: exp.title, company: exp.company,
      start_date: exp.start_date || "", end_date: exp.end_date || "",
      description: exp.description || "",
    })
    setEditingExp(exp.id)
    setShowExpForm(true)
  }

  const handleDeleteExperience = async (id: number) => {
    await api.deleteEntry(id)
    loadData()
  }

  if (loading) return <p className="text-muted-foreground">Loading...</p>

  const isEmpty = experiences.length === 0 && skills.length === 0

  // Group skills by category
  const skillsByCategory: Record<string, Skill[]> = {}
  for (const skill of skills) {
    const cat = skill.category || "other"
    if (!skillsByCategory[cat]) skillsByCategory[cat] = []
    skillsByCategory[cat].push(skill)
  }

  return (
    <div className="space-y-6">
      {isEmpty && (
        <Card className="border-dashed">
          <CardContent className="py-10 text-center">
            <div className="text-4xl mb-3">&#128170;</div>
            <h3 className="font-semibold mb-2">Your superpowers are hidden!</h3>
            <p className="text-sm text-muted-foreground">
              Import your resume from the Jobs tab, or add experiences and skills below.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Add Knowledge */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Add Knowledge</CardTitle></CardHeader>
        <CardContent>
          <Textarea
            placeholder="Paste your experience here..."
            value={freeText} onChange={(e) => setFreeText(e.target.value)}
            rows={3} className="mb-3"
          />
          <Button onClick={handleExtract} disabled={!freeText.trim()}>Extract Skills</Button>
          {extractedSkills.length > 0 && (
            <div className="mt-4 p-4 bg-muted rounded-lg">
              <p className="text-sm font-medium mb-2">Found {extractedSkills.length} skills:</p>
              <div className="flex flex-wrap gap-2 mb-3">
                {extractedSkills.map((s) => <Badge key={s} variant="secondary">{s}</Badge>)}
              </div>
              <Button size="sm" onClick={handleSaveSkills}>Save to Knowledge Bank</Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Experiences */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-lg">Experiences ({experiences.length})</CardTitle>
          <Button variant="outline" size="sm" onClick={() => {
            setShowExpForm(!showExpForm); setEditingExp(null)
            setForm({ type: "job", title: "", company: "", start_date: "", end_date: "", description: "" })
          }}>
            {showExpForm ? "Cancel" : "+ Add"}
          </Button>
        </CardHeader>
        <CardContent>
          {showExpForm && (
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
              <Button onClick={handleSaveExperience} disabled={!form.title}>
                {editingExp ? "Update" : "Save"}
              </Button>
            </div>
          )}
          <div className="space-y-3">
            {experiences.map((exp) => (
              <div key={exp.id} className="flex items-start justify-between p-3 border rounded-lg">
                <div className="flex-1">
                  <div className="font-medium">{exp.title} — {exp.company}</div>
                  <div className="text-xs text-muted-foreground">{exp.start_date} — {exp.end_date || "Present"}</div>
                  {exp.description && <p className="text-sm mt-1 line-clamp-2">{exp.description}</p>}
                </div>
                <div className="flex gap-1">
                  <Button variant="ghost" size="sm" onClick={() => startEdit(exp)}>Edit</Button>
                  <Button variant="ghost" size="sm" onClick={() => handleDeleteExperience(exp.id)}>Delete</Button>
                </div>
              </div>
            ))}
            {experiences.length === 0 && !showExpForm && (
              <p className="text-muted-foreground text-sm">No experiences yet.</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Education */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Education ({education.length})</CardTitle></CardHeader>
        <CardContent>
          {education.length === 0 ? (
            <p className="text-muted-foreground text-sm">No education entries. Import your resume to populate.</p>
          ) : (
            <div className="space-y-2">
              {education.map((edu) => (
                <div key={edu.id} className="p-3 border rounded-lg">
                  <div className="font-medium">{edu.degree} {edu.field ? `in ${edu.field}` : ""}</div>
                  <div className="text-sm text-muted-foreground">{edu.institution}{edu.end_date ? ` (${edu.end_date})` : ""}</div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Projects */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Projects ({projects.length})</CardTitle></CardHeader>
        <CardContent>
          {projects.length === 0 ? (
            <p className="text-muted-foreground text-sm">No projects. Import your resume or add manually.</p>
          ) : (
            <div className="space-y-2">
              {projects.map((proj) => (
                <div key={proj.id} className="p-3 border rounded-lg">
                  <div className="font-medium">{proj.name}</div>
                  {proj.description && <p className="text-sm mt-1">{proj.description}</p>}
                  {proj.url && <a href={proj.url} className="text-sm text-primary">{proj.url}</a>}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Separator />

      {/* Skills by Category */}
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
    </div>
  )
}
