import type { ProtocolRow, Results } from '../api/types'
import Disclaimer from './Disclaimer'

export function ProtocolTable({ rows, renderExtra }: { rows: ProtocolRow[]; renderExtra?: (row: ProtocolRow) => React.ReactNode }) {
  return (
    <div className="table-scroll">
      <table className="protocol" data-testid="protocol-table">
        <thead>
          <tr>
            <th>Card</th>
            <th>#</th>
            <th>Response</th>
            <th>Loc</th>
            <th>DQ</th>
            <th>Det</th>
            <th>FQ</th>
            <th>(2)</th>
            <th>Cont</th>
            <th>P</th>
            <th>Z</th>
            <th>Special</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.response_id} className={r.overridden ? 'overridden' : undefined}>
              <td>
                {r.card_roman}
                {r.orientation !== '^' && <span className="muted"> {r.orientation}</span>}
              </td>
              <td>{r.number}</td>
              <td className="verbatim-cell">
                <div>{r.verbatim}</div>
                {r.inquiry && <div className="muted small">{r.inquiry}</div>}
                <code className="score-line">{r.score_line}</code>
                {renderExtra?.(r)}
              </td>
              <td>
                {r.location.label}
                {r.location.placeholder && <span className="muted" title="Placeholder region map">*</span>}
              </td>
              <td>{r.dq}</td>
              <td>{r.determinants.join('.')}</td>
              <td>{r.fq ?? ''}</td>
              <td>{r.pair ? '2' : ''}</td>
              <td>{r.contents.join(', ')}</td>
              <td>{r.popular ? 'P' : ''}</td>
              <td>{r.z ?? ''}</td>
              <td>{r.special_scores.join(', ')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function SummaryView({ results }: { results: Results }) {
  const { summary } = results
  return (
    <section className="block" data-testid="results-summary">
      <h2>Structural Summary</h2>
      <div className="summary-grid">
        {summary.sections.map((s) => (
          <div className="summary-section" key={s.title}>
            <h3>{s.title}</h3>
            <dl>
              {s.items.map((it) => (
                <div className="kv" key={it.label}>
                  <dt>{it.label}</dt>
                  <dd>{it.value}</dd>
                </div>
              ))}
            </dl>
          </div>
        ))}
      </div>
      {summary.constellations.length > 0 && (
        <>
          <h3>Constellations</h3>
          <div className="constellations">
            {summary.constellations.map((c) => (
              <details key={c.name} className={`constellation${c.positive ? ' positive' : ''}`}>
                <summary>
                  <strong>{c.name}</strong> = {c.value}{' '}
                  <span className="muted">(positive if {c.threshold})</span>{' '}
                  <span className={`badge${c.positive ? ' on' : ''}`}>{c.positive ? 'positive' : 'not positive'}</span>
                </summary>
                <ul className="conditions">
                  {c.conditions.map((cond, i) => (
                    <li key={i} className={cond.met ? 'met' : undefined}>
                      <span aria-hidden="true">{cond.met ? '●' : '○'}</span> {cond.label}
                    </li>
                  ))}
                </ul>
              </details>
            ))}
          </div>
        </>
      )}
    </section>
  )
}

export function InterpretationView({ results }: { results: Results }) {
  const { interpretation } = results
  return (
    <section className="block">
      <h2>Interpretation</h2>
      {interpretation.key_variable && (
        <p>
          <strong>Key variable:</strong> {interpretation.key_variable}
        </p>
      )}
      {interpretation.strategy && (
        <p>
          <strong>Search strategy:</strong> {interpretation.strategy}
        </p>
      )}
      {interpretation.clusters.map((c) => (
        <div key={c.name} className="cluster">
          <h3>{c.name}</h3>
          {c.findings.length === 0 ? (
            <p className="muted">No notable findings.</p>
          ) : (
            <ul>
              {c.findings.map((f, i) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
      {interpretation.caveats.length > 0 && (
        <div className="caveats">
          <h3>Caveats</h3>
          <ul>
            {interpretation.caveats.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

export function ResultsHeader({ results }: { results: Results }) {
  return (
    <>
      <Disclaimer />
      {!results.valid && (
        <p className="warning-banner">This record is not interpretively valid (for example, too few responses).</p>
      )}
      {results.warnings.length > 0 && (
        <ul className="warnings">
          {results.warnings.map((w, i) => (
            <li key={i}>{w}</li>
          ))}
        </ul>
      )}
    </>
  )
}
