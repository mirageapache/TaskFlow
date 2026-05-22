<template>
  <div data-test="attachment-uploader" class="space-y-2">
    <label
      class="inline-flex items-center gap-2 h-9 px-3 rounded-lg border border-stone-200 dark:border-stone-700 text-sm font-medium cursor-pointer hover:bg-stone-50 dark:hover:bg-stone-700"
      :class="{ 'opacity-60 cursor-not-allowed': uploading }"
    >
      <i v-if="uploading" class="pi pi-spinner pi-spin"></i>
      <i v-else class="pi pi-upload"></i>
      <span>{{ uploading ? '上傳中…' : '選擇檔案' }}</span>
      <input
        ref="inputEl"
        data-test="file-input"
        type="file"
        class="hidden"
        :disabled="uploading"
        :accept="ALLOWED_MIME_TYPES.join(',')"
        @change="onFileChange"
      />
    </label>

    <p
      v-if="errorMsg"
      data-test="upload-error"
      class="text-sm text-red-600 bg-red-50 dark:bg-red-950/30 px-3 py-2 rounded-md"
    >
      {{ errorMsg }}
    </p>
  </div>
</template>

<script setup lang="ts">
/**
 * AttachmentUploader — 任務附件上傳元件（Presigned URL 六步流程）。
 *
 * 規格：.doc/taskflow-backend.md §7.3
 *
 * 流程：
 *   1. POST /tasks/{taskId}/attachments/request-upload/ → { attachment_id, upload_url, fields }
 *   2. 將 fields 與 file 包入 FormData，POST 到 S3 upload_url（**用原生 fetch，避免帶 JWT**）
 *   3. PATCH /tasks/{taskId}/attachments/{attachment_id}/confirm/ → 完整 Attachment
 *   4. emit('uploaded', attachment) 通知父層更新列表
 *
 * 為何不用 axios client 上傳到 S3：
 *   `src/api/client.ts` 有 request interceptor 會在所有請求加 `Authorization: Bearer <JWT>`。
 *   把 JWT 送到 S3 不僅會被 S3 視為非法 header 拒收，也是憑證外洩。
 *
 * 前端會在送出前先檢查 MIME 與檔案大小（與後端 `tasks/serializers.py` 的白名單一致），
 * 但這只是 UX 上的早退；最終把關仍在後端。
 */
import { ref } from 'vue'

import client from '@/api/client'
import type { Attachment, RequestUploadResponse } from '@/types'

const props = defineProps<{ taskId: string }>()
const emit = defineEmits<{ (e: 'uploaded', attachment: Attachment): void }>()

// 與 backend/apps/tasks/serializers.py 的 ALLOWED_MIME_TYPES 對齊；新增類型時兩邊一起改
const ALLOWED_MIME_TYPES = [
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
  'application/pdf',
  'text/plain',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
]
const MAX_FILE_SIZE = 10 * 1024 * 1024

const inputEl = ref<HTMLInputElement | null>(null)
const uploading = ref(false)
const errorMsg = ref('')

async function onFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  errorMsg.value = ''

  if (file.size > MAX_FILE_SIZE) {
    errorMsg.value = `檔案過大，請選擇 10 MB 以下的檔案。`
    input.value = ''
    return
  }
  if (!ALLOWED_MIME_TYPES.includes(file.type)) {
    errorMsg.value = `不支援的檔案類型：${file.type || '未知'}`
    input.value = ''
    return
  }

  uploading.value = true
  try {
    // step 1：請後端產生 presigned POST
    const { data: presigned } = await client.post<RequestUploadResponse>(
      `/tasks/${props.taskId}/attachments/request-upload/`,
      {
        file_name: file.name,
        file_size: file.size,
        mime_type: file.type,
      },
    )

    // step 2：直傳 S3（用原生 fetch，避免被 axios interceptor 加 JWT）
    const form = new FormData()
    for (const [k, v] of Object.entries(presigned.fields)) {
      form.append(k, v)
    }
    form.append('file', file) // file 必須是 multipart 最後一欄（S3 限制）

    const s3Res = await fetch(presigned.upload_url, { method: 'POST', body: form })
    if (!s3Res.ok) {
      throw new Error(`S3 upload failed: ${s3Res.status}`)
    }

    // step 3：confirm，把 is_confirmed 翻牌
    const { data: attachment } = await client.patch<Attachment>(
      `/tasks/${props.taskId}/attachments/${presigned.attachment_id}/confirm/`,
    )

    emit('uploaded', attachment)
  } catch (err) {
    errorMsg.value = err instanceof Error ? `上傳失敗：${err.message}` : '上傳失敗'
  } finally {
    uploading.value = false
    if (inputEl.value) inputEl.value.value = ''
  }
}
</script>
