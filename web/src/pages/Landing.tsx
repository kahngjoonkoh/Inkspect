import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, errorMessage, getLastSession, setLastSession } from '../api/client'
import Disclaimer from '../components/Disclaimer'

export default function Landing() {
  const navigate = useNavigate()
  const [consent, setConsent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const last = getLastSession()

  async function start() {
    setBusy(true)
    setError(null)
    try {
      const s = await api.createSession()
      setLastSession(s.id)
      navigate(`/test/${s.id}`)
    } catch (err) {
      setError(errorMessage(err))
      setBusy(false)
    }
  }

  return (
    <section className="panel landing">
      <h1>The inkblot test</h1>
      <p className="lead">
        You'll see ten inkblots, one at a time. For each one, tell us what it might be — in your own words. There
        are no right or wrong answers.
      </p>
      <ol className="steps">
        <li>
          <strong>Responses.</strong> Look at each card and type everything it could be.
        </li>
        <li>
          <strong>Inquiry.</strong> We go back through your answers. For each one, draw around the part of the blot
          you meant and tell us what made it look that way.
        </li>
        <li>
          <strong>Results.</strong> Your answers are scored with the Exner Comprehensive System and summarised.
        </li>
      </ol>
      <p>Set aside about 30–45 minutes somewhere quiet. We don't ask for your name or any personal details.</p>
      <Disclaimer />
      <label className="check">
        <input
          type="checkbox"
          data-testid="consent-checkbox"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
        />
        I understand this is not a diagnosis, and I agree that my anonymous answers are stored for scoring.
      </label>
      <div className="actions">
        <button className="primary" data-testid="start-button" disabled={!consent || busy} onClick={start}>
          {busy ? 'Starting…' : 'Start the test'}
        </button>
        {last && (
          <Link to={`/test/${last}`} className="button secondary">
            Resume last session
          </Link>
        )}
      </div>
      {error && <p className="error">{error}</p>}
    </section>
  )
}
