import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, errorMessage } from '../api/client'
import type { CodeOverride, ProtocolRow, Results, Validity } from '../api/types'
import { InterpretationView, ProtocolTable, ResultsHeader, SummaryView } from '../components/ResultsView'

const DQ = ['+', 'o', 'v/+', 'v']
const FQ = ['', '+', 'o', 'u', '-']
const VALIDITY: Validity[] = ['genuine', 'unserious', 'gibberish', 'refusal', 'off_task']

const splitList = (s: string): string[] =>
  s
    .split(',')
    .map((x) => x.trim())
    .filter(Boolean)

export default function AdminReview() {
  const { id = '' } = useParams()
  const [results, setResults] = useState<Results | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    api
      .adminSession(id)
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

  if (error && !results) {
    return (
      <section className="panel">
        <h1>Review</h1>
        <p className="error">{error}</p>
        <Link to="/admin">Back to examiner tools</Link>
      </section>
    )
  }
  if (!results) return <p className="muted">Loading…</p>

  return (
    <section className="panel wide">
      <p>
        <Link to="/admin">← Examiner tools</Link>
      </p>
      <h1>Review protocol</h1>
      <ResultsHeader results={results} />
      {error && <p className="error">{error}</p>}
      <section className="block">
        <h2>Sequence of scores</h2>
        <ProtocolTable rows={results.protocol} />
      </section>
      <section className="block">
        <h2>Edit codes</h2>
        {results.protocol.map((row) => (
          <RowEditor
            key={`${row.response_id}-${row.score_line}`}
            row={row}
            onResults={(r) => {
              setError(null)
              setResults(r)
            }}
            onError={setError}
          />
        ))}
      </section>
      <SummaryView results={results} />
      <InterpretationView results={results} />
    </section>
  )
}

interface RowProps {
  row: ProtocolRow
  onResults: (r: Results) => void
  onError: (msg: string) => void
}

function RowEditor({ row, onResults, onError }: RowProps) {
  const [location, setLocation] = useState(row.location.label)
  const [dq, setDq] = useState(row.dq)
  const [determinants, setDeterminants] = useState(row.determinants.join(', '))
  const [fq, setFq] = useState(row.fq ?? '')
  const [pair, setPair] = useState(row.pair)
  const [contents, setContents] = useState(row.contents.join(', '))
  const [special, setSpecial] = useState(row.special_scores.join(', '))
  const [validity, setValidity] = useState<Validity>(row.validity)
  const [note, setNote] = useState(row.override?.note ?? '')
  const [busy, setBusy] = useState(false)

  async function save() {
    const body: CodeOverride = {
      location_label: location.trim() || undefined,
      dq,
      determinants: splitList(determinants),
      pair,
      contents: splitList(contents),
      special_scores: splitList(special),
      validity,
      fq: fq || null,
      note: note.trim() || undefined,
    }
    setBusy(true)
    try {
      onResults(await api.overrideCodes(row.response_id, body))
    } catch (err) {
      onError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  async function revert() {
    setBusy(true)
    try {
      onResults(await api.revertCodes(row.response_id))
    } catch (err) {
      onError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const raw = row.raw_codes
  return (
    <details className={`row-editor${row.overridden ? ' overridden' : ''}`}>
      <summary>
        <strong>
          {row.card_roman}.{row.number}
        </strong>{' '}
        {row.verbatim} — <code>{row.score_line}</code>
        {row.overridden && <span className="badge on">overridden</span>}
      </summary>
      {row.inquiry && <p className="muted small">Inquiry: {row.inquiry}</p>}
      <div className="form-grid">
        <label className="field">
          <span>Location</span>
          <input value={location} onChange={(e) => setLocation(e.target.value)} />
        </label>
        <label className="field">
          <span>DQ</span>
          <select value={dq} onChange={(e) => setDq(e.target.value)}>
            {DQ.map((d) => (
              <option key={d} value={d}>
                {d}
              </option>
            ))}
          </select>
        </label>
        <label className="field">
          <span>Determinants</span>
          <input value={determinants} onChange={(e) => setDeterminants(e.target.value)} placeholder="Ma, FC" />
        </label>
        <label className="field">
          <span>FQ</span>
          <select value={fq} onChange={(e) => setFq(e.target.value)}>
            {FQ.map((f) => (
              <option key={f} value={f}>
                {f || '(none)'}
              </option>
            ))}
          </select>
        </label>
        <label className="check inline">
          <input type="checkbox" checked={pair} onChange={(e) => setPair(e.target.checked)} /> Pair (2)
        </label>
        <label className="field">
          <span>Contents</span>
          <input value={contents} onChange={(e) => setContents(e.target.value)} placeholder="H, Cg" />
        </label>
        <label className="field">
          <span>Special scores</span>
          <input value={special} onChange={(e) => setSpecial(e.target.value)} placeholder="COP, MOR" />
        </label>
        <label className="field">
          <span>Validity</span>
          <select value={validity} onChange={(e) => setValidity(e.target.value as Validity)}>
            {VALIDITY.map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
        </label>
        <label className="field wide-field">
          <span>Note</span>
          <input value={note} onChange={(e) => setNote(e.target.value)} />
        </label>
      </div>
      <div className="actions">
        <button className="primary" onClick={save} disabled={busy}>
          Save override
        </button>
        {row.overridden && (
          <button onClick={revert} disabled={busy}>
            Revert to coder output
          </button>
        )}
      </div>
      {raw && (
        <div className="raw-codes">
          <p className="small">
            <strong>Coder ({raw.coder ?? row.coder}):</strong> DQ {raw.dq} · {raw.determinants.join('.')} ·{' '}
            {raw.pair ? '(2) · ' : ''}
            {raw.contents.join(', ')}
            {raw.special_scores.length > 0 && ` · ${raw.special_scores.join(', ')}`}
            {raw.fq_fallback && ` · FQ fallback ${raw.fq_fallback}`}
          </p>
          {raw.evidence && Object.keys(raw.evidence).length > 0 && (
            <table className="evidence">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Evidence</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(raw.evidence).map(([code, span]) => (
                  <tr key={code}>
                    <td>{code}</td>
                    <td>“{span}”</td>
                    <td>{raw.confidence?.[code] !== undefined ? raw.confidence[code].toFixed(2) : ''}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </details>
  )
}
