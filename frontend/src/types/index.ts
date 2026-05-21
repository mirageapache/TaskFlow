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

export type TaskPriority = 'urgent' | 'high' | 'medium' | 'low'

export interface Task {
  id: string
  /** project FK（UUID） */
  project: string
  parent_task: string | null
  /** 看板欄位 FK（UUID）— 寫入時用 status_id */
  status: string
  /** 建立者 UUID */
  creator: string
  title: string
  description: string
  priority: TaskPriority
  start_date: string | null
  due_date: string | null
  estimated_hours: number | null
  order: number
  assignees: User[]
  /** tag FK 陣列（UUID） */
  tags: string[]
  created_at: string
  updated_at: string
}

export interface ProjectStatus {
  id: string
  name: string
  color: string
  order: number
  is_completed: boolean
  created_at: string
  updated_at: string
}

export interface Tag {
  id: string
  name: string
  color: string
  created_at: string
  updated_at: string
}

export type NotificationType =
  | 'task_assigned'
  | 'task_comment'
  | 'task_status_changed'
  | 'mention'
  | 'workspace_invite'

export interface Notification {
  id: string
  /** recipient UUID（= 自己） */
  recipient: string
  notif_type: NotificationType
  title: string
  body: string
  payload: Record<string, unknown>
  is_read: boolean
  read_at: string | null
  created_at: string
}
