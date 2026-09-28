import { useState } from 'react'
import { api, errorMessage } from '../api/client'
import type { Polygon, Response, SessionState } from '../api/types'
import { ORIENTATION_LABEL, roman } from '../cards'
import ExaminerMessage from './ExaminerMessage'
import LassoCanvas from './LassoCanvas'

interface Props {
  state: SessionState
  onReload: () => Promise<void>
  onFinished: () => void
}

export default function InquiryPhase({ state, onReload, onFinished }: Props) {
  const [finishing, setFinishing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const pending = state.responses.filter((r) => !r.inquiry.done)
  const index = Math.min(state.inquiry_index, state.responses.length)
  const current: Response | undefined = state.responses[index] && !state.responses[index].inquiry.done
    ? state.responses[index]
    : pending[0]

  async function finish() {
    setFinishing(true)
    setError(null)
    try {
      await api.finish(state.id)
      onFinished()
    } catch (err) {
      setError(errorMessage(err))
      setFinishing(false)
    }
  }

  async function stepDone() {
    const remaining = state.responses.filter((r) => !r.inquiry.done && r.id !== current?.id)
    if (remaining.length === 0) {
      await finish()
    } else {
      await onReload()
    }
  }

  if (!current) {
    return (
      <section className="panel">
        <h1>Scoring your answers</h1>
        {error ? (
          <>
            <p className="error">{error}</p>
            <button className="primary" onClick={finish} disabled={finishing}>
              Try again
            </button>
          </>
        ) : (
          <>
            <p className="muted">All answers are done.</p>
            <button className="primary" onClick={finish} disabled={finishing}>
              {finishing ? 'Scoring…' : 'See results'}
            </button>
          </>
        )}
      </section>
    )
  }

  const doneCount = state.responses.length - pending.length
  return (
    <>
      <p className="muted progress">
        Answer {doneCount + 1} of {state.responses.length}
      </p>
      <InquiryStep key={current.id} response={current} onDone={stepDone} />
      {finishing && <p className="muted">Scoring your answers…</p>}
      {error && <p className="error">{error}</p>}
    </>
  )
}

interface StepProps {
  response: Response
  onDone: () => Promise<void>
}

function InquiryStep({ response, onDone }: StepProps) {
  const [regions, setRegions] = useState<Polygon[]>(response.inquiry.regions ?? [])
  const [wholeCard, setWholeCard] = useState(response.inquiry.whole_card ?? false)
  const [explanation, setExplanation] = useState(response.inquiry.explanation ?? '')
  const [followup, setFollowup] = useState<string | null>(null)
  const [answer, setAnswer] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const canSubmit = (regions.length > 0 || wholeCard) && explanation.trim().length > 0 && !busy

  async function markDone() {
    await api.inquiryDone(response.id)
    await onDone()
  }

  async function submit() {
    if (!canSubmit) {
      setError(
        regions.length === 0 && !wholeCard
          ? 'Draw around the part of the card you meant, or choose “The whole card”.'
          : 'Tell us what makes it look like that.',
      )
      return
    }
    setBusy(true)
    setError(null)
    try {
      const res = await api.saveInquiry(response.id, regions, wholeCard, explanation.trim())
      if (res.followup) {
        setFollowup(res.followup)
      } else {
        await markDone()
      }
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  async function submitFollowup() {
    if (!followup || !answer.trim()) return
    setBusy(true)
    setError(null)
    try {
      const res = await api.addFollowup(response.id, followup, answer.trim())
      setAnswer('')
      if (res.followup) {
        setFollowup(res.followup)
      } else {
        setFollowup(null)
        await markDone()
      }
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const locked = followup !== null

  return (
    <section className="panel test">
      <div className="card-head">
        <h1>
          Card {roman(response.card)} — you said: <q>{response.verbatim}</q>
        </h1>
        <span className="sr-only" data-testid="card-number">
          {response.card}
        </span>
      </div>
      {response.orientation !== '^' && (
        <p className="muted small">You saw this with the card {ORIENTATION_LABEL[response.orientation].toLowerCase()}.</p>
      )}
      <p className="prompt">Draw around the part of the blot where you saw it. You can draw more than one area.</p>
      <LassoCanvas
        card={response.card}
        orientation={response.orientation}
        regions={regions}
        wholeCard={wholeCard}
        disabled={locked || busy}
        onRegionDrawn={(poly) => {
          setRegions((prev) => [...prev, poly])
          setError(null)
        }}
        label={`Card ${roman(response.card)} — draw the area you meant`}
      />
      <div className="tool-row">
        <label className="check inline">
          <input
            type="checkbox"
            data-testid="whole-card-toggle"
            checked={wholeCard}
            disabled={locked}
            onChange={(e) => setWholeCard(e.target.checked)}
          />
          The whole card
        </label>
        <button
          data-testid="undo-region"
          onClick={() => setRegions((prev) => prev.slice(0, -1))}
          disabled={locked || regions.length === 0}
        >
          Undo
        </button>
        <button data-testid="clear-regions" onClick={() => setRegions([])} disabled={locked || regions.length === 0}>
          Clear
        </button>
        <span className="muted small">
          {regions.length} area{regions.length === 1 ? '' : 's'} drawn
        </span>
      </div>

      <label className="field">
        <span>What makes it look like that?</span>
        <textarea
          data-testid="inquiry-explanation"
          rows={3}
          value={explanation}
          disabled={locked}
          onChange={(e) => setExplanation(e.target.value)}
        />
      </label>

      {!locked && (
        <div className="actions end">
          <button className="primary" data-testid="submit-inquiry" onClick={submit} disabled={busy}>
            {busy ? 'Saving…' : 'Continue'}
          </button>
        </div>
      )}

      {locked && (
        <div className="followup">
          <ExaminerMessage message={followup} />
          <div className="input-row">
            <textarea
              data-testid="followup-answer"
              rows={2}
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  void submitFollowup()
                }
              }}
            />
            <button className="primary" data-testid="submit-followup" onClick={submitFollowup} disabled={busy || !answer.trim()}>
              Answer
            </button>
          </div>
        </div>
      )}
      {error && <p className="error">{error}</p>}
    </section>
  )
}
