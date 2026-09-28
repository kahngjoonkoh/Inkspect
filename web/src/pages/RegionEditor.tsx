import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, downloadBlob, errorMessage } from '../api/client'
import type { Region, RegionKind, RegionMap } from '../api/types'
import LassoCanvas from '../components/LassoCanvas'
import { roman } from '../cards'

const KINDS: RegionKind[] = ['W', 'D', 'Dd', 'S']

export default function RegionEditor() {
  const { card: cardParam = '1' } = useParams()
  const card = Math.min(10, Math.max(1, Number(cardParam) || 1))
  const [map, setMap] = useState<RegionMap | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [newId, setNewId] = useState('')
  const [newKind, setNewKind] = useState<RegionKind>('D')
  const [showAll, setShowAll] = useState(true)
  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    let cancelled = false
    api
      .regions(card)
      .then((m) => {
        if (cancelled) return
        setMap(m)
        setSelected(null)
        setDirty(false)
        setError(null)
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(errorMessage(err))
      })
    return () => {
      cancelled = true
    }
  }, [card])

  function update(fn: (regions: Region[]) => Region[]) {
    setMap((m) => (m ? { ...m, regions: fn(m.regions) } : m))
    setDirty(true)
    setStatus(null)
  }

  function addRegion() {
    const id = newId.trim()
    if (!id || !map) return
    if (map.regions.some((r) => r.id === id)) {
      setError(`Region ${id} already exists.`)
      return
    }
    if (newKind === 'W' && map.regions.some((r) => r.kind === 'W')) {
      setError('There can be only one W region.')
      return
    }
    setError(null)
    update((rs) => [...rs, { id, kind: newKind, polygons: [] }])
    setSelected(id)
    setNewId('')
  }

  async function save() {
    if (!map) return
    setError(null)
    try {
      const saved = await api.saveRegions(card, map)
      setMap(saved)
      setDirty(false)
      setStatus('Saved.')
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  function download() {
    if (!map) return
    downloadBlob(new Blob([JSON.stringify(map, null, 2) + '\n'], { type: 'application/json' }), `card_${card}.json`)
  }

  if (!map) {
    return (
      <section className="panel">
        <h1>Card {roman(card)} regions</h1>
        {error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>}
      </section>
    )
  }

  const sel = map.regions.find((r) => r.id === selected) ?? null
  const overlays = map.regions
    .filter((r) => showAll || r.id === selected)
    .map((r) => ({ id: r.id, kind: r.kind, polygons: r.polygons, highlighted: r.id === selected }))

  return (
    <section className="panel wide">
      <p>
        <Link to="/admin">← Examiner tools</Link>
      </p>
      <h1>Card {roman(card)} regions</h1>
      <nav className="card-links">
        {Array.from({ length: 10 }, (_, i) => i + 1).map((c) => (
          <Link key={c} className={`chip${c === card ? ' active' : ''}`} to={`/admin/regions/${c}`}>
            {roman(c)}
          </Link>
        ))}
      </nav>
      {map.placeholder && (
        <p className="warning-banner">
          This map is a placeholder generated from the image. Replace it with the real Exner location areas.
        </p>
      )}
      <div className="editor-layout">
        <div>
          <LassoCanvas
            card={card}
            regions={[]}
            overlays={overlays}
            disabled={!sel}
            onRegionDrawn={(poly) => {
              if (!sel) return
              update((rs) => rs.map((r) => (r.id === sel.id ? { ...r, polygons: [...r.polygons, poly] } : r)))
            }}
            testId="region-canvas"
          />
          <p className="muted small">
            {sel ? `Drawing adds a polygon to ${sel.id}.` : 'Select or create a region, then draw on the card.'}
          </p>
        </div>
        <aside className="region-panel">
          <label className="check inline">
            <input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} /> Show all regions
          </label>
          <label className="check inline">
            <input
              type="checkbox"
              checked={map.placeholder}
              onChange={(e) => {
                const placeholder = e.target.checked
                setMap((m) => (m ? { ...m, placeholder } : m))
                setDirty(true)
              }}
            />{' '}
            Placeholder map
          </label>
          <ul className="region-list">
            {map.regions.map((r) => (
              <li key={r.id} className={r.id === selected ? 'selected' : undefined}>
                <button className="link" onClick={() => setSelected(r.id === selected ? null : r.id)}>
                  <span className={`swatch kind-${r.kind}`} /> {r.id}
                </button>
                <span className="muted small">
                  {r.kind} · {r.polygons.length} polygon{r.polygons.length === 1 ? '' : 's'}
                </span>
                <button
                  className="link danger"
                  onClick={() => {
                    update((rs) => rs.filter((x) => x.id !== r.id))
                    if (selected === r.id) setSelected(null)
                  }}
                >
                  Delete
                </button>
              </li>
            ))}
          </ul>
          {sel && sel.polygons.length > 0 && (
            <div>
              <h3>{sel.id} polygons</h3>
              <ul className="region-list">
                {sel.polygons.map((p, i) => (
                  <li key={i}>
                    Polygon {i + 1} <span className="muted small">({p.length} points)</span>
                    <button
                      className="link danger"
                      onClick={() =>
                        update((rs) =>
                          rs.map((r) => (r.id === sel.id ? { ...r, polygons: r.polygons.filter((_, j) => j !== i) } : r)),
                        )
                      }
                    >
                      Delete
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <form
            className="new-region"
            onSubmit={(e) => {
              e.preventDefault()
              addRegion()
            }}
          >
            <h3>New region</h3>
            <input placeholder="ID, e.g. D3 or DdS24" value={newId} onChange={(e) => setNewId(e.target.value)} />
            <select value={newKind} onChange={(e) => setNewKind(e.target.value as RegionKind)}>
              {KINDS.map((k) => (
                <option key={k} value={k}>
                  {k}
                </option>
              ))}
            </select>
            <button type="submit">Add</button>
          </form>
          <div className="actions">
            <button className="primary" onClick={save} disabled={!dirty}>
              Save
            </button>
            <button onClick={download}>Download JSON</button>
          </div>
          {status && <p className="muted">{status}</p>}
          {error && <p className="error">{error}</p>}
        </aside>
      </div>
    </section>
  )
}
