import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Project } from "@/types"

interface Props {
  projects: Project[]
  onDelete: (id: number) => void
}

export default function ProjectList({ projects, onDelete }: Props) {
  return (
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
                <Button variant="ghost" size="sm" onClick={() => onDelete(proj.id)}>Delete</Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
