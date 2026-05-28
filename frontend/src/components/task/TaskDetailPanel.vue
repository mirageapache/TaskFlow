<template>
  <!-- Header -->
  <header
    class="px-6 py-4 border-b border-stone-200 dark:border-stone-700 flex items-start gap-3"
  >
    <input
      v-model="form.title"
      data-test="title-input"
      type="text"
      class="flex-1 text-xl font-semibold tracking-tight bg-transparent border-0 focus:outline-none focus:ring-2 focus:ring-orange-500/25 rounded text-stone-900 dark:text-stone-50"
    />
    <button
      data-test="close-btn"
      class="p-2 rounded-lg text-stone-500 hover:bg-stone-100 dark:hover:bg-stone-700"
      aria-label="關閉"
      @click="emit('close')"
    >
      <i class="pi pi-times"></i>
    </button>
  </header>

  <!-- 屬性區 -->
  <section
    class="px-6 py-4 border-b border-stone-200 dark:border-stone-700 grid grid-cols-2 gap-4 text-sm"
  >
    <div>
      <label class="block text-xs font-medium text-stone-500 mb-1">優先級</label>
      <select
        v-model="form.priority"
        data-test="priority-select"
        class="w-full h-9 px-2 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 focus:outline-none focus:border-orange-500 focus:ring-[3px] focus:ring-orange-500/25"
      >
        <option value="urgent">緊急</option>
        <option value="high">高</option>
        <option value="medium">中</option>
        <option value="low">低</option>
      </select>
    </div>
    <div>
      <label class="block text-xs font-medium text-stone-500 mb-1">截止日</label>
      <input
        v-model="form.due_date"
        type="date"
        class="w-full h-9 px-2 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 focus:outline-none focus:border-orange-500 focus:ring-[3px] focus:ring-orange-500/25"
      />
    </div>
  </section>

  <!-- Tabs -->
  <nav class="px-6 border-b border-stone-200 dark:border-stone-700 flex gap-4">
    <button
      v-for="t in tabs"
      :key="t.key"
      :data-test="`tab-btn-${t.key}`"
      class="py-3 text-sm font-medium border-b-2 -mb-[1px] transition-colors"
      :class="
        activeTab === t.key
          ? 'border-orange-500 text-orange-600'
          : 'border-transparent text-stone-500 hover:text-stone-700 dark:hover:text-stone-200'
      "
      @click="onTabClick(t.key)"
    >
      {{ t.label }}
    </button>
  </nav>

  <!-- Tab 內容 -->
  <div class="flex-1 overflow-y-auto px-6 py-4">
    <!-- 描述 -->
    <div v-if="activeTab === 'description'" data-test="tab-description">
      <textarea
        v-model="form.description"
        rows="10"
        placeholder="任務描述…"
        class="w-full px-3 py-2 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 text-sm focus:outline-none focus:border-orange-500 focus:ring-[3px] focus:ring-orange-500/25"
      ></textarea>
    </div>

    <!-- 留言 -->
    <div v-else-if="activeTab === 'comments'" data-test="tab-comments">
      <form
        data-test="comment-form"
        class="flex gap-2 items-start"
        @submit.prevent="onSubmitComment"
      >
        <textarea
          v-model="newComment"
          data-test="comment-input"
          rows="2"
          placeholder="新增留言…"
          class="flex-1 px-3 py-2 rounded-lg border border-stone-200 dark:border-stone-700 bg-white dark:bg-stone-900 text-sm focus:outline-none focus:border-orange-500 focus:ring-[3px] focus:ring-orange-500/25"
        ></textarea>
        <button
          type="submit"
          :disabled="!newComment.trim() || submittingComment"
          class="h-9 px-3 rounded-lg bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium disabled:opacity-60"
        >
          送出
        </button>
      </form>
      <ul class="mt-4 space-y-3">
        <li
          v-for="c in comments"
          :key="c.id"
          class="p-3 rounded-lg border border-stone-200 dark:border-stone-700 bg-stone-50 dark:bg-stone-900/50"
        >
          <div class="flex items-center gap-2 text-xs text-stone-500">
            <span class="font-medium text-stone-800 dark:text-stone-100">
              {{ c.author.username }}
            </span>
            <span>{{ formatDate(c.created_at) }}</span>
          </div>
          <p class="mt-1 text-sm whitespace-pre-wrap">{{ c.content }}</p>
        </li>
        <li
          v-if="!loadingComments && comments.length === 0"
          class="text-sm text-stone-500 text-center py-4"
        >
          尚無留言
        </li>
      </ul>
    </div>

    <!-- 附件 -->
    <div v-else-if="activeTab === 'attachments'" data-test="tab-attachments">
      <AttachmentUploader :task-id="task.id" class="mb-3" @uploaded="onAttachmentUploaded" />
      <ul v-if="attachments.length > 0" class="space-y-2">
        <li
          v-for="a in attachments"
          :key="a.id"
          class="p-3 rounded-lg border border-stone-200 dark:border-stone-700 flex items-center gap-3"
        >
          <i class="pi pi-file text-stone-500"></i>
          <div class="flex-1 min-w-0">
            <div class="text-sm font-medium truncate">{{ a.file_name }}</div>
            <div class="text-xs text-stone-500">
              {{ formatBytes(a.file_size) }} · {{ a.uploaded_by?.username }}
            </div>
          </div>
        </li>
      </ul>
      <p v-else-if="!loadingAttachments" class="text-sm text-stone-500 text-center py-4">
        尚無附件
      </p>
      <p v-if="loadingAttachments" class="text-sm text-stone-500 text-center py-4">
        <i class="pi pi-spinner pi-spin"></i> 載入中…
      </p>
    </div>

    <!-- 子任務 -->
    <div v-else-if="activeTab === 'subtasks'" data-test="tab-subtasks">
      <ul v-if="subtasks.length > 0" class="space-y-2">
        <li
          v-for="s in subtasks"
          :key="s.id"
          class="p-3 rounded-lg border border-stone-200 dark:border-stone-700 flex items-center gap-2 text-sm"
        >
          <span
            class="w-2 h-2 rounded-full"
            :class="priorityColor(s.priority)"
          ></span>
          <span class="flex-1 truncate">{{ s.title }}</span>
        </li>
      </ul>
      <p v-else class="text-sm text-stone-500 text-center py-4">尚無子任務</p>
    </div>
  </div>

  <!-- Footer 動作列 -->
  <footer
    class="px-6 py-3 border-t border-stone-200 dark:border-stone-700 flex justify-between gap-2"
  >
    <button
      data-test="delete-btn"
      class="h-9 px-3 rounded-lg text-red-600 hover:bg-red-50 dark:hover:bg-red-950/40 text-sm font-medium"
      @click="onDelete"
    >
      <i class="pi pi-trash mr-1"></i>刪除
    </button>
    <div class="flex gap-2">
      <button
        class="h-9 px-3 rounded-lg border border-stone-200 dark:border-stone-700 text-stone-800 dark:text-stone-100 text-sm font-medium hover:bg-stone-100 dark:hover:bg-stone-700"
        @click="emit('close')"
      >
        關閉
      </button>
      <button
        data-test="save-btn"
        :disabled="saving"
        class="h-9 px-4 rounded-lg bg-orange-500 hover:bg-orange-600 text-white text-sm font-medium inline-flex items-center gap-2 disabled:opacity-60"
        @click="onSave"
      >
        <i v-if="saving" class="pi pi-spinner pi-spin"></i>
        <span>儲存</span>
      </button>
    </div>
  </footer>
