/**
 * HTML sanitizer — prevents XSS from LLM-generated content.
 *
 * Uses DOMPurify to strip scripts, event handlers, and dangerous HTML
 * before rendering via dangerouslySetInnerHTML.
 */

import DOMPurify from "dompurify"

/**
 * Sanitize HTML string — removes scripts, event handlers, and dangerous tags.
 * Safe for use with dangerouslySetInnerHTML.
 */
export function sanitizeHtml(dirtyHtml: string): string {
  return DOMPurify.sanitize(dirtyHtml, {
    ALLOWED_TAGS: ["strong", "em", "b", "i", "br", "div", "span", "p", "ul", "li", "ol"],
    ALLOWED_ATTR: ["class"],
  })
}

/**
 * Convert markdown-like LLM text to sanitized HTML.
 * Handles: **bold**, bullet points (- item), paragraph breaks.
 */
export function markdownToSafeHtml(text: string): string {
  const html = text
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/^- (.+)$/gm, '{{BULLET}}$1{{/BULLET}}')
    .replace(/\n*{{BULLET}}/g, '<div class="flex items-start gap-2 py-0.5 ml-1"><span class="w-1.5 h-1.5 rounded-full bg-purple-400 flex-shrink-0 mt-1.5"></span><span>')
    .replace(/{{\/BULLET}}\n*/g, "</span></div>")
    .replace(/\n\n/g, '<div class="h-2.5"></div>')
    .replace(/\n/g, " ")

  return sanitizeHtml(html)
}
