import { renderHook, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { useAsync } from '@/hooks/useAsync'

describe('useAsync hook', () => {
  it('starts in idle state', () => {
    const { result } = renderHook(() => useAsync())
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBe("")
    expect(result.current.data).toBeNull()
  })

  it('sets loading during execution', async () => {
    const { result } = renderHook(() => useAsync())

    let resolve: (v: string) => void
    const promise = new Promise<string>((r) => { resolve = r })

    act(() => { result.current.run(() => promise) })
    expect(result.current.isLoading).toBe(true)

    await act(async () => { resolve!("done") })
    expect(result.current.isLoading).toBe(false)
  })

  it('returns data on success', async () => {
    const { result } = renderHook(() => useAsync<string>())

    await act(async () => {
      await result.current.run(() => Promise.resolve("hello"))
    })

    expect(result.current.data).toBe("hello")
    expect(result.current.error).toBe("")
    expect(result.current.isLoading).toBe(false)
  })

  it('sets error on failure', async () => {
    const { result } = renderHook(() => useAsync())

    await act(async () => {
      await result.current.run(() => Promise.reject(new Error("failed")))
    })

    expect(result.current.error).toBe("failed")
    expect(result.current.data).toBeNull()
    expect(result.current.isLoading).toBe(false)
  })

  it('resets state', async () => {
    const { result } = renderHook(() => useAsync<string>())

    await act(async () => {
      await result.current.run(() => Promise.resolve("data"))
    })
    expect(result.current.data).toBe("data")

    act(() => { result.current.reset() })
    expect(result.current.data).toBeNull()
    expect(result.current.error).toBe("")
  })

  it('returns the async result from run()', async () => {
    const { result } = renderHook(() => useAsync<number>())

    let returnedValue: number | undefined
    await act(async () => {
      returnedValue = await result.current.run(() => Promise.resolve(42))
    })

    expect(returnedValue).toBe(42)
  })
})
