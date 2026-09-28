import type { Orientation } from './api/types'

export interface CardMeta {
  card: number
  image: string
  width: number
  height: number
  chromatic: boolean
}

// Pixel sizes of the images in public/cards (used for the SVG viewBox).
const SIZES: Record<number, [number, number]> = {
  1: [736, 482],
  2: [690, 493],
  3: [800, 550],
  4: [794, 536],
  5: [760, 555],
  6: [772, 570],
  7: [800, 547],
  8: [689, 600],
  9: [754, 699],
  10: [890, 711],
}

const CHROMATIC = new Set([2, 3, 8, 9, 10])

export function cardMeta(card: number): CardMeta {
  const [width, height] = SIZES[card] ?? [800, 550]
  return { card, image: `/cards/card_${card}.jpg`, width, height, chromatic: CHROMATIC.has(card) }
}

const ROMAN = ['', 'I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X']

export function roman(card: number): string {
  return ROMAN[card] ?? String(card)
}

export const ORIENTATIONS: Orientation[] = ['^', '>', 'v', '<']

export const ORIENTATION_LABEL: Record<Orientation, string> = {
  '^': 'Upright',
  '>': 'Turned right',
  v: 'Upside down',
  '<': 'Turned left',
}

export const ORIENTATION_DEGREES: Record<Orientation, number> = {
  '^': 0,
  '>': 90,
  v: 180,
  '<': 270,
}

/** SVG transform that draws a W×H image rotated into a viewBox of rotatedSize(). */
export function rotationTransform(o: Orientation, w: number, h: number): string {
  switch (o) {
    case '>':
      return `translate(${h} 0) rotate(90)`
    case 'v':
      return `translate(${w} ${h}) rotate(180)`
    case '<':
      return `translate(0 ${w}) rotate(-90)`
    default:
      return ''
  }
}

export function rotatedSize(o: Orientation, w: number, h: number): [number, number] {
  return o === '>' || o === '<' ? [h, w] : [w, h]
}
