import { useEffect, useRef, useState } from 'react'
import { api, errorMessage } from '../api/client'
import type { NextResult, Orientation, SessionState } from '../api/types'
import { cardMeta, ORIENTATION_DEGREES, ORIENTATION_LABEL, ORIENTATIONS, roman } from '../cards'
import ExaminerMessage from './ExaminerMessage'

interface Props {
  state: SessionState
  onState: (s: SessionState) => void
}

export default function ResponsePhase({ state, onState }: Props) {
  const card = state.current_card
  const meta = cardMeta(card)
  const [orientation, setOrientation] = useState<Orientation>('^')
  const [text, setText] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [prominent, setProminent] = useState(false)
  const [busy, setBusy] = useState(false)
  const shownAt = useRef(0)
  const autoNext = useRef<number | null>(null)
  const [prevCard, setPrevCard] = useState(card)

  // Reset per-card UI state when the card changes.
  if (prevCard !== card) {
    setPrevCard(card)
    setOrientation('^')
    setText('')
  }

  useEffect(() => {
    shownAt.current = performance.now()
  }, [card, state.administration])

  useEffect(
    () => () => {
      if (autoNext.current !== null) window.clearTimeout(autoNext.current)
    },
    [],
  )

  const cardResponses = state.responses.filter((r) => r.card === card)

  function applyNext(result: NextResult) {
    onState(result.state)
    setMessage(result.message)
    setProminent(result.action === 'readminister')
  }

  async function goNext() {
    if (autoNext.current !== null) {
      window.clearTimeout(autoNext.current)
      autoNext.current = null
    }
    setBusy(true)
    try {
      applyNext(await api.nextCard(state.id, card))
    } catch (err) {
      setMessage(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  async function add() {
    const verbatim = text.trim()
    if (!verbatim || busy) return
    setBusy(true)
    try {
      const reaction = Math.round(performance.now() - shownAt.current)
      const res = await api.addResponse(state.id, card, verbatim, orientation, reaction)
      setMessage(res.message)
      setProminent(false)
      if (res.accepted && res.response) {
        setText('')
        const response = res.response
        onState({
          ...state,
          responses: [...state.responses, response],
          total_responses: state.total_responses + 1,
        })
      }
      if (res.card_full) {
        autoNext.current = window.setTimeout(() => {
          autoNext.current = null
          void goNext()
        }, 1500)
      }
    } catch (err) {
      setMessage(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  async function remove(rid: number) {
    setBusy(true)
    try {
      onState(await api.deleteResponse(state.id, rid))
    } catch (err) {
      setMessage(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const cardFull = cardResponses.length >= 5

  return (
    <section className="panel test">
      <div className="card-head">
        <h1>
          Card {roman(card)} <span className="muted small">of X</span>
        </h1>
        <span className="sr-only" data-testid="card-number">
          {card}
        </span>
      </div>
      <p className="prompt">What might this be?</p>
      <div className="card-stage">
        <img
          src={meta.image}
          alt={`Inkblot card ${roman(card)}`}
          className="card-image"
          style={{ transform: `rotate(${ORIENTATION_DEGREES[orientation]}deg)` }}
          draggable={false}
        />
      </div>
      <div className="rotate-row" role="group" aria-label="Turn the card">
        {ORIENTATIONS.map((o) => (
          <button
            key={o}
            className={`chip${orientation === o ? ' active' : ''}`}
            aria-pressed={orientation === o}
            onClick={() => setOrientation(o)}
            title={ORIENTATION_LABEL[o]}
          >
            <span aria-hidden="true" style={{ display: 'inline-block', transform: `rotate(${ORIENTATION_DEGREES[o]}deg)` }}>
              ↑
            </span>{' '}
            {ORIENTATION_LABEL[o]}
          </button>
        ))}
      </div>

      <ExaminerMessage message={message} prominent={prominent} />

      <div className="input-row">
        <textarea
          data-testid="response-input"
          value={text}
          rows={2}
          placeholder="It looks like…"
          disabled={cardFull}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void add()
            }
          }}
        />
        <button data-testid="add-response" onClick={add} disabled={busy || cardFull || !text.trim()}>
          Add
        </button>
      </div>

      {cardResponses.length > 0 && (
        <ul className="response-list">
          {cardResponses.map((r) => (
            <li key={r.id}>
              <span className="orientation-tag" title={ORIENTATION_LABEL[r.orientation]}>
                {r.orientation}
              </span>
              <span className="verbatim">{r.verbatim}</span>
              <button className="link" onClick={() => remove(r.id)} disabled={busy} aria-label={`Remove “${r.verbatim}”`}>
                Remove
              </button>
            </li>
          ))}
        </ul>
      )}

      <div className="actions end">
        <button className="primary" data-testid="next-card" onClick={goNext} disabled={busy}>
          {card === 10 ? 'Finish cards' : 'Next card'}
        </button>
      </div>
    </section>
  )
}
