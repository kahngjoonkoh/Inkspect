import { useRef, useState } from 'react'
import type { Orientation, Point, Polygon } from '../api/types'
import { cardMeta, rotatedSize, rotationTransform } from '../cards'

export interface Overlay {
  id: string
  polygons: Polygon[]
  highlighted?: boolean
  kind?: string
}

interface Props {
  card: number
  orientation?: Orientation
  regions: Polygon[]
  onRegionDrawn?: (polygon: Polygon) => void
  overlays?: Overlay[]
  wholeCard?: boolean
  disabled?: boolean
  testId?: string
  label?: string
}

// Minimum distance (normalized units) between successive lasso points.
const MIN_STEP = 0.01

function toPoints(poly: Polygon, w: number, h: number): string {
  return poly.map(([x, y]) => `${(x * w).toFixed(1)},${(y * h).toFixed(1)}`).join(' ')
}

export default function LassoCanvas({
  card,
  orientation = '^',
  regions,
  onRegionDrawn,
  overlays = [],
  wholeCard = false,
  disabled = false,
  testId = 'card-canvas',
  label,
}: Props) {
  const meta = cardMeta(card)
  const { width: w, height: h } = meta
  const [vw, vh] = rotatedSize(orientation, w, h)
  const svgRef = useRef<SVGSVGElement>(null)
  const groupRef = useRef<SVGGElement>(null)
  const drawingRef = useRef<Point[] | null>(null)
  const [drawing, setDrawing] = useState<Point[] | null>(null)

  const interactive = !disabled && !!onRegionDrawn

  function toCard(e: React.PointerEvent): Point | null {
    const svg = svgRef.current
    const g = groupRef.current
    if (!svg || !g) return null
    const ctm = g.getScreenCTM()
    if (!ctm) return null
    const pt = svg.createSVGPoint()
    pt.x = e.clientX
    pt.y = e.clientY
    const p = pt.matrixTransform(ctm.inverse())
    const x = Math.min(1, Math.max(0, p.x / w))
    const y = Math.min(1, Math.max(0, p.y / h))
    return [Number(x.toFixed(4)), Number(y.toFixed(4))]
  }

  function onPointerDown(e: React.PointerEvent<SVGSVGElement>) {
    if (!interactive) return
    if (e.pointerType === 'mouse' && e.button !== 0) return
    const p = toCard(e)
    if (!p) return
    e.currentTarget.setPointerCapture(e.pointerId)
    e.preventDefault()
    drawingRef.current = [p]
    setDrawing([p])
  }

  function onPointerMove(e: React.PointerEvent<SVGSVGElement>) {
    const current = drawingRef.current
    if (!current) return
    const p = toCard(e)
    if (!p) return
    const last = current[current.length - 1]
    if (Math.hypot(p[0] - last[0], p[1] - last[1]) < MIN_STEP) return
    const next = [...current, p]
    drawingRef.current = next
    setDrawing(next)
  }

  function finish(e: React.PointerEvent<SVGSVGElement>) {
    const current = drawingRef.current
    if (!current) return
    drawingRef.current = null
    setDrawing(null)
    if (e.currentTarget.hasPointerCapture(e.pointerId)) e.currentTarget.releasePointerCapture(e.pointerId)
    if (current.length >= 3 && onRegionDrawn) onRegionDrawn(current)
  }

  return (
    <div className="canvas-wrap">
      <svg
        ref={svgRef}
        data-testid={testId}
        className={`lasso-canvas${interactive ? ' interactive' : ''}`}
        viewBox={`0 0 ${vw} ${vh}`}
        role="img"
        aria-label={label ?? `Card ${card}`}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={finish}
        onPointerCancel={finish}
      >
        <g ref={groupRef} transform={rotationTransform(orientation, w, h)}>
          <image href={meta.image} x={0} y={0} width={w} height={h} preserveAspectRatio="none" />
          {wholeCard && <rect className="whole-card" x={0} y={0} width={w} height={h} />}
          {overlays.map((o) =>
            o.polygons.map((poly, i) => (
              <polygon
                key={`${o.id}-${i}`}
                className={`overlay kind-${o.kind ?? 'x'}${o.highlighted ? ' highlighted' : ''}`}
                points={toPoints(poly, w, h)}
                vectorEffect="non-scaling-stroke"
              />
            )),
          )}
          {regions.map((poly, i) => (
            <polygon key={i} className="region" points={toPoints(poly, w, h)} vectorEffect="non-scaling-stroke" />
          ))}
          {drawing && drawing.length > 1 && (
            <polyline className="drawing" points={toPoints(drawing, w, h)} vectorEffect="non-scaling-stroke" />
          )}
        </g>
      </svg>
    </div>
  )
}
