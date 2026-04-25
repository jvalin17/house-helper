import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { api } from "@/api/client"

interface Experience {
  id: number
  title: string
  company: string
  start_date: string
  end_date: string
  description: string
}

interface Skill {
  id: number
  name: string
  category: string
}

export default function KnowledgeBank() {
  const [experiences, setExperiences] = useState<Experience[]>([])
  const [skills, setSkills] = useState<Skill[]>([])
  const [freeText, setFreeText] = useState("")
  const [extractedSkills, setExtractedSkills] = useState<string[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ type: "job", title: "", company: "", start_date: "", end_date: "", description: "" })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const data = await api.listEntries() as { experiences: Experience[]; skills: Skill[] }
      setExperiences(data.experiences || [])
      const skillData = await api.listSkills() as Skill[]
      setSkills(skillData)
    } catch {
      // handle silently
    } finally {
      setLoading(false)
    }
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

  const handleAddExperience = async () => {
    await api.createEntry(form)
    setForm({ type: "job", title: "", company: "", start_date: "", end_date: "", description: "" })
    setShowForm(false)
    loadData()
  }

  const handleDeleteExperience = async (id: number) => {
    await api.deleteEntry(id)
    loadData()
  }

  if (loading) return <p className="text-muted-foreground">Loading knowledge bank...</p>

  const isEmpty = experiences.length === 0 && skills.length === 0

  return (
    <div className="space-y-6">
      {/* Empty State */}
      {isEmpty && (
        <Card className="border-dashed">
          <CardContent className="py-10 text-center">
            <div className="text-4xl mb-3">&#128218;</div>
            <h3 className="font-semibold mb-2">Your knowledge bank is empty</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Import your resume from the Jobs tab, or add experiences and skills manually below.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Free Text Extraction */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Add Knowledge</CardTitle>
        </CardHeader>
        <CardContent>
          <Textarea
            placeholder="Paste your experience, project descriptions, or anything about your work...&#10;&#10;Example: 'I worked at Google for 3 years building distributed systems with Java and Python. Led a team of 5 on the search ranking project. Reduced query latency by 40%.'"
            value={freeText}
            onChange={(e) => setFreeText(e.target.value)}
            rows={4}
            className="mb-3"
          />
          <Button onClick={handleExtract} disabled={!freeText.trim()}>
            Extract Skills
          </Button>

          {extractedSkills.length > 0 && (
            <div className="mt-4 p-4 bg-muted rounded-lg">
              <p className="text-sm font-medium mb-2">Found {extractedSkills.length} skills:</p>
              <div className="flex flex-wrap gap-2 mb-3">
                {extractedSkills.map((skill) => (
                  <Badge key={skill} variant="secondary">{skill}</Badge>
                ))}
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
          <Button variant="outline" size="sm" onClick={() => setShowForm(!showForm)}>
            {showForm ? "Cancel" : "+ Add Manually"}
          </Button>
        </CardHeader>
        <CardContent>
          {showForm && (
            <div className="grid grid-cols-2 gap-3 mb-4 p-4 bg-muted rounded-lg">
              <Input placeholder="Job Title" value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })} />
              <Input placeholder="Company" value={form.company}
                onChange={(e) => setForm({ ...form, company: e.target.value })} />
              <Input placeholder="Start Date (2020-01)" value={form.start_date}
                onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
              <Input placeholder="End Date (or leave empty)" value={form.end_date}
                onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
              <div className="col-span-2">
                <Textarea placeholder="What did you do?" value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })} rows={3} />
              </div>
              <Button onClick={handleAddExperience} disabled={!form.title}>Save Experience</Button>
            </div>
          )}

          {experiences.length === 0 && !showForm && (
            <p className="text-muted-foreground text-sm">No experiences yet.</p>
          )}

          <div className="space-y-3">
            {experiences.map((exp) => (
              <div key={exp.id} className="flex items-start justify-between p-3 border rounded-lg">
                <div>
                  <div className="font-medium">{exp.title} — {exp.company}</div>
                  <div className="text-xs text-muted-foreground">{exp.start_date} — {exp.end_date || "Present"}</div>
                  {exp.description && <p className="text-sm mt-1 line-clamp-2">{exp.description}</p>}
                </div>
                <Button variant="ghost" size="sm" onClick={() => handleDeleteExperience(exp.id)}>
                  Delete
                </Button>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Separator />

      {/* Skills */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Skills ({skills.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {skills.length === 0 ? (
            <p className="text-muted-foreground text-sm">No skills yet. Use "Add Knowledge" above to extract from text, or import your resume from the Jobs tab.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {skills.map((skill) => (
                <Badge key={skill.id} variant="outline">{skill.name}</Badge>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
