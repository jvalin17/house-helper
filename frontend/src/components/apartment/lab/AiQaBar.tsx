import { useState } from "react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { api } from "@/api/client"
import { markdownToSafeHtml } from "@/utils/sanitize"

const SUGGESTED_QUESTIONS = [
  "How far is the nearest Indian grocery store?",
  "Is this good for someone with a large dog?",
  "How is the commute to downtown?",
  "Are there good restaurants nearby?",
  "How safe is this neighborhood at night?",
  "Are there parks or playgrounds nearby?",
  "What are the schools like nearby?",
  "Is there a farmers market nearby?",
]

interface Props {
  listingId: number
  qaHistory: Array<{ question: string; answer: string }>
  onQaUpdate: (newHistory: Array<{ question: string; answer: string }>) => void
}

export default function AiQaBar({ listingId, qaHistory, onQaUpdate }: Props) {
  const [qaInput, setQaInput] = useState("")
  const [qaLoading, setQaLoading] = useState(false)

  const handleAskQuestion = async () => {
    if (!qaInput.trim()) return
    setQaLoading(true)
    const questionText = qaInput.trim()
    setQaInput("")
    try {
      const result = await api.askAboutListing(listingId, questionText)
      onQaUpdate([...qaHistory, { question: result.question, answer: result.answer }])
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to get answer")
      setQaInput(questionText)
    } finally {
      setQaLoading(false)
    }
  }

  return (
    <div className="rounded-2xl bg-white border shadow-sm p-6 mb-6">
      <h3 className="text-sm font-medium text-purple-600 uppercase tracking-wider mb-3">Ask about this property</h3>

      {/* Q&A History */}
      {qaHistory.length > 0 && (
        <div className="space-y-4 mb-4 max-h-96 overflow-y-auto">
          {qaHistory.map((entry, index) => (
            <div key={index}>
              <div className="flex items-start gap-2 mb-1.5">
                <span className="w-5 h-5 rounded-full bg-purple-100 text-purple-700 flex items-center justify-center text-[10px] font-bold flex-shrink-0 mt-0.5">Q</span>
                <p className="text-sm font-medium text-gray-800">{entry.question}</p>
              </div>
              <div className="ml-7 bg-gray-50 rounded-xl p-3 border border-gray-100">
                <div className="text-sm text-gray-700 leading-relaxed [&_strong]:font-semibold [&_strong]:text-gray-800"
                  dangerouslySetInnerHTML={{ __html: markdownToSafeHtml(entry.answer) }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Suggestions — always visible, dim asked ones */}
      {!qaLoading && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {SUGGESTED_QUESTIONS.map((suggestion) => {
            const alreadyAsked = qaHistory.some(entry => entry.question === suggestion)
            return (
              <button key={suggestion}
                onClick={() => { if (!alreadyAsked) setQaInput(suggestion) }}
                className={`text-[11px] px-2.5 py-1 rounded-full transition-colors ${
                  alreadyAsked ? "bg-gray-100 text-gray-400 cursor-default line-through"
                    : "bg-purple-50 text-purple-600 hover:bg-purple-100 cursor-pointer"
                }`}>
                {suggestion.length > 40 ? suggestion.slice(0, 40) + "..." : suggestion}
              </button>
            )
          })}
        </div>
      )}

      {/* Loading */}
      {qaLoading && (
        <div className="flex items-center gap-3 py-3 mb-2">
          <div className="w-5 h-5 border-2 border-purple-300 border-t-purple-600 rounded-full animate-spin" />
          <span className="text-sm text-gray-500">Thinking about your question...</span>
        </div>
      )}

      {/* Input */}
      <div className="flex gap-2">
        <Input placeholder="Is this good for a dog owner? How far is the nearest Indian grocery?"
          value={qaInput} onChange={(event) => setQaInput(event.target.value)}
          onKeyDown={(event) => { if (event.key === "Enter" && qaInput.trim() && !qaLoading) { event.preventDefault(); handleAskQuestion() } }}
          disabled={qaLoading} />
        <Button className="bg-purple-600 hover:bg-purple-700 text-white px-4 flex-shrink-0"
          onClick={handleAskQuestion} disabled={qaLoading || !qaInput.trim()}>
          {qaLoading ? "..." : "Ask"}
        </Button>
      </div>
      {!qaLoading && qaHistory.length === 0 && (
        <p className="text-[10px] text-gray-400 mt-2">AI answers using listing data, analysis, and your preferences as context.</p>
      )}
    </div>
  )
}
