export type Orientation = '^' | '>' | 'v' | '<'
export type Point = [number, number]
export type Polygon = Point[]

export interface Location {
  code: 'W' | 'D' | 'Dd'
  number: number | null
  space: boolean
  label: string
  placeholder?: boolean
}

export interface Followup {
  prompt: string
  answer: string
}

export interface Inquiry {
  regions: Polygon[]
  whole_card: boolean
  explanation: string
  followups: Followup[]
  done: boolean
}

export interface Response {
  id: number
  card: number
  number: number
  verbatim: string
  orientation: Orientation
  reaction_ms: number | null
  inquiry: Inquiry
}

export type Phase = 'response' | 'inquiry' | 'complete'

export interface SessionState {
  id: string
  phase: Phase
  current_card: number
  administration: number
  total_responses: number
  responses: Response[]
  inquiry_index: number
}

export interface CardInfo {
  card: number
  image: string
  width: number
  height: number
  chromatic: boolean
}

export interface AddResponseResult {
  accepted: boolean
  response: Response | null
  message: string | null
  card_full: boolean
}

export type NextAction = 'stay' | 'next_card' | 'readminister' | 'inquiry'

export interface NextResult {
  action: NextAction
  message: string | null
  state: SessionState
}

export interface InquiryResult {
  followup: string | null
  response: Response
}

export type Validity = 'genuine' | 'unserious' | 'gibberish' | 'refusal' | 'off_task'

export interface Codes {
  dq: string
  determinants: string[]
  pair: boolean
  contents: string[]
  special_scores: string[]
  fq_fallback?: string | null
  validity?: Validity
  evidence?: Record<string, string>
  confidence?: Record<string, number>
  coder?: string
}

export interface ProtocolRow {
  response_id: number
  card: number
  card_roman: string
  number: number
  verbatim: string
  inquiry: string
  orientation: Orientation
  location: Location
  dq: string
  determinants: string[]
  fq: string | null
  pair: boolean
  contents: string[]
  popular: boolean
  z: number | null
  special_scores: string[]
  validity: Validity
  coder: string
  overridden: boolean
  score_line: string
  raw_codes?: Codes
  override?: (Partial<Codes> & { location_label?: string; fq?: string | null; note?: string }) | null
}

export interface SummaryItem {
  label: string
  value: string
}

export interface SummarySection {
  title: string
  items: SummaryItem[]
}

export interface Constellation {
  name: string
  value: number
  threshold: string
  positive: boolean
  conditions: { label: string; met: boolean }[]
}

export interface Summary {
  sections: SummarySection[]
  constellations: Constellation[]
}

export interface Interpretation {
  strategy: string
  key_variable: string
  clusters: { name: string; findings: string[] }[]
  caveats: string[]
}

export interface OverviewBand {
  key: string
  title: string
  level: 'lower' | 'typical' | 'higher'
  value: string
  unit: string
  typical: string
  text: string
}

export interface Overview {
  available: boolean
  message: string | null
  bands: OverviewBand[]
}

export interface Results {
  session_id: string
  valid: boolean
  warnings: string[]
  overview: Overview
  protocol: ProtocolRow[]
  summary: Summary
  interpretation: Interpretation
}

export interface AdminSession {
  id: string
  created_at: string
  phase: Phase
  total_responses: number
}

export type RegionKind = 'W' | 'D' | 'Dd' | 'S'

export interface Region {
  id: string
  kind: RegionKind
  polygons: Polygon[]
}

export interface RegionMap {
  card: number
  placeholder: boolean
  regions: Region[]
}

export interface CodeOverride {
  location_label?: string
  dq: string
  determinants: string[]
  pair: boolean
  contents: string[]
  special_scores: string[]
  validity: Validity
  fq?: string | null
  note?: string
}
