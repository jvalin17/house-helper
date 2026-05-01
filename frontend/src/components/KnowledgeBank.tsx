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

  const handleSaveExperience = async (form: Record<string, string>) => {
    try {
      await api.createEntry(form)
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

  const handleDeleteProject = async (id: number) => {
    try { await api.deleteProject(id); loadData() }
    catch (e) { toast.error(e instanceof Error ? e.message : "Failed to delete") }
  }

  const handleDeleteSkill = async (skillId: number) => {
    try {
      await api.deleteSkill(skillId)
      setSkills(previousSkills => previousSkills.filter(skill => skill.id !== skillId))
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to delete skill")
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
            <Input placeholder="Paste a link (GitHub, LinkedIn, portfolio, etc.)"
              value={linkInput} onChange={(e) => setLinkInput(e.target.value)} className="mb-2" />
            <Button size="sm" onClick={handleFetchLink} disabled={!linkInput.trim() || linkLoading}>
              {linkLoading ? "Extracting..." : "Extract from Link"}
            </Button>
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
        experiences={experiences}
        onSave={handleSaveExperience}
        onEdit={() => {}}
        onDelete={handleDeleteExperience}
      />

      <EducationList education={education} onDelete={handleDeleteEducation} />

      <ProjectList projects={projects} onDelete={handleDeleteProject} />

      <Separator />

      <SkillsDisplay skills={skills} onDelete={handleDeleteSkill} />
    </div>
  )
}
