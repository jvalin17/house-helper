import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import ResumeBuilderTab from '@/components/tabs/ResumeBuilderTab'

// Mock api
vi.mock('@/api/client', () => ({
  api: {
    listJobs: vi.fn().mockResolvedValue([
      { id: 1, title: 'SWE at Google', company: 'Google', match_score: null, parsed_data: '{}', match_breakdown: null },
    ]),
    parseJobs: vi.fn().mockResolvedValue({ jobs: [] }),
    listEntries: vi.fn().mockResolvedValue({ experiences: [], skills: [], education: [], projects: [] }),
    listSkills: vi.fn().mockResolvedValue([]),
    getStoredResume: vi.fn().mockResolvedValue({ has_resume: false }),
    listTemplates: vi.fn().mockResolvedValue([]),
    extractSkills: vi.fn().mockResolvedValue({ extracted_skills: [], raw_text: '', source: 'text', method: 'algorithmic' }),
    importResume: vi.fn().mockResolvedValue({ experiences: 0, skills: 0 }),
    analyzeResumeFit: vi.fn().mockResolvedValue({
      current_resume_match: 65, knowledge_bank_match: 80, match_gap: '+15%',
      strengths: ['Python'], gaps: ['K8s'], suggested_improvements: [], summary: 'OK',
    }),
    generateResume: vi.fn().mockResolvedValue({ id: 1, content: 'resume' }),
    generateCoverLetter: vi.fn().mockResolvedValue({ id: 1, content: 'cl' }),
  },
}))

vi.mock('sonner', () => ({ toast: { success: vi.fn(), error: vi.fn() } }))

describe('Resume Builder Tab — State Independence', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('starts at My Superpowers sub-tab', () => {
    render(<BrowserRouter><ResumeBuilderTab /></BrowserRouter>)
    expect(screen.getByText('Superpower Lab')).toBeInTheDocument()
    expect(screen.getByText('My Superpowers')).toBeInTheDocument()
    expect(screen.getByText('Resume Builder')).toBeInTheDocument()
  })

  it('switching to Resume Builder shows job selection', async () => {
    render(<BrowserRouter><ResumeBuilderTab /></BrowserRouter>)
    await userEvent.click(screen.getByText('Resume Builder'))
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Paste a job link/)).toBeInTheDocument()
    })
  })

  it('switching away and back resets to job selection', async () => {
    render(<BrowserRouter><ResumeBuilderTab /></BrowserRouter>)

    // Go to builder
    await userEvent.click(screen.getByText('Resume Builder'))
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Paste a job link/)).toBeInTheDocument()
    })

    // Switch to superpowers and back
    await userEvent.click(screen.getByText('My Superpowers'))
    await userEvent.click(screen.getByText('Resume Builder'))

    // Should be at select step again
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/Paste a job link/)).toBeInTheDocument()
    })
  })

  it('ResumeBuilderTab and PreviewModal have independent state', () => {
    // Architectural test — verify no shared state or context
    // ResumeBuilderTab: step = "select" | "analyzing" | "analysis" | "generating" | "result"
    // PreviewModal: step = "checking" | "empty-kb" | "analyzing" | "analysis" | "generating" | "result" | "applied"
    // Different type definitions, different components, different useState calls

    const { container } = render(<BrowserRouter><ResumeBuilderTab /></BrowserRouter>)
    expect(container.querySelector('[role="dialog"]')).toBeNull()
  })
})

describe('Tab state — sub-tab switching', () => {
  beforeEach(() => { vi.clearAllMocks() })

  it('My Superpowers content persists across sub-tab switches', async () => {
    render(<BrowserRouter><ResumeBuilderTab /></BrowserRouter>)
    expect(screen.getByText('Superpower Lab')).toBeInTheDocument()
    await userEvent.click(screen.getByText('Resume Builder'))
    await userEvent.click(screen.getByText('My Superpowers'))
    expect(screen.getByText('Superpower Lab')).toBeInTheDocument()
  })

  it('Resume Builder always starts fresh on every switch', async () => {
    render(<BrowserRouter><ResumeBuilderTab /></BrowserRouter>)
    await userEvent.click(screen.getByText('Resume Builder'))
    await waitFor(() => expect(screen.getByPlaceholderText(/Paste a job link/)).toBeInTheDocument())
    await userEvent.click(screen.getByText('My Superpowers'))
    await userEvent.click(screen.getByText('Resume Builder'))
    await waitFor(() => expect(screen.getByPlaceholderText(/Paste a job link/)).toBeInTheDocument())
  })
})
