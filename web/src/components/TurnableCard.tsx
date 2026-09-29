import { useDragRotate } from './useDragRotate'

interface Props {
  image: string
  label: string
  onTurn: (quarterTurns: number) => void
}

/**
 * The card as the test taker holds it: drag around it to turn it, and it snaps to the nearest
 * quarter turn. As in the CS, turning is allowed but never suggested, so nothing says so.
 */
export default function TurnableCard({ image, label, onTurn }: Props) {
  const { angle, dragging, handlers } = useDragRotate(onTurn)
  return (
    <div
      className={`card-stage turnable${dragging ? ' dragging' : ''}`}
      data-testid="response-card"
      role="img"
      aria-label={label}
      tabIndex={0}
      {...handlers}
    >
      <img
        src={image}
        alt=""
        className="card-image"
        style={{ transform: `rotate(${angle}deg)`, transition: dragging ? 'none' : undefined }}
        draggable={false}
      />
    </div>
  )
}
