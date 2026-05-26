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

export interface CalendarEvent {
  id: string
  /** workspace FK（UUID） */
  workspace: string
  /** creator UUID；後端帳號刪除走 SET_NULL，可能為 null */
  creator: string | null
  title: string
  description: string
  /** ISO 8601 datetime */
  start_at: string
  end_at: string
  is_all_day: boolean
  /** iCal RRULE 字串；空字串代表單次活動 */
  recurrence_rule: string
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

/**
 * 任務附件 metadata（對應後端 `TaskAttachmentSerializer`）。
 *
 * 上傳流程使用 Presigned URL 六步流程；`is_confirmed=false` 代表還未呼叫 confirm，
 * UI 應隱藏或顯示為「上傳中」。下載 URL 不在此處，必須另呼叫 download 端點取得 15 分鐘短期連結。
 */
export interface Attachment {
  id: string
  uploader: User | null
  file_name: string
  file_key: string
  file_size: number
  mime_type: string
  is_confirmed: boolean
  created_at: string
  updated_at: string
}

/**
 * `POST /tasks/{id}/attachments/request-upload/` 回應。
 *
 * `upload_url` + `fields` 是 boto3 `generate_presigned_post()` 產生的 S3 直傳組合；
 * 前端必須以 multipart/form-data POST 到 `upload_url`，欄位先放 `fields`，最後一欄放 `file`。
 * 此步驟不可帶 Authorization header（會被 S3 拒收），需用原生 fetch 而非帶 JWT 的 axios client。
 */
export interface RequestUploadResponse {
  attachment_id: string
  upload_url: string
  fields: Record<string, string>
}
