import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { api } from "@/api/client"

interface Props {
  onJobsParsed: () => void
}

export default function JobInput({ onJobsParsed }: Props) {
  const [input, setInput] = useState("")
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState("")

  const handleSubmit = async () => {
    if (!input.trim()) return

    setLoading(true)
    setMessage("")

    try {
      const lines = input.split("\n").map((l) => l.trim()).filter(Boolean)
      const result = await api.parseJobs(lines)
      const count = result.jobs.length
      setMessage(`Parsed ${count} job${count !== 1 ? "s" : ""} successfully`)
      setInput("")
      onJobsParsed()
    } catch (err) {
      setMessage(`Error: ${err instanceof Error ? err.message : "Unknown error"}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle className="text-lg">Add Jobs</CardTitle>
      </CardHeader>
      <CardContent>
        <Textarea
          placeholder={"Paste job links (one per line) or a job description...\n\nhttps://careers.example.com/job/123\nhttps://boards.greenhouse.io/company/jobs/456"}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          rows={5}
          className="mb-3 font-mono text-sm"
        />
        <div className="flex items-center gap-3">
          <Button onClick={handleSubmit} disabled={loading || !input.trim()}>
            {loading ? "Parsing..." : "Parse Jobs"}
          </Button>
          {message && (
            <span className={`text-sm ${message.startsWith("Error") ? "text-destructive" : "text-green-600"}`}>
              {message}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
