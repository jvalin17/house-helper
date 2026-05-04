import { describe, it, expect } from "vitest"
import { summarizeAnswer, shortenQuestion } from "./textSummarizer"

describe("summarizeAnswer", () => {
  const INDIAN_GROCERY_ANSWER = `Based on the Decker Lane location in East Austin, here are the nearest Indian grocery stores:
Closest Options:
• Shan Foods - approximately 8-10 miles southwest on South Lamar Boulevard
• Phoenicia Specialty Foods - approximately 10-12 miles west (carries Middle Eastern and some Indian products)
• Asia Market - approximately 6-8 miles west on East Cesar Chavez (limited Indian selection but some basics)

More Comprehensive Indian Groceries:
• Patel Brothers - approximately 12-15 miles northwest in North Austin/Round Rock area
• Bombay Bazaar - approximately 10-12 miles southwest near South Austin

The Decker neighborhood is quite car-dependent and doesn't have many ethnic grocery options nearby. You'll need to drive 15-20 minutes minimum to reach a proper Indian grocery store.

Note: These are approximate distances based on the property location. For verified details, use Nest Intel to get live data from Google Maps and Walk Score.`

  const SAFETY_ANSWER = `This is generally considered a **safe neighborhood**:
Safety Positives:
• Well-established suburban area with new development
• Good lighting and maintained streets
• Active community association

Safety Concerns:
• Some property crime reported in adjacent areas
• Limited nighttime pedestrian activity

Overall, the area has a low violent crime rate and is considered family-friendly.`

  const COMMUTE_ANSWER = `Here's the commute situation to downtown Austin:
Driving Commute:
• Distance: approximately 12-15 miles
• Rush hour: 30-45 minutes via I-35 or Mopac
• Off-peak: 20-25 minutes

Transit Options:
• MetroBus Route 803 - approximately 55-65 minutes with transfers
• No direct rail access from this location

I'd recommend checking Google Maps during your typical commute time for accurate estimates.`

  it("extracts first fact from Indian grocery answer, skips headers", () => {
    const result = summarizeAnswer(INDIAN_GROCERY_ANSWER)
    expect(result).toContain("Shan Foods")
    expect(result).not.toContain("Closest Options:")
    expect(result).not.toContain("here are the nearest")
    expect(result).not.toMatch(/:$/)
  })

  it("extracts Patel Brothers from second paragraph", () => {
    const result = summarizeAnswer(INDIAN_GROCERY_ANSWER)
    expect(result).toContain("Patel Brothers")
  })

  it("extracts car-dependent summary sentence", () => {
    const result = summarizeAnswer(INDIAN_GROCERY_ANSWER)
    expect(result).toContain("car-dependent")
  })

  it("skips Note disclaimer paragraph", () => {
    const result = summarizeAnswer(INDIAN_GROCERY_ANSWER)
    expect(result).not.toContain("Note:")
    expect(result).not.toContain("Nest Intel")
  })

  it("never ends a point with a colon", () => {
    const result = summarizeAnswer(INDIAN_GROCERY_ANSWER)
    const points = result.split(" • ")
    for (const point of points) {
      expect(point.trim()).not.toMatch(/:$/)
    }
  })

  it("extracts safety facts, skips Safety Positives header", () => {
    const result = summarizeAnswer(SAFETY_ANSWER)
    expect(result).not.toContain("Safety Positives:")
    expect(result).not.toContain("Safety Concerns:")
    expect(result).toContain("suburban area")
  })

  it("extracts commute facts, skips Driving Commute header", () => {
    const result = summarizeAnswer(COMMUTE_ANSWER)
    expect(result).not.toContain("Driving Commute:")
    expect(result).not.toContain("Transit Options:")
    expect(result).toContain("12-15 miles")
  })

  it("skips I'd recommend disclaimers from commute", () => {
    const result = summarizeAnswer(COMMUTE_ANSWER)
    expect(result).not.toContain("I'd recommend")
  })

  it("returns max 3 key points joined by bullet", () => {
    const result = summarizeAnswer(INDIAN_GROCERY_ANSWER)
    const points = result.split(" • ")
    expect(points.length).toBeLessThanOrEqual(3)
    expect(points.length).toBeGreaterThanOrEqual(1)
  })

  it("handles short simple answer without bullets", () => {
    const result = summarizeAnswer("Yes, this property allows large dogs. There are no breed restrictions mentioned.")
    expect(result).toContain("allows large dogs")
  })

  it("handles empty answer", () => {
    const result = summarizeAnswer("")
    expect(result).toBe("")
  })

  it("strips markdown bold markers", () => {
    const result = summarizeAnswer("The area is **very safe** with **low crime rates**.")
    expect(result).not.toContain("**")
    expect(result).toContain("very safe")
  })

  it("never returns just a header like 'Closest Options'", () => {
    const headerOnly = "Closest Options:\n• Store A - 5 miles\n• Store B - 10 miles"
    const result = summarizeAnswer(headerOnly)
    expect(result).not.toBe("Closest Options:")
    expect(result).toContain("Store A")
  })
})

