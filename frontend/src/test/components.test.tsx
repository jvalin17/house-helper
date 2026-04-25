import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import GenerationPrefs from '@/components/GenerationPrefs'
import JobDetail from '@/components/JobDetail'
import ResumeUpload from '@/components/ResumeUpload'

describe('GenerationPrefs', () => {
  it('renders all preference sections', () => {
    render(<GenerationPrefs onGenerate={vi.fn()} loading={false} />)
    expect(screen.getByText('Length')).toBeInTheDocument()
    expect(screen.getByText('Tone')).toBeInTheDocument()
    expect(screen.getByText('Emphasis')).toBeInTheDocument()
    expect(screen.getByText('Include Sections')).toBeInTheDocument()
  })

  it('renders length options', () => {
    render(<GenerationPrefs onGenerate={vi.fn()} loading={false} />)
    expect(screen.getByText('1 page')).toBeInTheDocument()
    expect(screen.getByText('2 pages')).toBeInTheDocument()
  })

  it('renders tone options', () => {
    render(<GenerationPrefs onGenerate={vi.fn()} loading={false} />)
    expect(screen.getByText('Professional')).toBeInTheDocument()
    expect(screen.getByText('Conversational')).toBeInTheDocument()
    expect(screen.getByText('Technical')).toBeInTheDocument()
  })

  it('renders section toggles', () => {
    render(<GenerationPrefs onGenerate={vi.fn()} loading={false} />)
    expect(screen.getByText('Summary')).toBeInTheDocument()
    expect(screen.getByText('Experience')).toBeInTheDocument()
    expect(screen.getByText('Skills')).toBeInTheDocument()
    expect(screen.getByText('Education')).toBeInTheDocument()
    expect(screen.getByText('Projects')).toBeInTheDocument()
  })

  it('calls onGenerate with preferences when button clicked', async () => {
    const onGenerate = vi.fn()
    render(<GenerationPrefs onGenerate={onGenerate} loading={false} />)
    await userEvent.click(screen.getByText('Generate Resume & Cover Letter'))
    expect(onGenerate).toHaveBeenCalledWith(
      expect.objectContaining({
        length: '1 page',
        tone: 'Professional',
        emphasis: 'Balanced',
        sections: expect.arrayContaining(['experience', 'skills']),
      })
    )
  })

  it('shows loading state', () => {
    render(<GenerationPrefs onGenerate={vi.fn()} loading={true} />)
    expect(screen.getByText('Generating...')).toBeInTheDocument()
  })
})

describe('JobDetail', () => {
  const mockJob = {
    id: 1,
    title: 'Software Engineer',
    company: 'BigTech',
    match_score: 0.75,
    parsed_data: JSON.stringify({
      required_skills: ['Python', 'React'],
      preferred_skills: ['Docker'],
      location: 'San Francisco',
      salary_range: '$150k - $200k',
      description: 'Build awesome things',
    }),
    match_breakdown: JSON.stringify({
      skills_overlap: 0.8,
      tfidf: 0.6,
    }),
  }

  it('renders job title and company', () => {
    render(<JobDetail job={mockJob} onClose={vi.fn()} onGenerate={vi.fn()} onRate={vi.fn()} />)
    expect(screen.getByText('Software Engineer')).toBeInTheDocument()
    expect(screen.getByText('BigTech')).toBeInTheDocument()
  })

  it('renders match score', () => {
    render(<JobDetail job={mockJob} onClose={vi.fn()} onGenerate={vi.fn()} onRate={vi.fn()} />)
    expect(screen.getByText('75%')).toBeInTheDocument()
  })

  it('renders required skills', () => {
    render(<JobDetail job={mockJob} onClose={vi.fn()} onGenerate={vi.fn()} onRate={vi.fn()} />)
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(screen.getByText('React')).toBeInTheDocument()
  })

  it('renders match rating buttons', () => {
    render(<JobDetail job={mockJob} onClose={vi.fn()} onGenerate={vi.fn()} onRate={vi.fn()} />)
    expect(screen.getByText('Yes')).toBeInTheDocument()
    expect(screen.getByText('Somewhat')).toBeInTheDocument()
    expect(screen.getByText('No')).toBeInTheDocument()
  })

  it('calls onRate when rating button clicked', async () => {
    const onRate = vi.fn()
    render(<JobDetail job={mockJob} onClose={vi.fn()} onGenerate={vi.fn()} onRate={onRate} />)
    await userEvent.click(screen.getByText('Yes'))
    expect(onRate).toHaveBeenCalledWith('good')
  })

  it('renders generate button', () => {
    render(<JobDetail job={mockJob} onClose={vi.fn()} onGenerate={vi.fn()} onRate={vi.fn()} />)
    expect(screen.getByText('Generate Resume & Cover Letter')).toBeInTheDocument()
  })

  it('renders location and salary', () => {
    render(<JobDetail job={mockJob} onClose={vi.fn()} onGenerate={vi.fn()} onRate={vi.fn()} />)
    expect(screen.getByText(/San Francisco/)).toBeInTheDocument()
    expect(screen.getByText(/\$150k/)).toBeInTheDocument()
  })
})

describe('ResumeUpload', () => {
  it('renders drag and drop area', () => {
    render(<ResumeUpload onImported={vi.fn()} onViewKnowledge={vi.fn()} />)
    expect(screen.getByText(/Drop your resume here/)).toBeInTheDocument()
    expect(screen.getByText(/DOCX, PDF, or TXT/)).toBeInTheDocument()
  })

  it('has a hidden file input', () => {
    render(<ResumeUpload onImported={vi.fn()} onViewKnowledge={vi.fn()} />)
    const input = document.getElementById('resume-upload') as HTMLInputElement
    expect(input).toBeTruthy()
    expect(input.type).toBe('file')
    expect(input.accept).toBe('.docx,.pdf,.txt')
  })
})
