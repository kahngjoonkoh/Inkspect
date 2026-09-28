import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, errorMessage } from '../api/client'
import type { Results } from '../api/types'
import { InterpretationView, ProtocolTable, ResultsHeader, SummaryView } from '../components/ResultsView'

export default function ResultsPage() {
  const { id = '' } = useParams()
  const [results, setResults] = useState<Results | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .results(id)
      .then((r) => {
        if (!cancelled) setResults(r)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(errorMessage(err))
      })
    return () => {
      cancelled = true
    }
  }, [id])

  if (error) {
    return (
      <section className="panel">
        <h1>Results unavailable</h1>
        <p className="error">{error}</p>
        <Link to={`/test/${id}`}>Back to the test</Link>
      </section>
    )
  }
  if (!results) return <p className="muted">Loading results…</p>

  return (
    <section className="panel wide results">
      <h1>Your results</h1>
      <ResultsHeader results={results} />
      <section className="block">
        <h2>Sequence of scores</h2>
        <ProtocolTable rows={results.protocol} />
      </section>
      <SummaryView results={results} />
      <InterpretationView results={results} />
    </section>
  )
}