</template>

<script setup lang="ts">
/**
 * TaskDetailPanel — 任務詳情面板（純內容，不含容器外殼）。
 *
 * 設計為可嵌入任意容器（抽屜、彈窗等），容器負責決定尺寸與動畫。
 *
 * Props:
 *   - task: Task — 要顯示與編輯的任務
 *
 * Emits:
 *   - close()   — 請求容器關閉
 *   - deleted() — 任務刪除後通知父層
 */
import { computed, reactive, ref, watch } from 'vue'
import dayjs from 'dayjs'

import client from '@/api/client'
import { useTaskStore } from '@/stores/task'
import type { Attachment as AttachmentDTO, Task, TaskPriority, User } from '@/types'
import AttachmentUploader from '@/components/task/AttachmentUploader.vue'

const props = defineProps<{ task: Task }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'deleted'): void }>()

const taskStore = useTaskStore()

type TabKey = 'description' | 'comments' | 'attachments' | 'subtasks'
const tabs: { key: TabKey; label: string }[] = [
  { key: 'description', label: '描述' },
  { key: 'comments', label: '留言' },
  { key: 'attachments', label: '附件' },
  { key: 'subtasks', label: '子任務' },
]
const activeTab = ref<TabKey>('description')

interface Comment {
  id: string
  author: User
  content: string
  created_at: string
  updated_at: string
}
interface Attachment {
  id: string
  file_name: string
  file_size: number
  mime_type: string
  uploaded_by?: User | null
  created_at: string
}

