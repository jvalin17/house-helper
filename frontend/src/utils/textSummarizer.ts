/**
 * Text summarizer — extracts key sentences from LLM answers.
 *
 * Rules:
 * - Takes first complete sentence from each paragraph (max 3 paragraphs)
 * - Never returns lines ending with ":" (section headers)
 * - Never returns bullet markers without content
 * - Never cuts mid-word or mid-sentence
 * - Skips disclaimer paragraphs ("Note:", "For verified...")
 * - Joins results with " • "
 */

const SKIP_PATTERNS = [
  /^Note:/i,
  /^For verified/i,
  /^For more precise/i,
  /^I['']d recommend/i,
  /^You should/i,
  /^These are approximate/i,
]

const HEADER_PATTERNS = [
  /:\s*$/, // Ends with colon
  /^(Closest|Safety|Driving|Options|Positives|Negatives|Commute|More Comprehensive)\s/i,
]

export function summarizeAnswer(raw: string): string {
  const cleaned = raw.replace(/\*\*/g, "").trim()

  // Split into paragraphs
  const paragraphs = cleaned
    .split(/\n\n+|\n(?=[A-Z][\w\s]*:)/)
    .map(paragraph => paragraph.trim())
    .filter(paragraph => paragraph.length > 5)

  const keyLines: string[] = []

  for (const paragraph of paragraphs) {
    // Skip disclaimers
    if (SKIP_PATTERNS.some(pattern => pattern.test(paragraph))) continue

    // Get individual lines/bullets
    const lines = paragraph
      .split(/\n/)
      .map(line => line.replace(/^[-•*]\s*/, "").trim())
      .filter(line => line.length > 5)

    for (const line of lines) {
      // Skip section headers (lines ending with ":" or starting with header words)
      if (HEADER_PATTERNS.some(pattern => pattern.test(line))) continue

      // Extract first complete sentence
      const sentenceEnd = line.search(/[.!?](\s|$)/)
      const sentence = sentenceEnd > 10 ? line.slice(0, sentenceEnd + 1) : line

      // Final validation — don't return if it ends with ":" or is just a label
      if (sentence.endsWith(":") || sentence.length < 8) continue

      keyLines.push(sentence)
      break // Only first valid line per paragraph
    }

    if (keyLines.length >= 3) break
  }

  return keyLines.join(" • ")
}

export function shortenQuestion(question: string): string {
  return question
    .replace(
      /^(How far is the nearest |How far is |Is this good for |Are there |How is the |What are the |How safe is |Is it a? )/i,
      "",
    )
    .replace(/\?$/, "")
}
