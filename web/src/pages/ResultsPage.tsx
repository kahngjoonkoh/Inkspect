import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, errorMessage } from '../api/client'
import type { Results } from '../api/types'
import { InterpretationView, OverviewView, ProtocolTable, ResultsHeader, SummaryView } from '../components/ResultsView'

type Tab = 'overview' | 'professional'
const TABS: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'professional', label: 'Professional' },
]

export default function ResultsPage() {
  const { id = '' } = useParams()
  const [results, setResults] = useState<Results | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>(() => (window.location.hash === '#professional' ? 'professional' : 'overview'))

  function choose(t: Tab) {
    setTab(t)
    window.history.replaceState(null, '', t === 'overview' ? window.location.pathname : '#professional')
  }

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
      <div className="tabs" role="tablist" aria-label="Results view">
        {TABS.map((t) => (
          <button
            key={t.id}
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={tab === t.id}
            aria-controls={`panel-${t.id}`}
            className={`tab${tab === t.id ? ' active' : ''}`}
            onClick={() => choose(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>
      {tab === 'overview' ? (
        <div role="tabpanel" id="panel-overview" aria-labelledby="tab-overview">
          <OverviewView results={results} />
        </div>
      ) : (
        <div role="tabpanel" id="panel-professional" aria-labelledby="tab-professional">
          <p className="muted">
            The full Exner Comprehensive System record: the scored responses, the structural summary and a
            rule-based interpretation, for readers who know the system.
          </p>
          <section className="block">
            <h2>Sequence of scores</h2>
            <ProtocolTable rows={results.protocol} />
          </section>
          <SummaryView results={results} />
          <InterpretationView results={results} />
        </div>
      )}
    </section>
  )
}
