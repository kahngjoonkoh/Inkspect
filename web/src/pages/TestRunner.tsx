import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, errorMessage } from '../api/client'
import type { SessionState } from '../api/types'
import ResponsePhase from '../components/ResponsePhase'
import InquiryPhase from '../components/InquiryPhase'

export default function TestRunner() {
  const { id = '' } = useParams()
  const navigate = useNavigate()
  const [state, setState] = useState<SessionState | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    try {
      setState(await api.session(id))
    } catch (err) {
      setError(errorMessage(err))
    }
  }, [id])

  useEffect(() => {
    let cancelled = false
    api
      .session(id)
      .then((s) => {
        if (!cancelled) setState(s)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(errorMessage(err))
      })
    return () => {
      cancelled = true
    }
  }, [id])

  useEffect(() => {
    if (state?.phase === 'complete') navigate(`/results/${id}`, { replace: true })
  }, [state?.phase, id, navigate])

  if (error) {
    return (
      <section className="panel">
        <h1>Something went wrong</h1>
        <p className="error">{error}</p>
        <button onClick={() => window.location.reload()}>Try again</button>
      </section>
    )
  }
  if (!state) return <p className="muted">Loading…</p>

  return (
    <>
      <p className="phase-indicator">
        Phase: <span data-testid="phase-label">{state.phase}</span>
        {state.administration > 1 && <span className="muted"> · second administration</span>}
      </p>
      {state.phase === 'response' && <ResponsePhase state={state} onState={setState} />}
      {state.phase === 'inquiry' && (
        <InquiryPhase state={state} onReload={reload} onFinished={() => navigate(`/results/${id}`)} />
      )}
      {state.phase === 'complete' && <p className="muted">Loading your results…</p>}
    </>
  )
}
