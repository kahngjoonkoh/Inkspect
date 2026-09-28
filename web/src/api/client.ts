import type {
  AddResponseResult,
  AdminSession,
  CardInfo,
  CodeOverride,
  InquiryResult,
  NextResult,
  Orientation,
  Polygon,
  RegionMap,
  Response,
  Results,
  SessionState,
} from './types'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

const TOKEN_KEY = 'inkspect.adminToken'
const SESSION_KEY = 'inkspect.lastSession'

function storageGet(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null
  }
}

function storageSet(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value)
  } catch {
    // storage unavailable; ignore
  }
}

export const getAdminToken = (): string => storageGet(TOKEN_KEY) ?? ''
export const setAdminToken = (token: string): void => storageSet(TOKEN_KEY, token)
export const getLastSession = (): string | null => storageGet(SESSION_KEY)
export const setLastSession = (id: string): void => storageSet(SESSION_KEY, id)

async function request<T>(method: string, path: string, body?: unknown, admin = false): Promise<T> {
  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (admin) headers['X-Admin-Token'] = getAdminToken()
  const res = await fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const data: unknown = await res.json()
      if (data && typeof data === 'object' && 'detail' in data) {
        const d = (data as { detail: unknown }).detail
        detail = typeof d === 'string' ? d : JSON.stringify(d)
      }
    } catch {
      // non-JSON error body
    }
    throw new ApiError(res.status, detail || `HTTP ${res.status}`)
  }
  const type = res.headers.get('content-type') ?? ''
  if (type.includes('application/json')) return (await res.json()) as T
  return (await res.text()) as unknown as T
}

export const api = {
  cards: () => request<CardInfo[]>('GET', '/api/cards'),
  createSession: () => request<SessionState>('POST', '/api/sessions', { consent: true }),
  session: (id: string) => request<SessionState>('GET', `/api/sessions/${id}`),
  addResponse: (id: string, card: number, verbatim: string, orientation: Orientation, reactionMs: number | null) =>
    request<AddResponseResult>('POST', `/api/sessions/${id}/responses`, {
      card,
      verbatim,
      orientation,
      reaction_ms: reactionMs,
    }),
  deleteResponse: (id: string, rid: number) =>
    request<SessionState>('DELETE', `/api/sessions/${id}/responses/${rid}`),
  nextCard: (id: string, card: number) => request<NextResult>('POST', `/api/sessions/${id}/cards/${card}/next`, {}),
  saveInquiry: (rid: number, regions: Polygon[], wholeCard: boolean, explanation: string) =>
    request<InquiryResult>('PUT', `/api/responses/${rid}/inquiry`, {
      regions,
      whole_card: wholeCard,
      explanation,
    }),
  addFollowup: (rid: number, prompt: string, answer: string) =>
    request<InquiryResult>('POST', `/api/responses/${rid}/followups`, { prompt, answer }),
  inquiryDone: (rid: number) => request<{ response: Response }>('POST', `/api/responses/${rid}/inquiry/done`),
  finish: (id: string) => request<Results>('POST', `/api/sessions/${id}/finish`),
  results: (id: string) => request<Results>('GET', `/api/sessions/${id}/results`),
  regions: (card: number) => request<RegionMap>('GET', `/api/regions/${card}`),

  adminSessions: () => request<AdminSession[]>('GET', '/api/admin/sessions', undefined, true),
  adminSession: (id: string) => request<Results>('GET', `/api/admin/sessions/${id}`, undefined, true),
  overrideCodes: (rid: number, codes: CodeOverride) =>
    request<Results>('PUT', `/api/admin/responses/${rid}/codes`, codes, true),
  revertCodes: (rid: number) => request<Results>('DELETE', `/api/admin/responses/${rid}/codes`, undefined, true),
  saveRegions: (card: number, map: RegionMap) =>
    request<RegionMap>('PUT', `/api/admin/regions/${card}`, map, true),
  async trainingExport(): Promise<Blob> {
    const res = await fetch('/api/admin/export/training.jsonl', {
      headers: { 'X-Admin-Token': getAdminToken() },
    })
    if (!res.ok) throw new ApiError(res.status, `Export failed (HTTP ${res.status})`)
    return res.blob()
  },
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 401 || err.status === 403) return 'Admin token rejected.'
    return err.message
  }
  if (err instanceof Error) return err.message
  return String(err)
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
