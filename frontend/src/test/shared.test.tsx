import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import Modal from '@/components/shared/Modal'
import StatCard from '@/components/shared/StatCard'

describe('Modal', () => {
  it('renders children', () => {
    render(<Modal onClose={vi.fn()}><p>Hello Modal</p></Modal>)
    expect(screen.getByText('Hello Modal')).toBeInTheDocument()
  })

  it('has dialog role', () => {
    render(<Modal onClose={vi.fn()}><p>Content</p></Modal>)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })

  it('calls onClose when backdrop clicked', async () => {
    const onClose = vi.fn()
    render(<Modal onClose={onClose}><p>Content</p></Modal>)
    const backdrop = screen.getByRole('dialog')
    await userEvent.click(backdrop)
    expect(onClose).toHaveBeenCalled()
  })

  it('does not close when content clicked', async () => {
    const onClose = vi.fn()
    render(<Modal onClose={onClose}><p>Content</p></Modal>)
    await userEvent.click(screen.getByText('Content'))
    expect(onClose).not.toHaveBeenCalled()
  })

  it('renders with custom className', () => {
    render(<Modal onClose={vi.fn()} className="max-w-lg"><p>Content</p></Modal>)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
  })
})

describe('StatCard', () => {
  it('renders value and label', () => {
    render(<StatCard value={42} label="Total Jobs" />)
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('Total Jobs')).toBeInTheDocument()
  })

  it('renders string values', () => {
    render(<StatCard value="$0.07" label="Today" />)
    expect(screen.getByText('$0.07')).toBeInTheDocument()
  })
})
