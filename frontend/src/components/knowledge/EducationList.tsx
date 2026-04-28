import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { Education } from "@/types"

interface Props {
  education: Education[]
  onDelete: (id: number) => void
}

export default function EducationList({ education, onDelete }: Props) {
  return (
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
                <Button variant="ghost" size="sm" onClick={() => onDelete(edu.id)}>Delete</Button>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
