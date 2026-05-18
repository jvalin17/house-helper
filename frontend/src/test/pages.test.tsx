import { render, screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import Home from '@/pages/Home'
import { api } from '@/api/client'

vi.mock('@/api/client')

describe('Home (Landing Page)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(api.getHomeStats).mockResolvedValue({ applications: 0, homes_explored: 0, hours_saved: 0 })
    vi.mocked(api.getCredentialsReadiness).mockResolvedValue({
      ai_ready: true, nestscout_ready: true, jobsmith_ready: true,
      ai_provider: "claude", configured_count: 3, total_count: 14,
    })
  })

  it('renders app title', () => {
    render(<BrowserRouter><Home /></BrowserRouter>)
    expect(screen.getByText('Panini')).toBeInTheDocument()
  })

  it('renders subtitle', () => {
    render(<BrowserRouter><Home /></BrowserRouter>)
    expect(screen.getByText('Your personal AI assistant')).toBeInTheDocument()
  })

  it('renders jobsmith card', () => {
    render(<BrowserRouter><Home /></BrowserRouter>)
    expect(screen.getByText('Jobsmith')).toBeInTheDocument()
  })

  it('renders NestScout as active and other agents as coming soon', () => {
    render(<BrowserRouter><Home /></BrowserRouter>)
    expect(screen.getByText('NestScout')).toBeInTheDocument()
    expect(screen.getByText('Recipe Agent')).toBeInTheDocument()
    expect(screen.getByText('Travel Agent')).toBeInTheDocument()
  })

  it('renders request agent card', () => {
    render(<BrowserRouter><Home /></BrowserRouter>)
    expect(screen.getByText('Request Agent')).toBeInTheDocument()
  })

  it('shows "Needs setup" tag when agent source is not configured', async () => {
    vi.mocked(api.getCredentialsReadiness).mockResolvedValue({
      ai_ready: false, nestscout_ready: false, jobsmith_ready: false,
      ai_provider: null, configured_count: 0, total_count: 14,
    })
    render(<BrowserRouter><Home /></BrowserRouter>)
    await waitFor(() => {
      const setupTags = screen.getAllByText('Needs setup')
      expect(setupTags.length).toBe(2)
    })
  })

  it('shows no badge when agent is fully configured', async () => {
    render(<BrowserRouter><Home /></BrowserRouter>)
    await waitFor(() => expect(api.getCredentialsReadiness).toHaveBeenCalled())
    expect(screen.queryByText('Needs setup')).not.toBeInTheDocument()
  })

  it('shows "Get started" tile when nothing is configured', async () => {
    vi.mocked(api.getCredentialsReadiness).mockResolvedValue({
      ai_ready: false, nestscout_ready: false, jobsmith_ready: false,
      ai_provider: null, configured_count: 0, total_count: 14,
    })
    render(<BrowserRouter><Home /></BrowserRouter>)
    await waitFor(() => {
      expect(screen.getByText('Get started')).toBeInTheDocument()
      expect(screen.getByText('Connect an API source')).toBeInTheDocument()
    })
  })

  it('hides "Get started" tile when sources are configured', async () => {
    render(<BrowserRouter><Home /></BrowserRouter>)
    await waitFor(() => expect(api.getCredentialsReadiness).toHaveBeenCalled())
    expect(screen.queryByText('Get started')).not.toBeInTheDocument()
  })
})
