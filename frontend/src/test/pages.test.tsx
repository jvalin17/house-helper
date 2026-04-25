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
    expect(screen.getByText('House Helper')).toBeInTheDocument()
  })

  it('renders subtitle', () => {
    render(<BrowserRouter><Home /></BrowserRouter>)
    expect(screen.getByText('Your personal AI assistant')).toBeInTheDocument()
  })

  it('renders job agent card', () => {
    render(<BrowserRouter><Home /></BrowserRouter>)
    expect(screen.getByText('Job Agent')).toBeInTheDocument()
  })

  it('renders apartment agent as coming soon', () => {
    render(<BrowserRouter><Home /></BrowserRouter>)
    expect(screen.getByText('Apartment Agent')).toBeInTheDocument()
  })

  it('renders recipe agent as coming soon', () => {
    render(<BrowserRouter><Home /></BrowserRouter>)
    expect(screen.getByText('Recipe Agent')).toBeInTheDocument()
  })

  it('renders all three agent cards', () => {
    render(<BrowserRouter><Home /></BrowserRouter>)
    const cards = screen.getAllByText(/Agent/)
    expect(cards.length).toBeGreaterThanOrEqual(3)
  })
})
