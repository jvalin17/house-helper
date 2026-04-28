import { useCallback, useState } from "react"

interface AsyncState<T> {
  data: T | null
  error: string
  isLoading: boolean
}

/**
 * Hook for async operations with loading/error state.
 * Replaces the repeated fetch+loading+error pattern across components.
 *
 * Usage:
 *   const { data, error, isLoading, run, reset } = useAsync<Job[]>()
 *   const handleLoad = () => run(() => api.listJobs())
 */
export function useAsync<T = unknown>() {
  const [state, setState] = useState<AsyncState<T>>({
    data: null,
    error: "",
    isLoading: false,
  })

  const run = useCallback(async (asyncFn: () => Promise<T>): Promise<T | undefined> => {
    setState((prev) => ({ ...prev, isLoading: true, error: "" }))
    try {
      const result = await asyncFn()
      setState({ data: result, error: "", isLoading: false })
      return result
    } catch (e) {
      const message = e instanceof Error ? e.message : "An error occurred"
      setState({ data: null, error: message, isLoading: false })
      return undefined
    }
  }, [])

  const reset = useCallback(() => {
    setState({ data: null, error: "", isLoading: false })
  }, [])

  return { ...state, run, reset }
}
