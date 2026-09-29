import { useRef, useState } from 'react'

// Dragging less than this is treated as an accidental nudge and snaps back.
const DEAD_ZONE_DEG = 25

function pointerAngle(e: React.PointerEvent, el: Element): number {
  const r = el.getBoundingClientRect()
  return (Math.atan2(e.clientY - (r.top + r.height / 2), e.clientX - (r.left + r.width / 2)) * 180) / Math.PI
}

/**
 * Rotate an element by dragging around its centre; on release it snaps to the nearest quarter
 * turn. A click or a small drag never turns it. Returns the angle in degrees (a multiple of 90
 * when not dragging), whether a drag is in progress, and the handlers to spread on the element.
 */
export function useDragRotate(onSnap?: (quarterTurns: number) => void) {
  const [angle, setAngle] = useState(0)
  const [dragging, setDragging] = useState(false)
  const drag = useRef<{ start: number; last: number; angle: number } | null>(null)

  function snapTo(deg: number) {
    const snapped = Math.round(deg / 90) * 90
    setAngle(snapped)
    onSnap?.(snapped / 90)
  }

  const handlers = {
    onPointerDown(e: React.PointerEvent<HTMLElement>) {
      if (e.pointerType === 'mouse' && e.button !== 0) return
      e.currentTarget.setPointerCapture(e.pointerId)
      drag.current = { start: angle, last: pointerAngle(e, e.currentTarget), angle }
      setDragging(true)
    },
    onPointerMove(e: React.PointerEvent<HTMLElement>) {
      const d = drag.current
      if (!d) return
      const now = pointerAngle(e, e.currentTarget)
      let step = now - d.last
      if (step > 180) step -= 360
      if (step < -180) step += 360
      d.last = now
      d.angle += step
      setAngle(d.angle)
    },
    onPointerUp(e: React.PointerEvent<HTMLElement>) {
      const d = drag.current
      if (!d) return
      drag.current = null
      setDragging(false)
      if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId)
      snapTo(Math.abs(d.angle - d.start) < DEAD_ZONE_DEG ? d.start : d.angle)
    },
    onPointerCancel() {
      const d = drag.current
      drag.current = null
      setDragging(false)
      if (d) setAngle(d.start)
    },
    onKeyDown(e: React.KeyboardEvent<HTMLElement>) {
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        e.preventDefault()
        snapTo(angle + (e.key === 'ArrowRight' ? 90 : -90))
      }
    },
  }

  function reset() {
    drag.current = null
    setDragging(false)
    setAngle(0)
  }

  return { angle, dragging, handlers, reset }
}
