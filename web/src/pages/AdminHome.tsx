import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, downloadBlob, errorMessage, getAdminToken, setAdminToken } from '../api/client'
import type { AdminSession } from '../api/types'
import { roman } from '../cards'

export default function AdminHome() {
  const [token, setToken] = useState(getAdminToken())
  const [sessions, setSessions] = useState<AdminSession[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function load() {
    setAdminToken(token)
    setBusy(true)
    setError(null)
    try {
      setSessions(await api.adminSessions())
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  async function exportTraining() {
    setAdminToken(token)
    setError(null)
    try {
      downloadBlob(await api.trainingExport(), 'training.jsonl')
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <section className="panel wide">
      <h1>Examiner tools</h1>
      <form
        className="input-row"
        onSubmit={(e) => {
          e.preventDefault()
          void load()
        }}
      >
        <input
          type="password"
          placeholder="Admin token"
          value={token}
          onChange={(e) => setToken(e.target.value)}
          aria-label="Admin token"
        />
        <button className="primary" type="submit" disabled={busy}>
          Load sessions
        </button>
        <button type="button" onClick={exportTraining}>
          Download training.jsonl
        </button>
      </form>
      {error && <p className="error">{error}</p>}

      <section className="block">
        <h2>Region maps</h2>
        <p className="muted small">Draw and label the Exner location areas (W, D, Dd, S) for each card.</p>
        <div className="card-links">
          {Array.from({ length: 10 }, (_, i) => i + 1).map((c) => (
            <Link key={c} className="button secondary" to={`/admin/regions/${c}`} onClick={() => setAdminToken(token)}>
              Card {roman(c)}
            </Link>
          ))}
        </div>
      </section>

      {sessions && (
        <section className="block">
          <h2>Sessions</h2>
          {sessions.length === 0 ? (
            <p className="muted">No sessions yet.</p>
          ) : (
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Created</th>
                    <th>Phase</th>
                    <th>R</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {sessions.map((s) => (
                    <tr key={s.id}>
                      <td>{new Date(s.created_at).toLocaleString()}</td>
                      <td>{s.phase}</td>
                      <td>{s.total_responses}</td>
                      <td>
                        {s.phase === 'complete' ? (
                          <Link to={`/admin/review/${s.id}`}>Review</Link>
                        ) : (
                          <span className="muted">in progress</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </section>
  )
}
