/**
 * parseApiError 單元測試
 * 行為對應 DRF 常見錯誤回應形式。
 */
import { describe, it, expect } from 'vitest'

import { parseApiError } from '@/utils/api-errors'

function err(data: unknown) {
  const e = new Error('mock') as Error & { response?: unknown }
  e.response = { data }
  return e
}

describe('parseApiError', () => {
  it('non-axios error：banner 與 fieldErrors 都為空', () => {
    expect(parseApiError(new Error('plain'))).toEqual({ banner: null, fieldErrors: {} })
    expect(parseApiError(null)).toEqual({ banner: null, fieldErrors: {} })
    expect(parseApiError(undefined)).toEqual({ banner: null, fieldErrors: {} })
  })

  it('{ detail } → 放入 banner，fieldErrors 為空', () => {
    const r = parseApiError(err({ detail: '帳號或密碼錯誤' }))
    expect(r.banner).toBe('帳號或密碼錯誤')
    expect(r.fieldErrors).toEqual({})
  })

  it('{ non_field_errors } → 放入 banner', () => {
    const r = parseApiError(err({ non_field_errors: ['名稱已使用'] }))
    expect(r.banner).toBe('名稱已使用')
    expect(r.fieldErrors).toEqual({})
  })

  it('已知欄位驗證錯誤 → 放入 fieldErrors', () => {
    const r = parseApiError(
      err({ password: ['這個密碼太常見了。'] }),
      ['email', 'password', 'username'],
    )
    expect(r.banner).toBeNull()
    expect(r.fieldErrors).toEqual({ password: '這個密碼太常見了。' })
  })

  it('多欄位 + 多訊息：以「；」串接同欄位的多條訊息', () => {
    const r = parseApiError(
      err({
        email: ['Email 已存在'],
        password: ['至少 8 個字元', '不可為純數字'],
      }),
      ['email', 'password'],
    )
    expect(r.fieldErrors).toEqual({
      email: 'Email 已存在',
      password: '至少 8 個字元；不可為純數字',
    })
  })

  it('未知欄位：彙整到 banner，已知欄位仍進 fieldErrors', () => {
    const r = parseApiError(
      err({
        password: ['太短'],
        unknown_field: ['伺服器內部代碼'],
      }),
      ['password'],
    )
    expect(r.fieldErrors).toEqual({ password: '太短' })
    expect(r.banner).toBe('unknown_field: 伺服器內部代碼')
  })

  it('detail 優先於欄位錯誤（DRF 通常擇一回傳，但安全起見）', () => {
    const r = parseApiError(
      err({ detail: '不是此工作區成員', password: ['不該出現'] }),
      ['password'],
    )
    expect(r.banner).toBe('不是此工作區成員')
    expect(r.fieldErrors).toEqual({})
  })

  it('欄位值為單一字串（非陣列）也能解出', () => {
    const r = parseApiError(err({ email: 'Email 格式錯誤' }), ['email'])
    expect(r.fieldErrors).toEqual({ email: 'Email 格式錯誤' })
  })

  it('整段 body 是字串：放進 banner', () => {
    const r = parseApiError(err('Internal Server Error'))
    expect(r.banner).toBe('Internal Server Error')
  })

  it('沒有 known fields 時所有訊息都塞 banner', () => {
    const r = parseApiError(err({ password: ['太短'], email: ['格式錯誤'] }))
    expect(r.fieldErrors).toEqual({})
    // 兩條都應在 banner（順序可能不保證，但都要存在）
    expect(r.banner).toContain('password: 太短')
    expect(r.banner).toContain('email: 格式錯誤')
  })
})
