import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { BrowserRouter } from 'react-router-dom'
import Home from '@/pages/Home'

// Mock fetch for stats
globalThis.fetch = vi.fn(() =>
  Promise.resolve({ ok: true, json: () => Promise.resolve([]) })
) as unknown as typeof fetch

describe('Home (Landing Page)', () => {
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

  it('renders coming soon agents', () => {
    render(<BrowserRouter><Home /></BrowserRouter>)
    expect(screen.getByText('Apartment Agent')).toBeInTheDocument()
    expect(screen.getByText('Recipe Agent')).toBeInTheDocument()
    expect(screen.getByText('Travel Agent')).toBeInTheDocument()
  })

  it('renders request agent card', () => {
    render(<BrowserRouter><Home /></BrowserRouter>)
    expect(screen.getByText('Request Agent')).toBeInTheDocument()
  })
})
