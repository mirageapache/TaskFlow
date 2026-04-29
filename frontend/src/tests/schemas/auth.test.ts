/**
 * Zod Auth Schema 測試
 * 規格：.doc/taskflow-frontend.md §4.6
 *
 * 驗證 LoginSchema 與 RegisterSchema 的：
 * - 合法輸入通過
 * - 不合法輸入給出對應錯誤訊息（email 格式、密碼長度、確認密碼一致）
 */
import { describe, it, expect } from 'vitest'

import { LoginSchema, RegisterSchema } from '@/schemas/auth'

describe('LoginSchema', () => {
  it('合法輸入通過驗證', () => {
    const result = LoginSchema.safeParse({
      email: 'user@example.com',
      password: 'password123',
    })
    expect(result.success).toBe(true)
  })

  it('email 格式錯誤回傳對應訊息', () => {
    const result = LoginSchema.safeParse({
      email: 'not-an-email',
      password: 'password123',
    })
    expect(result.success).toBe(false)
    if (!result.success) {
      const emailIssue = result.error.issues.find((i) => i.path[0] === 'email')
      expect(emailIssue?.message).toBe('請輸入有效的 Email')
    }
  })

  it('密碼少於 8 字元回傳對應訊息', () => {
    const result = LoginSchema.safeParse({
      email: 'user@example.com',
      password: 'short',
    })
    expect(result.success).toBe(false)
    if (!result.success) {
      const pwIssue = result.error.issues.find((i) => i.path[0] === 'password')
      expect(pwIssue?.message).toBe('密碼至少 8 個字元')
    }
  })

  it('email 與 password 同時錯誤時兩個 issue 都會回傳', () => {
    const result = LoginSchema.safeParse({ email: '', password: '' })
    expect(result.success).toBe(false)
    if (!result.success) {
      const paths = result.error.issues.map((i) => i.path[0])
      expect(paths).toContain('email')
      expect(paths).toContain('password')
    }
  })
})

describe('RegisterSchema', () => {
  const valid = {
    email: 'new@example.com',
    username: 'newuser',
    password: 'StrongPwd1',
    confirmPassword: 'StrongPwd1',
  }

  it('合法輸入通過驗證', () => {
    const result = RegisterSchema.safeParse(valid)
    expect(result.success).toBe(true)
  })

  it('username 少於 3 字元回傳對應訊息', () => {
    const result = RegisterSchema.safeParse({ ...valid, username: 'ab' })
    expect(result.success).toBe(false)
    if (!result.success) {
      const issue = result.error.issues.find((i) => i.path[0] === 'username')
      expect(issue?.message).toBe('使用者名至少 3 個字元')
    }
  })

  it('username 超過 50 字元回傳錯誤', () => {
    const result = RegisterSchema.safeParse({ ...valid, username: 'a'.repeat(51) })
    expect(result.success).toBe(false)
  })

  it('password 不足 8 字元回傳對應訊息', () => {
    const result = RegisterSchema.safeParse({
      ...valid,
      password: 'short',
      confirmPassword: 'short',
    })
    expect(result.success).toBe(false)
    if (!result.success) {
      const issue = result.error.issues.find((i) => i.path[0] === 'password')
      expect(issue?.message).toBe('密碼至少 8 個字元')
    }
  })

  it('confirmPassword 不符 password 回傳「密碼不一致」於 confirmPassword 路徑', () => {
    const result = RegisterSchema.safeParse({
      ...valid,
      confirmPassword: 'DifferentPwd1',
    })
    expect(result.success).toBe(false)
    if (!result.success) {
      const issue = result.error.issues.find((i) => i.path[0] === 'confirmPassword')
      expect(issue?.message).toBe('密碼不一致')
    }
  })

  it('email 格式錯誤回傳對應訊息', () => {
    const result = RegisterSchema.safeParse({ ...valid, email: 'bad' })
    expect(result.success).toBe(false)
    if (!result.success) {
      const issue = result.error.issues.find((i) => i.path[0] === 'email')
      expect(issue?.message).toBe('請輸入有效的 Email')
    }
  })
})