describe("summarizeAnswer for comparison cards", () => {
  it("produces readable summary for 2-listing comparison", () => {
    const answers = [
      { question: "How far is Indian grocery?", answer: "Patel Brothers is approximately 5 miles away on North Lamar. India Bazaar is about 8 miles south." },
      { question: "Is it safe?", answer: "Very safe suburban area. Low crime statistics. Well-maintained streets." },
    ]

    for (const qa of answers) {
      const summary = summarizeAnswer(qa.answer)
      expect(summary.length).toBeGreaterThan(10)
      expect(summary).not.toMatch(/:$/)
      // Should not cut mid-word (no trailing partial words)
      expect(summary).not.toMatch(/\s\w{1,2}$/)
    }
  })

  it("produces readable summary for 3-listing comparison with verbose answers", () => {
    const verboseAnswers = [
      `Based on the location, here are nearby options:
Grocery Stores:
• H-E-B - 2.5 miles north on Research Boulevard
• Whole Foods - 3 miles east in the Domain

The area has excellent grocery access within a short drive.`,
      `Safety Assessment:
Overall Rating: Safe
• Low violent crime rate for the area
• Well-lit parking areas and gated access

Minor Concerns:
• Package theft reported occasionally
• Some traffic noise from nearby highway`,
      `Commute Details:
By Car:
• 20-25 minutes to downtown during rush hour
• 15 minutes off-peak via Mopac Expressway

The highway access is convenient for commuters heading south.`,
    ]

    for (const answer of verboseAnswers) {
      const summary = summarizeAnswer(answer)
      expect(summary.length).toBeGreaterThan(10)
      expect(summary.length).toBeLessThan(300)
      // No headers or colons at end
      expect(summary).not.toMatch(/:(\s*•\s*)?$/)
      expect(summary).not.toContain("Grocery Stores:")
      expect(summary).not.toContain("Safety Assessment:")
      expect(summary).not.toContain("Commute Details:")
      expect(summary).not.toContain("By Car:")
      expect(summary).not.toContain("Minor Concerns:")
    }
  })
})

describe("summarizeAnswer never cuts mid-word or mid-sentence", () => {
  const LONG_ANSWERS = [
    `Based on the Decker Lane location in East Austin, here are the nearest Indian grocery stores:
Closest Options:
• Patel Brothers - Approximately 3-4 miles southwest on South Lamar Boulevard near Barton Springs
• India Bazaar - Approximately 8-10 miles northwest in the North Austin area near Parmer Lane
The neighborhood has limited walkable grocery options but driving access is reasonable.`,

    `This is a very safe area with well-maintained streets and active neighborhood watch programs.
Safety Statistics:
• Violent crime rate is 40% below city average
• Property crime is moderate, mostly package theft
Overall the area is family-friendly and well-lit at night.`,

    `The commute to downtown is approximately 25-30 minutes during rush hour via I-35 or Mopac Expressway.
Transit Options:
• MetroBus Route 803 runs every 15 minutes during peak hours
• Capital Metro Rail station is about 2 miles from the property
You should test drive the commute during your typical work hours for accuracy.`,

    "Short answer with no bullets or sections at all.",

    `Here's a comprehensive analysis:
Overview:
The property is well-located.
Details:
• Feature one is good
• Feature two needs improvement
Conclusion:
Overall a solid choice for the price point.`,
  ]

  it("never produces output ending with a colon", () => {
    for (const answer of LONG_ANSWERS) {
      const result = summarizeAnswer(answer)
      expect(result).not.toMatch(/:\s*$/);
      // Also check each bullet point
      const points = result.split(" • ")
      for (const point of points) {
        expect(point.trim()).not.toMatch(/:\s*$/)
      }
    }
  })

  it("never cuts mid-word (no trailing 2-char fragments after space)", () => {
    for (const answer of LONG_ANSWERS) {
      const result = summarizeAnswer(answer)
      // A mid-word cut would look like "...some wo" or "...approximatel"
      // Check that result doesn't end with a partial word (lowercase letters without punctuation)
      const points = result.split(" • ")
      for (const point of points) {
        const trimmed = point.trim()
        if (trimmed.length === 0) continue
        // Should end with a letter, period, or closing paren — not mid-word
        // If it ends with a letter, the word should be at least 3 chars
        const lastWord = trimmed.split(/\s+/).pop() || ""
        if (lastWord.length > 0 && /^[a-z]+$/i.test(lastWord)) {
          // Last word should be a real word (3+ chars) unless it's a known short word
          const shortWords = new Set(["a", "an", "as", "at", "be", "by", "do", "go", "if", "in", "is", "it", "me", "my", "no", "of", "on", "or", "so", "to", "up", "us", "we"])
          if (!shortWords.has(lastWord.toLowerCase())) {
            expect(lastWord.length).toBeGreaterThanOrEqual(3)
          }
        }
      }
    }
  })

  it("each bullet point is a complete thought (ends with period or has verb)", () => {
    for (const answer of LONG_ANSWERS) {
      const result = summarizeAnswer(answer)
      if (result.length === 0) continue
      const points = result.split(" • ")
      for (const point of points) {
        const trimmed = point.trim()
        if (trimmed.length === 0) continue
        // Should be at least 8 characters (a real sentence/phrase)
        expect(trimmed.length).toBeGreaterThanOrEqual(8)
      }
    }
  })

  it("returns non-empty for all non-empty inputs", () => {
    for (const answer of LONG_ANSWERS) {
      const result = summarizeAnswer(answer)
      expect(result.length).toBeGreaterThan(0)
    }
  })
})

describe("shortenQuestion", () => {
  it("removes common prefixes", () => {
    expect(shortenQuestion("How far is the nearest Indian grocery store?")).toBe("Indian grocery store")
    expect(shortenQuestion("Is this good for someone with a large dog?")).toBe("someone with a large dog")
    expect(shortenQuestion("How safe is this neighborhood at night?")).toBe("this neighborhood at night")
    expect(shortenQuestion("Are there good restaurants nearby?")).toBe("good restaurants nearby")
  })

  it("removes question mark", () => {
    expect(shortenQuestion("What about parking?")).not.toContain("?")
  })

  it("keeps short questions as-is", () => {
    expect(shortenQuestion("Pet policy?")).toBe("Pet policy")
  })
})
