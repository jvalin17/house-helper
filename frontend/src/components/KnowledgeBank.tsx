import { useEffect, useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { api } from "@/api/client"
import type { Experience, Skill, Education, Project, ResumeTemplate } from "@/types"
import TemplateManager from "@/components/knowledge/TemplateManager"
import ExperienceList from "@/components/knowledge/ExperienceList"
import EducationList from "@/components/knowledge/EducationList"
import ProjectList from "@/components/knowledge/ProjectList"
import SkillsDisplay from "@/components/knowledge/SkillsDisplay"
import CategorySaveButton from "@/components/knowledge/CategorySaveButton"

export default function KnowledgeBank() {
  const [experiences, setExperiences] = useState<Experience[]>([])
  const [skills, setSkills] = useState<Skill[]>([])
  const [education, setEducation] = useState<Education[]>([])
  const [projects, setProjects] = useState<Project[]>([])
  const [templates, setTemplates] = useState<ResumeTemplate[]>([])
  const [storedResume, setStoredResume] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)
  const [uploadingTemplate, setUploadingTemplate] = useState(false)

  // Skill extraction state
  const [freeText, setFreeText] = useState("")
  const [linkInput, setLinkInput] = useState("")
  const [linkLoading, setLinkLoading] = useState(false)
  const [linkPreview, setLinkPreview] = useState<{ skills: string[]; description: string } | null>(null)
  const [extractedSkills, setExtractedSkills] = useState<string[]>([])
  const [acceptedSkills, setAcceptedSkills] = useState<Set<string>>(new Set())

  // Bullet extraction state
  const [showBulletCostWarning, setShowBulletCostWarning] = useState(false)
  const [bulletLoading, setBulletLoading] = useState(false)
  const [extractedExperiences, setExtractedExperiences] = useState<Array<{ company: string; title: string; bullets: string[] }>>([])
  const [extractedProjects, setExtractedProjects] = useState<Array<{ name: string; description: string; tech_stack: string }>>([])


  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    try {
      const data = await api.listEntries()
      setExperiences(Array.isArray(data.experiences) ? data.experiences : [])
      setEducation(Array.isArray(data.education) ? data.education : [])
      setProjects(Array.isArray(data.projects) ? data.projects : [])
      const skillData = await api.listSkills()
      setSkills(Array.isArray(skillData) ? skillData : [])
      try { setStoredResume(await api.getStoredResume()) } catch { /* no resume */ }
      try { const templateList = await api.listTemplates(); setTemplates(Array.isArray(templateList) ? templateList : []) } catch { /* no templates */ }
    } catch { /* silent */ } finally { setLoading(false) }
  }

  // ── Skill extraction handlers ─────────────────

  const handleExtract = async () => {
    const text = freeText.trim() || linkInput.trim()
    if (!text) return
    try {
      const result = await api.extractSkills(text)
      const skillsList = Array.isArray(result.extracted_skills) ? result.extracted_skills : []
      setExtractedSkills(skillsList)
      setAcceptedSkills(new Set(skillsList))
    } catch (e) { toast.error(e instanceof Error ? e.message : "Skill extraction failed") }
  }

  const handleFetchLink = async () => {
    if (!linkInput.trim()) return
    setLinkLoading(true)
    setLinkPreview(null)
    try {
      const result = await api.extractSkills(linkInput.trim())
      const skillsList = Array.isArray(result.extracted_skills) ? result.extracted_skills : []
      setExtractedSkills(skillsList)
      setAcceptedSkills(new Set(skillsList))
      setLinkPreview({ skills: skillsList, description: (result.raw_text || "").slice(0, 500) })
      if (result.source === "url" && result.raw_text) setFreeText(result.raw_text.slice(0, 2000))
    } catch (err) {
      setLinkPreview({ skills: [], description: err instanceof Error ? err.message : "Failed to fetch" })
    } finally { setLinkLoading(false) }
  }

  const handleSaveSkills = async () => {
    try {
      for (const skill of extractedSkills.filter((extractedSkill) => acceptedSkills.has(extractedSkill))) {
        await api.createSkill({ name: skill, category: "extracted" })
      }
      setExtractedSkills([]); setAcceptedSkills(new Set())
      setFreeText(""); setLinkInput(""); setLinkPreview(null)
      loadData()
      toast.success("Skills saved")
    } catch (e) { toast.error(e instanceof Error ? e.message : "Failed to save skills") }
  }

  const toggleSkill = (skill: string) => {
    setAcceptedSkills((prev) => {
      const next = new Set(prev)
      if (next.has(skill)) next.delete(skill); else next.add(skill)
      return next
    })
  }

  // ── CRUD handlers ─────────────────────────────

  const handleSaveExperience = async (form: Record<string, string>, editingId?: number) => {
    try {
      if (editingId) {
        await api.updateEntry(editingId, form)
      } else {
        await api.createEntry(form)
      }
      loadData()
    } catch (e) { toast.error(e instanceof Error ? e.message : "Failed to save experience") }
  }

  const handleDeleteExperience = async (id: number) => {
    try { await api.deleteEntry(id); loadData() }
    catch (e) { toast.error(e instanceof Error ? e.message : "Failed to delete") }
  }

  const handleDeleteEducation = async (id: number) => {
    try { await api.deleteEducation(id); loadData() }
    catch (e) { toast.error(e instanceof Error ? e.message : "Failed to delete") }
  }

  const handleEditEducation = async (educationId: number, data: Record<string, string>) => {
    try {
      await api.updateEducation(educationId, data)
      loadData()
      toast.success("Education updated")
    } catch (e) { toast.error(e instanceof Error ? e.message : "Failed to update") }
  }

  const handleDeleteProject = async (id: number) => {
    try { await api.deleteProject(id); loadData() }
    catch (e) { toast.error(e instanceof Error ? e.message : "Failed to delete") }
  }

  const handleEditProject = async (projectId: number, data: Record<string, string>) => {
    try {
      await api.updateProject(projectId, data)
      loadData()
      toast.success("Project updated")
    } catch (e) { toast.error(e instanceof Error ? e.message : "Failed to update") }
  }

  const handleDeleteSkill = async (skillId: number) => {
    try {
      await api.deleteSkill(skillId)
      setSkills(previousSkills => previousSkills.filter(skill => skill.id !== skillId))
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to delete skill")
    }
  }

  const handleDeleteSkillCategory = async (category: string) => {
    try {
      const result = await api.deleteSkillsByCategory(category)
      setSkills(previousSkills => previousSkills.filter(skill => skill.category !== category))
      toast.success(`Removed ${result.deleted_count} ${category} skills`)
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to delete skills")
    }
  }

  const handleEditSkill = async (skillId: number, data: Record<string, string>) => {
    try {
      await api.updateSkill(skillId, data)
      setSkills(previousSkills =>
        previousSkills.map(skill => skill.id === skillId ? { ...skill, ...data } : skill)
      )
      toast.success("Skill updated")
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to update skill")
    }
  }

  const handleUploadTemplate = async (file: File) => {
    setUploadingTemplate(true)
    try { await api.uploadTemplate(file); loadData() }
    catch (e) { toast.error(e instanceof Error ? e.message : "Upload failed") }
    finally { setUploadingTemplate(false) }
  }

  const handleSetDefaultTemplate = async (id: number) => {
    try { await api.setDefaultTemplate(id); loadData() }
    catch (e) { toast.error(e instanceof Error ? e.message : "Failed to set default") }
  }

  const handleDeleteTemplate = async (id: number) => {
    try { await api.deleteTemplate(id); loadData() }
    catch (e) { toast.error(e instanceof Error ? e.message : "Failed to delete template") }
  }

  if (loading) return <p className="text-muted-foreground">Loading...</p>

  const isEmpty = experiences.length === 0 && skills.length === 0

  return (
    <div className="space-y-6">
      {isEmpty && (
        <Card className="border-dashed">
          <CardContent className="py-10 text-center">
            <h3 className="font-semibold mb-2">Your superpowers are hidden!</h3>
            <p className="text-sm text-muted-foreground">
              Import your resume from the Jobs tab, or add experiences and skills below.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Add Knowledge — skill extraction */}
      <Card>
        <CardHeader><CardTitle className="text-lg">Add Knowledge</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          <div>
            <Input placeholder="Paste a link (LinkedIn profile, portfolio, Wikipedia, GitHub, etc.)"
              value={linkInput} onChange={(e) => setLinkInput(e.target.value)} className="mb-2" />
            <div className="flex gap-2 flex-wrap">
              <Button size="sm" onClick={handleFetchLink} disabled={!linkInput.trim() || linkLoading}>
                {linkLoading ? "Extracting..." : "Extract Skills"}
              </Button>
              <Button size="sm" variant="outline" disabled={!linkInput.trim() || bulletLoading}
                onClick={() => {
                  if (!linkInput.trim()) return
                  setShowBulletCostWarning(true)
                }}>
                {bulletLoading ? "Extracting..." : "Extract Experiences"}
              </Button>
            </div>
            {showBulletCostWarning && (
              <div className="mt-2 p-3 rounded-lg border border-orange-200 bg-orange-50 text-sm">
                <p className="font-medium text-orange-800 mb-1">This uses AI and costs tokens</p>
                <p className="text-xs text-orange-700 mb-2">
                  The page content will be sent to your configured AI provider for analysis. Typical cost: ~$0.002-0.01 per extraction depending on page length and model.
                </p>
                <div className="flex gap-2">
                  <Button size="sm" onClick={async () => {
                    setShowBulletCostWarning(false)
                    setBulletLoading(true)
                    try {
                      const result = await api.extractBullets(linkInput.trim())
                      setExtractedExperiences(result.experiences)
                      setExtractedProjects(result.projects || [])
                      const totalFound = result.experiences.length + (result.projects || []).length
                      if (totalFound === 0) {
                        toast.info("No work experiences or projects found on this page")
                      } else {
                        const parts = []
                        if (result.experiences.length > 0) parts.push(`${result.experiences.length} experience(s)`)
                        if ((result.projects || []).length > 0) parts.push(`${(result.projects || []).length} project(s)`)
                        toast.success(`Found ${parts.join(" and ")}`)
                      }
                    } catch (error) {
                      toast.error(error instanceof Error ? error.message : "Extraction failed")
                    } finally {
                      setBulletLoading(false)
                    }
                  }}>Proceed</Button>
                  <Button size="sm" variant="ghost" onClick={() => setShowBulletCostWarning(false)}>Cancel</Button>
                </div>
              </div>
            )}
            {(extractedExperiences.length > 0 || extractedProjects.length > 0) && (
              <div className="mt-3 space-y-3">
                <p className="text-sm font-medium">Extracted from page:</p>
                {extractedExperiences.map((experience, index) => (
                  <div key={`exp-${index}`} className="p-3 border rounded-lg">
                    <div className="font-medium text-sm">{experience.title} at {experience.company}</div>
                    <ul className="mt-1 space-y-0.5">
                      {experience.bullets.map((bullet, bulletIndex) => (
                        <li key={bulletIndex} className="text-xs text-muted-foreground">- {bullet}</li>
                      ))}
                    </ul>
                    <div className="mt-2">
                      <CategorySaveButton
                        data={{ title: experience.title, company: experience.company, description: experience.bullets.join("\n"), source_url: linkInput.trim() }}
                        onSave={async (categoryType, itemData) => {
                          try {
                            await api.createEntry({ type: categoryType, ...itemData })
                            setExtractedExperiences(previous => previous.filter((_, experienceIndex) => experienceIndex !== index))
                            loadData()
                            toast.success(`Saved as ${categoryType}: ${experience.title}`)
                          } catch (error) {
                            toast.error(error instanceof Error ? error.message : "Failed to save")
                          }
                        }}
                      />
                    </div>
                  </div>
                ))}
                {extractedProjects.map((project, index) => (
                  <div key={`proj-${index}`} className="p-3 border rounded-lg">
                    <div className="font-medium text-sm">{project.name}</div>
                    <p className="text-xs text-muted-foreground mt-1">{project.description}</p>
                    {project.tech_stack && (
                      <p className="text-xs text-muted-foreground mt-0.5">Tech: {project.tech_stack}</p>
                    )}
                    <div className="mt-2">
                      <CategorySaveButton
                        data={{ title: project.name, company: "", description: project.description, source_url: linkInput.trim() }}
                        onSave={async (categoryType, itemData) => {
                          try {
                            await api.createEntry({ type: categoryType, ...itemData })
                            setExtractedProjects(previous => previous.filter((_, projectIndex) => projectIndex !== index))
                            loadData()
                            toast.success(`Saved as ${categoryType}: ${project.name}`)
                          } catch (error) {
                            toast.error(error instanceof Error ? error.message : "Failed to save")
                          }
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div className="flex items-center gap-3">
            <Separator className="flex-1" />
            <span className="text-xs text-muted-foreground">or paste text</span>
            <Separator className="flex-1" />
          </div>
          <div>
            <Textarea placeholder="Paste your experience, project description, or any relevant text..."
              value={freeText} onChange={(e) => setFreeText(e.target.value)} rows={3} />
            <Button size="sm" className="mt-2" onClick={handleExtract} disabled={!freeText.trim()}>
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
                {extractedSkills.map((extractedSkill) => (
                  <Badge key={extractedSkill}
                    variant={acceptedSkills.has(extractedSkill) ? "default" : "outline"}
                    className={`cursor-pointer transition-opacity ${acceptedSkills.has(extractedSkill) ? "" : "opacity-40 line-through"}`}
                    onClick={() => toggleSkill(extractedSkill)}>{extractedSkill}</Badge>
                ))}
              </div>
              <div className="flex items-center gap-3">
                <Button size="sm" onClick={handleSaveSkills} disabled={acceptedSkills.size === 0}>
                  Save {acceptedSkills.size} Skill{acceptedSkills.size !== 1 ? "s" : ""}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => {
                  setExtractedSkills([]); setAcceptedSkills(new Set()); setLinkPreview(null)
                }}>Dismiss All</Button>
                <span className="text-xs text-muted-foreground">{acceptedSkills.size}/{extractedSkills.length} selected</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      <TemplateManager
        templates={templates}
        storedResume={storedResume}
        onUpload={handleUploadTemplate}
        onSetDefault={handleSetDefaultTemplate}
        onDelete={handleDeleteTemplate}
        isUploading={uploadingTemplate}
      />

      <ExperienceList
        experiences={experiences.filter(experience => experience.type === "job" || !experience.type)}
        onSave={handleSaveExperience}
        onEdit={() => {}}
        onDelete={handleDeleteExperience}
        sectionTitle="Work Experience"
      />

      {experiences.filter(experience => experience.type === "volunteering").length > 0 && (
        <ExperienceList
          experiences={experiences.filter(experience => experience.type === "volunteering")}
          onSave={handleSaveExperience}
          onEdit={() => {}}
          onDelete={handleDeleteExperience}
          sectionTitle="Volunteering"
        />
      )}

      {experiences.filter(experience => experience.type === "certification").length > 0 && (
        <ExperienceList
          experiences={experiences.filter(experience => experience.type === "certification")}
          onSave={handleSaveExperience}
          onEdit={() => {}}
          onDelete={handleDeleteExperience}
          sectionTitle="Certifications"
        />
      )}

      {experiences.filter(experience => !["job", "volunteering", "certification", ""].includes(experience.type || "job")).length > 0 && (
        <ExperienceList
          experiences={experiences.filter(experience => !["job", "volunteering", "certification", ""].includes(experience.type || "job"))}
          onSave={handleSaveExperience}
          onEdit={() => {}}
          onDelete={handleDeleteExperience}
          sectionTitle="Other Experience"
        />
      )}

      <EducationList education={education} onDelete={handleDeleteEducation} onEdit={handleEditEducation} />

      <ProjectList projects={projects} onDelete={handleDeleteProject} onEdit={handleEditProject} />

      <Separator />

      <SkillsDisplay skills={skills} onDelete={handleDeleteSkill} onDeleteCategory={handleDeleteSkillCategory} onEdit={handleEditSkill} />
    </div>
  )
}
