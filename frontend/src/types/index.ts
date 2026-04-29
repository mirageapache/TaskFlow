/**
 * 共用 TypeScript 型別定義 — 對應後端 DRF Serializer 回傳結構。
 *
 * 規格：
 * - Workspace、Project 對應 apps/workspaces/serializers.py、apps/projects/serializers.py
 * - 後端列表 API 採 PageNumberPagination（PAGE_SIZE=20）
 */

export interface User {
  id: string
  email: string
  username: string
  avatar_url?: string | null
}

export interface Workspace {
  id: string
  name: string
  description: string
  avatar_url: string | null
  /** owner 為使用者 UUID */
  owner: string
  created_at: string
  updated_at: string
}

export interface Project {
  id: string
  /** workspace FK（UUID 字串） */
  workspace: string
  name: string
  description: string
  color: string
  created_at: string
  updated_at: string
}

/** DRF PageNumberPagination 包裝型別 */
export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
