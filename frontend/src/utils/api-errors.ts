/**
 * 解析後端（DRF）回傳的錯誤格式。
 *
 * DRF 常見回應：
 *   - `{ detail: "..." }`                     — 認證 / 權限 / 全局錯誤 → banner
 *   - `{ non_field_errors: ["..."] }`         — 物件層級驗證 → banner
 *   - `{ field_name: ["msg1", ...] }`         — 欄位層級驗證 → 對應欄位
 *   - `{ field_name: "msg" }`                 — 偶發單一字串 → 對應欄位
 *
 * `knownFields` 用於決定哪些 key 要顯示在欄位下；其他未匹配的 key
 * 全部彙整到 banner（避免 "non_field_errors" 之外的未知 key 被吞掉）。
 *
 * 配合 vee-validate 使用範例：
 *   const { banner, fieldErrors } = parseApiError(err, ['email', 'password'])
 *   for (const [field, msg] of Object.entries(fieldErrors)) setFieldError(field, msg)
 *   apiError.value = banner ?? (Object.keys(fieldErrors).length === 0 ? '...通用訊息' : null)
 */

export interface ApiErrorResult {
  /** 顯示在表單頂端的整體錯誤；若 null 表示沒有需要 banner 的訊息 */
  banner: string | null
  /** field name → 訊息（單條，多條以「；」串接） */
  fieldErrors: Record<string, string>
}

export function parseApiError(err: unknown, knownFields: string[] = []): ApiErrorResult {
  const result: ApiErrorResult = { banner: null, fieldErrors: {} }

  const data = extractResponseData(err)
  if (!data) return result

  // 字串型 body（罕見，例如反向代理直接 echo 文字）
  if (typeof data === 'string') {
    result.banner = data
    return result
  }

  if (typeof data !== 'object' || Array.isArray(data)) return result

  const dataObj = data as Record<string, unknown>

  // 1. detail / non_field_errors → banner
  if ('detail' in dataObj) {
    result.banner = toMessage(dataObj.detail)
    return result
  }
  if ('non_field_errors' in dataObj) {
    result.banner = toMessage(dataObj.non_field_errors)
    return result
  }

  // 2. 逐欄位拆解
  const knownSet = new Set(knownFields)
  const unmatched: string[] = []
  for (const [field, value] of Object.entries(dataObj)) {
    const msg = toMessage(value)
    if (!msg) continue
    if (knownSet.has(field)) {
      result.fieldErrors[field] = msg
    } else {
      unmatched.push(`${field}: ${msg}`)
    }
  }

  if (unmatched.length > 0) {
    result.banner = unmatched.join('；')
  }

  return result
}

function extractResponseData(err: unknown): unknown {
  if (!err || typeof err !== 'object') return null
  if (!('response' in err)) return null
  const r = (err as { response?: { data?: unknown } }).response
  return r?.data ?? null
}

function toMessage(value: unknown): string {
  if (value == null) return ''
  if (Array.isArray(value)) return value.map((v) => String(v)).filter(Boolean).join('；')
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  // object：盡力序列化（不應該常發生）
  try {
    return JSON.stringify(value)
  } catch {
    return ''
  }
}
