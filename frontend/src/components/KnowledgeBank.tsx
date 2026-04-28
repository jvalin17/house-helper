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
  const [acceptedSkills, setAcceptedSkills] = useState<Set<string>>(new Set())
  const [showExpForm, setShowExpForm] = useState(false)
  const [editingExp, setEditingExp] = useState<number | null>(null)
  const [form, setForm] = useState({ type: "job", title: "", company: "", start_date: "", end_date: "", description: "" })
  const [loading, setLoading] = useState(true)
  const [expandedExp, setExpandedExp] = useState<number | null>(null)
  const [linkInput, setLinkInput] = useState("")
  const [linkLoading, setLinkLoading] = useState(false)
  const [linkPreview, setLinkPreview] = useState<{ skills: string[]; description: string } | null>(null)
  const [storedResume, setStoredResume] = useState<Record<string, unknown> | null>(null)
  const [showResume, setShowResume] = useState(false)

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    try {
      const data = await api.listEntries() as Record<string, unknown>
      setExperiences(Array.isArray(data?.experiences) ? data.experiences as Experience[] : [])
      setEducation(Array.isArray(data?.education) ? data.education as Education[] : [])
      setProjects(Array.isArray(data?.projects) ? data.projects as Project[] : [])
      const skillData = await api.listSkills()
      setSkills(Array.isArray(skillData) ? skillData as Skill[] : [])
      try {
        const resume = await api.getStoredResume()
        setStoredResume(resume)
      } catch { /* no resume stored yet */ }
    } catch { /* silent */ } finally { setLoading(false) }
  }

  const handleExtract = async () => {
    const text = freeText.trim() || linkInput.trim()
    if (!text) return
    try {
      const result = await api.extractSkills(text) as { extracted_skills: string[] }
      const skills = Array.isArray(result.extracted_skills) ? result.extracted_skills : []
      setExtractedSkills(skills)
      setAcceptedSkills(new Set(skills))  // all accepted by default
    } catch { /* silent */ }
  }

  const handleFetchLink = async () => {
    if (!linkInput.trim()) return
    setLinkLoading(true)
    setLinkPreview(null)
    try {
      const result = await api.extractSkills(linkInput.trim()) as {
        extracted_skills: string[]; raw_text: string; source: string
      }
      const skills = Array.isArray(result.extracted_skills) ? result.extracted_skills : []
      setExtractedSkills(skills)
      setAcceptedSkills(new Set(skills))
      const preview = result.raw_text || ""
      setLinkPreview({ skills, description: preview.slice(0, 500) })
      // Also put the extracted text into freeText so user can review
      if (result.source === "url" && result.raw_text) {
        setFreeText(result.raw_text.slice(0, 2000))
      }
    } catch (err) {
      setLinkPreview({ skills: [], description: err instanceof Error ? err.message : "Failed to fetch" })
    } finally { setLinkLoading(false) }
  }

  const handleSaveSkills = async () => {
    try {
      const toSave = extractedSkills.filter((s) => acceptedSkills.has(s))
      for (const skill of toSave) {
        await api.createSkill({ name: skill, category: "extracted" })
      }
      setExtractedSkills([])
      setAcceptedSkills(new Set())
      setFreeText("")
      setLinkInput("")
      setLinkPreview(null)
      loadData()
    } catch { /* silent */ }
  }

  const toggleSkill = (skill: string) => {
    setAcceptedSkills((prev) => {
      const next = new Set(prev)
      if (next.has(skill)) next.delete(skill); else next.add(skill)
      return next
    })
  }

  const handleSaveExperience = async () => {
    try {
      if (editingExp) {
        await api.updateEntry(editingExp, form)
        setEditingExp(null)
      } else {
        await api.createEntry(form)
      }
      setForm({ type: "job", title: "", company: "", start_date: "", end_date: "", description: "" })
      setShowExpForm(false)
      loadData()
    } catch { /* silent */ }
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
    try {
      await api.deleteEntry(id)
      loadData()
    } catch { /* silent */ }
  }

  const handleDeleteEducation = async (id: number) => {
    try {
      await api.deleteEducation(id)
      loadData()
    } catch { /* silent */ }
  }

  const handleDeleteProject = async (id: number) => {
    try {
      await api.deleteProject(id)
      loadData()
    } catch { /* silent */ }
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
        <CardContent className="space-y-3">
          <div>
            <Input
              placeholder="Paste a link (GitHub, LinkedIn, portfolio, etc.)"
              value={linkInput} onChange={(e) => setLinkInput(e.target.value)}
              className="mb-2"
            />
            <Button size="sm" onClick={handleFetchLink}
              disabled={!linkInput.trim() || linkLoading}>
              {linkLoading ? "Extracting..." : "Extract from Link"}
            </Button>
          </div>

          <div className="flex items-center gap-3">
            <Separator className="flex-1" />
            <span className="text-xs text-muted-foreground">or paste text</span>
            <Separator className="flex-1" />
          </div>

          <div>
            <Textarea
              placeholder="Paste your experience, project description, or any relevant text..."
              value={freeText} onChange={(e) => setFreeText(e.target.value)}
              rows={3}
            />
            <Button size="sm" className="mt-2" onClick={handleExtract}
              disabled={!freeText.trim()}>
              Extract Skills from Text
            </Button>
          </div>

          {linkPreview && linkPreview.skills.length === 0 && linkPreview.description && (
            <div className="p-3 rounded-lg bg-destructive/10 border border-destructive/20">
              <p className="text-sm text-destructive">{linkPreview.description}</p>
            </div>
          )}

          {linkPreview && linkPreview.description && linkPreview.skills.length > 0 && (
            <div className="p-3 rounded-lg bg-muted text-sm max-h-32 overflow-auto">
              <p className="text-xs text-muted-foreground mb-1">Extracted content preview:</p>
              <p className="whitespace-pre-wrap">{linkPreview.description}</p>
            </div>
          )}

          {extractedSkills.length > 0 && (
            <div className="p-4 bg-muted rounded-lg">
              <p className="text-sm font-medium mb-2">
                Found {extractedSkills.length} skills — click to accept or deny:
              </p>
              <div className="flex flex-wrap gap-2 mb-3">
                {extractedSkills.map((s) => (
                  <Badge key={s}
                    variant={acceptedSkills.has(s) ? "default" : "outline"}
                    className={`cursor-pointer transition-opacity ${acceptedSkills.has(s) ? "" : "opacity-40 line-through"}`}
                    onClick={() => toggleSkill(s)}>
                    {s}
                  </Badge>
                ))}
              </div>
              <div className="flex items-center gap-3">
                <Button size="sm" onClick={handleSaveSkills} disabled={acceptedSkills.size === 0}>
                  Save {acceptedSkills.size} Skill{acceptedSkills.size !== 1 ? "s" : ""}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => {
                  setExtractedSkills([]); setAcceptedSkills(new Set()); setLinkPreview(null)
                }}>
                  Dismiss All
                </Button>
                <span className="text-xs text-muted-foreground">
                  {acceptedSkills.size}/{extractedSkills.length} selected
                </span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Stored Resume */}
      {storedResume?.has_resume ? (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="text-lg">Uploaded Resume</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => setShowResume(!showResume)}>
              {showResume ? "Hide" : "View"}
            </Button>
          </CardHeader>
          {showResume && (
            <CardContent>
              {storedResume.structure ? (() => {
                const structure = storedResume.structure as { total_paragraphs: number; roles: Array<{ company: string; title: string; bullets: number }> }
                return (
                  <div className="mb-3 p-3 rounded-lg bg-blue-50/50 border border-blue-100 text-sm">
                    <p className="font-medium mb-1">{structure.total_paragraphs} paragraphs mapped{storedResume.has_docx ? " (DOCX format preserved)" : ""}</p>
                    {structure.roles.map((r, i) => (
                      <p key={i} className="text-muted-foreground">{r.company} | {r.title} — {r.bullets} bullets</p>
                    ))}
                  </div>
                )
              })() : null}
              <pre className="bg-muted p-4 rounded-lg text-sm whitespace-pre-wrap font-mono max-h-64 overflow-auto">
                {String(storedResume.text || "No text stored")}
              </pre>
            </CardContent>
          )}
        </Card>
      ) : null}

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
            {experiences.map((exp) => {
              const isExpanded = expandedExp === exp.id
              const bullets = (exp.description || "").split("\n").filter(Boolean)
              return (
                <div key={exp.id} className="p-3 border rounded-lg">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 cursor-pointer" onClick={() => setExpandedExp(isExpanded ? null : exp.id)}>
                      <div className="font-medium">{exp.title} — {exp.company}</div>
                      <div className="text-xs text-muted-foreground">
                        {exp.start_date} — {exp.end_date || "Present"}
                        {bullets.length > 0 && <span className="ml-2">{bullets.length} bullet{bullets.length !== 1 ? "s" : ""}</span>}
                      </div>
                    </div>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="sm" onClick={() => startEdit(exp)}>Edit</Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDeleteExperience(exp.id)}>Delete</Button>
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
                <div key={edu.id} className="flex items-start justify-between p-3 border rounded-lg">
                  <div>
                    <div className="font-medium">{edu.degree} {edu.field ? `in ${edu.field}` : ""}</div>
                    <div className="text-sm text-muted-foreground">{edu.institution}{edu.end_date ? ` (${edu.end_date})` : ""}</div>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => handleDeleteEducation(edu.id)}>Delete</Button>
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
                <div key={proj.id} className="flex items-start justify-between p-3 border rounded-lg">
                  <div className="flex-1">
                    <div className="font-medium">{proj.name}</div>
                    {proj.description && <p className="text-sm mt-1">{proj.description}</p>}
                    {proj.url && /^https?:\/\//i.test(proj.url) && (
                      <a href={proj.url} target="_blank" rel="noreferrer" className="text-sm text-primary">{proj.url}</a>
                    )}
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => handleDeleteProject(proj.id)}>Delete</Button>
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