const form = reactive({
  title: props.task.title,
  description: props.task.description,
  priority: props.task.priority,
  due_date: toDateInput(props.task.due_date),
})

watch(
  () => props.task,
  (t) => {
    form.title = t.title
    form.description = t.description
    form.priority = t.priority
    form.due_date = toDateInput(t.due_date)
    // 切換任務時重置 tab 與懶載入資料
    activeTab.value = 'description'
    comments.value = []
    attachments.value = []
  },
)

const saving = ref(false)
const newComment = ref('')
const submittingComment = ref(false)
const comments = ref<Comment[]>([])
const loadingComments = ref(false)
const attachments = ref<Attachment[]>([])
const loadingAttachments = ref(false)

const subtasks = computed(() => taskStore.getSubtasks(props.task.id))

async function onTabClick(key: TabKey) {
  activeTab.value = key
  if (key === 'comments' && comments.value.length === 0) {
    await loadComments()
  }
  if (key === 'attachments' && attachments.value.length === 0) {
    await loadAttachments()
  }
}

async function loadComments() {
  loadingComments.value = true
  try {
    const { data } = await client.get(`/tasks/${props.task.id}/comments/`)
    comments.value = data.results
  } finally {
    loadingComments.value = false
  }
}

async function onSubmitComment() {
  if (!newComment.value.trim()) return
  submittingComment.value = true
  try {
    const { data } = await client.post<Comment>(`/tasks/${props.task.id}/comments/`, {
      content: newComment.value.trim(),
    })
    comments.value = [...comments.value, data]
    newComment.value = ''
  } finally {
    submittingComment.value = false
  }
}

async function loadAttachments() {
  loadingAttachments.value = true
  try {
    const { data } = await client.get(`/tasks/${props.task.id}/attachments/`)
    attachments.value = data.results
  } finally {
    loadingAttachments.value = false
  }
}

function onAttachmentUploaded(a: AttachmentDTO) {
  // 後端 TaskAttachmentSerializer 用 `uploader`；本地列表型別歷史上叫 `uploaded_by`，做一次對齊
  attachments.value = [
    ...attachments.value,
    {
      id: a.id,
      file_name: a.file_name,
      file_size: a.file_size,
      mime_type: a.mime_type,
      uploaded_by: a.uploader,
      created_at: a.created_at,
    },
  ]
}

async function onSave() {
  saving.value = true
  try {
    await taskStore.update(props.task.id, {
      title: form.title,
      description: form.description,
      priority: form.priority as TaskPriority,
      due_date: form.due_date ? dayjs(form.due_date).toISOString() : null,
    })
  } finally {
    saving.value = false
  }
}

async function onDelete() {
  if (!window.confirm('確定要刪除此任務？')) return
  await taskStore.remove(props.task.id)
  emit('deleted')
  emit('close')
}

function toDateInput(iso: string | null): string {
  return iso ? dayjs(iso).format('YYYY-MM-DD') : ''
}

function formatDate(iso: string): string {
  return dayjs(iso).format('YYYY-MM-DD HH:mm')
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}

function priorityColor(p: TaskPriority): string {
  return {
    urgent: 'bg-red-700',
    high: 'bg-rose-600',
    medium: 'bg-blue-600',
    low: 'bg-stone-500',
  }[p]
}
</script>
