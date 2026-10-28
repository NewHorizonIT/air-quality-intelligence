import { useCallback, useEffect, useState } from 'react'

/**
 * Generic data-fetching hook.
 * @param {Function} fetcher  — async function returning data
 * @param {Array}    deps     — re-fetch when any dep changes
 * @param {boolean}  skip     — set true to defer the initial fetch
 */
export function useApi(fetcher, deps = [], skip = false) {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(!skip)
  const [error,   setError]   = useState(null)

  const run = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetcher()
      setData(result)
    } catch (err) {
      setError(err?.response?.data?.detail ?? err.message ?? 'Unknown error')
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  useEffect(() => {
    if (!skip) run()
  }, [run, skip])

  return { data, loading, error, refetch: run }
}
